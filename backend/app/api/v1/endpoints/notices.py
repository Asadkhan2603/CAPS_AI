from datetime import datetime, timezone
from typing import Any, List

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.notices import notice_public
from app.schemas.notice import NoticeCreate, NoticeOut
from app.services.audit import log_audit_event
from app.services.cloudinary_uploads import (
    ALLOWED_NOTICE_MIME_TYPES,
    MAX_NOTICE_FILE_BYTES,
    MAX_NOTICE_FILES,
    delete_cloudinary_asset,
    upload_notice_file,
)
from app.services.background_jobs import fanout_notice_notifications

router = APIRouter()


async def _distinct_values(collection: Any, field: str, query: dict, *, fallback_length: int) -> list[Any]:
    distinct = getattr(collection, 'distinct', None)
    if callable(distinct):
        try:
            return [value for value in await distinct(field, query) if value is not None]
        except Exception:
            pass
    rows = await collection.find(query, {field: 1}).to_list(length=fallback_length)
    values: list[Any] = []
    for row in rows:
        value = row.get(field)
        if value is not None:
            values.append(value)
    return values


def _can_publish_scope(current_user: dict, scope: str) -> bool:
    normalized_scope = 'class' if scope == 'section' else scope
    if current_user.get('role') == 'admin':
        return True
    if current_user.get('role') != 'teacher':
        return False
    extensions = current_user.get('extended_roles', [])
    if normalized_scope == 'college':
        return False
    if normalized_scope == 'batch':
        return 'year_head' in extensions
    if normalized_scope == 'class':
        return 'class_coordinator' in extensions
    if normalized_scope == 'subject':
        return True
    return False


async def _validate_scope_ref_access(current_user: dict, scope: str, scope_ref_id: str | None) -> str | None:
    normalized_scope = 'class' if scope == 'section' else scope
    if normalized_scope == 'college':
        if scope_ref_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope_ref_id must be empty for college scope')
        return None

    if normalized_scope in {'batch', 'class', 'subject'} and not scope_ref_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope_ref_id is required for this scope')

    if normalized_scope == 'batch':
        batch = await db.batches.find_one({'_id': parse_object_id(scope_ref_id)})
        if not batch:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Batch not found for provided scope_ref_id')
        return scope_ref_id

    if normalized_scope == 'class':
        class_doc = await db.classes.find_one({'_id': parse_object_id(scope_ref_id)})
        if not class_doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Class not found for provided scope_ref_id')
        if current_user.get('role') == 'teacher' and class_doc.get('class_coordinator_user_id') != str(current_user['_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to publish for this class')
        return scope_ref_id

    if normalized_scope == 'subject':
        subject = await db.subjects.find_one({'_id': parse_object_id(scope_ref_id)})
        if not subject:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Subject not found for provided scope_ref_id')
        return scope_ref_id

    return scope_ref_id


async def _student_scope_visibility_ids(current_user: dict) -> tuple[set[str], set[str], set[str]]:
    user_id = str(current_user['_id'])
    user_email = (current_user.get('email') or '').strip().lower()

    student_query = {'$or': [{'email': user_email}, {'user_id': user_id}]}
    student_object_ids = await _distinct_values(db.students, '_id', student_query, fallback_length=1000)
    student_ids = [str(item) for item in student_object_ids if item]

    class_ids = {
        value
        for value in await _distinct_values(db.students, 'class_id', student_query, fallback_length=1000)
        if isinstance(value, str) and value
    }

    if student_ids:
        class_ids.update(
            {
                value
                for value in await _distinct_values(
                    db.enrollments,
                    'class_id',
                    {'student_id': {'$in': student_ids}},
                    fallback_length=5000,
                )
                if isinstance(value, str) and value
            }
        )

    batch_ids: set[str] = set()
    if class_ids:
        class_object_ids = [ObjectId(class_id) for class_id in class_ids if ObjectId.is_valid(class_id)]
        if class_object_ids:
            batch_ids = {
                value
                for value in await _distinct_values(
                    db.classes,
                    'batch_id',
                    {'_id': {'$in': class_object_ids}},
                    fallback_length=2000,
                )
                if isinstance(value, str) and value
            }

    subject_ids: set[str] = set()
    if class_ids:
        subject_ids = {
            value
            for value in await _distinct_values(
                db.assignments,
                'subject_id',
                {'class_id': {'$in': list(class_ids)}},
                fallback_length=5000,
            )
            if isinstance(value, str) and value
        }

    return class_ids, batch_ids, subject_ids


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    normalized = normalized.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid expires_at datetime format') from exc


def _to_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _extract_payload_and_files(request: Request) -> tuple[NoticeCreate, list[tuple[bytes, str, str]], datetime | None]:
    content_type = request.headers.get('content-type', '').lower()
    files: list[tuple[bytes, str, str]] = []

    if content_type.startswith('multipart/form-data'):
        form = await request.form()
        images = form.getlist('images') if hasattr(form, 'getlist') else []
        if len(images) > MAX_NOTICE_FILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'At most {MAX_NOTICE_FILES} files are allowed per notice',
            )

        for item in images:
            if not isinstance(item, UploadFile):
                continue
            mime_type = (item.content_type or '').lower()
            if mime_type not in ALLOWED_NOTICE_MIME_TYPES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Unsupported file type: {mime_type}')
            content = await item.read()
            if len(content) > MAX_NOTICE_FILE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'File {item.filename or "file"} exceeds 10MB limit',
                )
            files.append((content, mime_type, item.filename or 'file'))

        payload = NoticeCreate(
            title=str(form.get('title') or ''),
            message=str(form.get('message') or ''),
            priority=str(form.get('priority') or 'normal'),
            scope=str(form.get('scope') or 'college'),
            scope_ref_id=(str(form.get('scope_ref_id')).strip() if form.get('scope_ref_id') else None),
            expires_at=_parse_datetime(str(form.get('expires_at')) if form.get('expires_at') else None),
        )
        scheduled_at = _parse_datetime(str(form.get('scheduled_at')) if form.get('scheduled_at') else None)
        return payload, files, scheduled_at

    raw = await request.json()
    scheduled_at = _parse_datetime(raw.get('scheduled_at')) if isinstance(raw, dict) else None
    payload = NoticeCreate(**raw)
    return payload, files, scheduled_at


@router.get('/', response_model=List[NoticeOut])
async def list_notices(
    scope: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    include_expired: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[NoticeOut]:
    query = {'is_active': True}
    if scope:
        query['scope'] = 'class' if scope == 'section' else scope
    if priority:
        query['priority'] = priority

    now = datetime.now(timezone.utc)
    query['$or'] = [{'scheduled_at': None}, {'scheduled_at': {'$lte': now}}]
    items = await db.notices.find(query).skip(skip).limit(limit).to_list(length=limit)
    items = sorted(items, key=lambda item: item.get('created_at') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    if not include_expired:
        items = [item for item in items if not _to_aware_utc(item.get('expires_at')) or _to_aware_utc(item.get('expires_at')) > now]

    if current_user.get('role') == 'student':
        class_ids, batch_ids, subject_ids = await _student_scope_visibility_ids(current_user)
        scoped_items = []
        for item in items:
            item_scope = item.get('scope')
            scope_ref_id = item.get('scope_ref_id')
            if item_scope == 'college':
                scoped_items.append(item)
                continue
            if item_scope == 'class' and scope_ref_id and scope_ref_id in class_ids:
                scoped_items.append(item)
                continue
            if item_scope == 'batch' and scope_ref_id and scope_ref_id in batch_ids:
                scoped_items.append(item)
                continue
            if item_scope == 'subject' and scope_ref_id and scope_ref_id in subject_ids:
                scoped_items.append(item)
                continue
        items = scoped_items

    return [NoticeOut(**notice_public(item)) for item in items]


@router.post('/', response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def create_notice(
    request: Request,
    background_tasks: BackgroundTasks,
    images: list[UploadFile] | None = File(default=None),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> NoticeOut:
    payload, uploaded_files, scheduled_at = await _extract_payload_and_files(request)

    if not _can_publish_scope(current_user, payload.scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to publish this notice scope')

    persisted_scope = 'class' if payload.scope == 'section' else payload.scope
    scope_ref_id = await _validate_scope_ref_access(current_user, payload.scope, payload.scope_ref_id)

    images: list[dict] = []
    try:
        for content, mime_type, filename in uploaded_files:
            item = await upload_notice_file(content=content, mime_type=mime_type, filename=filename)
            images.append(item)

        document = {
            'title': payload.title.strip(),
            'message': payload.message.strip(),
            'priority': payload.priority,
            'scope': persisted_scope,
            'scope_ref_id': scope_ref_id,
            'expires_at': payload.expires_at,
            'images': images,
            'is_pinned': False,
            'scheduled_at': scheduled_at,
            'read_count': 0,
            'seen_by': [],
            'created_by': str(current_user['_id']),
            'is_active': True,
            'created_at': datetime.now(timezone.utc),
        }
        result = await db.notices.insert_one(document)
        created = await db.notices.find_one({'_id': result.inserted_id})

        await log_audit_event(
            actor_user_id=str(current_user['_id']),
            action='create',
            entity_type='notice',
            entity_id=str(result.inserted_id),
            detail=f"Created {payload.priority} notice with scope {payload.scope} ({len(images)} attachments)",
        )
        if not scheduled_at or _to_aware_utc(scheduled_at) <= datetime.now(timezone.utc):
            background_tasks.add_task(fanout_notice_notifications, str(result.inserted_id))
        return NoticeOut(**notice_public(created))
    except HTTPException:
        for image in images:
            resource_type = 'image' if (image.get('mime_type') or '').startswith('image/') else 'raw'
            delete_cloudinary_asset(image.get('public_id') or '', resource_type=resource_type)
        raise
    except Exception as exc:  # pragma: no cover - handled by global error handler
        for image in images:
            resource_type = 'image' if (image.get('mime_type') or '').startswith('image/') else 'raw'
            delete_cloudinary_asset(image.get('public_id') or '', resource_type=resource_type)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to create notice') from exc


@router.delete('/{notice_id}')
async def delete_notice(
    notice_id: str,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
    notice_obj_id = parse_object_id(notice_id)
    current = await db.notices.find_one({'_id': notice_obj_id, 'is_active': True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')

    if current_user.get('role') == 'teacher' and current.get('created_by') != str(current_user['_id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this notice')

    for file_item in current.get('images', []) or []:
        mime = str(file_item.get('mime_type') or '').lower()
        resource_type = 'image' if mime.startswith('image/') else 'raw'
        delete_cloudinary_asset(file_item.get('public_id') or '', resource_type=resource_type)

    await db.notices.update_one(
        {'_id': notice_obj_id},
        {'$set': {'is_active': False, 'is_deleted': True, 'deleted_at': datetime.now(timezone.utc), 'deleted_by': str(current_user['_id'])}},
    )
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='delete',
        entity_type='notice',
        entity_id=notice_id,
        detail='Notice deleted and cloud attachments cleaned up',
    )
    return {'success': True, 'message': 'Notice deleted'}


@router.post('/process-scheduled')
async def process_scheduled_notices(
    background_tasks: BackgroundTasks,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
    now = datetime.now(timezone.utc)
    notices = await db.notices.find(
        {
            'is_active': True,
            'scheduled_at': {'$ne': None, '$lte': now},
            '$or': [{'fanout_dispatched_at': None}, {'fanout_dispatched_at': {'$exists': False}}],
        },
        {'_id': 1},
    ).limit(200).to_list(length=200)
    for notice in notices:
        background_tasks.add_task(fanout_notice_notifications, str(notice.get('_id')))
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='process_scheduled_notices',
        entity_type='notice',
        detail=f'Queued {len(notices)} scheduled notices for dispatch',
    )
    return {'success': True, 'queued': len(notices)}

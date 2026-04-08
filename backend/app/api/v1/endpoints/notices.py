from datetime import datetime, timezone
from typing import Any, List

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import NOTICE_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.notices import notice_public
from app.schemas.notice import NoticeCreate, NoticeOut, NoticeReadBatchRequest, NoticeUpdate
from app.services.audit import log_audit_event
from app.services.communication_deliveries import (
    default_delivery_summary,
    get_delivery_read_map,
    get_delivery_summaries,
    mark_delivery_read,
)
from app.services.club_permissions import can_manage_club
from app.services.cloudinary_uploads import (
    ALLOWED_NOTICE_MIME_TYPES,
    MAX_NOTICE_FILE_BYTES,
    MAX_NOTICE_FILES,
    delete_cloudinary_asset,
    upload_notice_file,
)
from app.services.background_jobs import dispatch_scheduled_notice_notifications, fanout_notice_notifications

router = APIRouter()


async def _attach_notice_delivery_context(items: list[dict], *, current_user_id: str) -> list[dict]:
    notice_ids = [str(item.get('_id')) for item in items if item.get('_id')]
    summaries = await get_delivery_summaries(source_kind='notice', source_ids=notice_ids)
    read_map = await get_delivery_read_map(
        source_kind='notice',
        source_ids=notice_ids,
        target_user_id=current_user_id,
    )
    hydrated: list[dict] = []
    for item in items:
        source_id = str(item.get('_id') or '')
        payload = dict(item)
        payload['delivery_summary'] = summaries.get(source_id, default_delivery_summary())
        payload['current_user_delivery_read'] = read_map.get(source_id, False)
        hydrated.append(payload)
    return hydrated


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
    if current_user.get('role') == 'student':
        return normalized_scope == 'club'
    if current_user.get('role') != 'teacher':
        return False
    extensions = current_user.get('extended_roles', [])
    if normalized_scope == 'college':
        return False
    if normalized_scope == 'batch':
        return 'year_head' in extensions
    if normalized_scope == 'class':
        return 'class_coordinator' in extensions
    if normalized_scope == 'club':
        return True
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

    if normalized_scope == 'club':
        club = await db.clubs.find_one({'_id': parse_object_id(scope_ref_id)})
        if not club:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Club not found for provided scope_ref_id')
        if current_user.get('role') == 'teacher' and not can_manage_club(current_user, club):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to publish for this club')
        if current_user.get('role') == 'student' and club.get('president_user_id') != str(current_user['_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only the club president can publish club announcements')
        return scope_ref_id

    return scope_ref_id


async def _student_scope_visibility_ids(current_user: dict) -> tuple[set[str], set[str], set[str], set[str]]:
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

    club_ids = {
        value
        for value in await _distinct_values(
            db.club_members,
            'club_id',
            {'student_user_id': user_id, 'status': 'active'},
            fallback_length=2000,
        )
        if isinstance(value, str) and value
    }
    club_ids.update(
        {
            value
            for value in await _distinct_values(
                db.clubs,
                '_id',
                {'president_user_id': user_id},
                fallback_length=200,
            )
            if value
        }
    )
    normalized_club_ids = {str(value) for value in club_ids if value}

    return class_ids, batch_ids, subject_ids, normalized_club_ids


def _notice_is_expired(item: dict, now: datetime) -> bool:
    expires_at = _to_aware_utc(item.get('expires_at'))
    return bool(expires_at and expires_at <= now)


def _student_can_view_notice(
    item: dict,
    *,
    class_ids: set[str],
    batch_ids: set[str],
    subject_ids: set[str],
    club_ids: set[str],
) -> bool:
    item_scope = item.get('scope')
    scope_ref_id = item.get('scope_ref_id')
    if item_scope == 'college':
        return True
    if item_scope == 'class' and scope_ref_id and scope_ref_id in class_ids:
        return True
    if item_scope == 'batch' and scope_ref_id and scope_ref_id in batch_ids:
        return True
    if item_scope == 'subject' and scope_ref_id and scope_ref_id in subject_ids:
        return True
    if item_scope == 'club' and scope_ref_id and scope_ref_id in club_ids:
        return True
    return False


async def _filter_visible_notices(items: list[dict], current_user: dict) -> list[dict]:
    if current_user.get('role') != 'student':
        return items

    class_ids, batch_ids, subject_ids, club_ids = await _student_scope_visibility_ids(current_user)
    return [
        item
        for item in items
        if _student_can_view_notice(
            item,
            class_ids=class_ids,
            batch_ids=batch_ids,
            subject_ids=subject_ids,
            club_ids=club_ids,
        )
    ]


async def _get_visible_notice_or_404(current_user: dict, notice_id: str) -> dict:
    notice_obj_id = parse_object_id(notice_id)
    notice = await db.notices.find_one({'_id': notice_obj_id, 'is_active': True})
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')

    now = datetime.now(timezone.utc)
    scheduled_at = _to_aware_utc(notice.get('scheduled_at'))
    if scheduled_at and scheduled_at > now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')
    if _notice_is_expired(notice, now):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')

    visible = await _filter_visible_notices([notice], current_user)
    if not visible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')
    return visible[0]


async def _mark_notice_read_for_user(notice: dict, current_user: dict) -> dict:
    current_user_id = str(current_user['_id'])
    seen_by = [str(item) for item in (notice.get('seen_by') or []) if item]
    if current_user_id not in seen_by:
        seen_by.append(current_user_id)
        await db.notices.update_one(
            {'_id': notice['_id']},
            {
                '$set': {
                    'seen_by': seen_by,
                    'read_count': len(seen_by),
                    'schema_version': NOTICE_SCHEMA_VERSION,
                }
            },
        )
        notice = await db.notices.find_one({'_id': notice['_id']})
    await mark_delivery_read(
        source_kind='notice',
        source_id=str(notice['_id']),
        target_user_id=current_user_id,
    )
    return notice


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
            is_pinned=str(form.get('is_pinned') or '').strip().lower() in {'1', 'true', 'yes', 'on'},
            template_key=(str(form.get('template_key')).strip() if form.get('template_key') else None),
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
    scope_ref_id: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    include_expired: bool = Query(default=False),
    include_scheduled: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[NoticeOut]:
    query = {'is_active': True}
    if scope:
        query['scope'] = 'class' if scope == 'section' else scope
    if scope_ref_id:
        query['scope_ref_id'] = scope_ref_id
    if priority:
        query['priority'] = priority

    now = datetime.now(timezone.utc)
    items = await db.notices.find(query).skip(skip).limit(limit).to_list(length=limit)
    if include_scheduled and current_user.get('role') in {'admin', 'teacher'}:
        current_user_id = str(current_user['_id'])
        items = [
            item
            for item in items
            if (
                (_to_aware_utc(item.get('scheduled_at')) or now) <= now
                or current_user.get('role') == 'admin'
                or item.get('created_by') == current_user_id
            )
        ]
    else:
        items = [
            item
            for item in items
            if (_to_aware_utc(item.get('scheduled_at')) or now) <= now
        ]
    items = sorted(
        items,
        key=lambda item: (
            1 if item.get('is_pinned') else 0,
            item.get('created_at') or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    if not include_expired:
        items = [item for item in items if not _notice_is_expired(item, now)]

    items = await _filter_visible_notices(items, current_user)

    hydrated = await _attach_notice_delivery_context(items, current_user_id=str(current_user['_id']))
    return [NoticeOut(**notice_public(item, current_user_id=str(current_user['_id']))) for item in hydrated]


@router.get('/unread-count')
async def get_unread_notice_count_payload(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    now = datetime.now(timezone.utc)
    items = await db.notices.find(
        {
            'is_active': True,
            '$or': [{'scheduled_at': None}, {'scheduled_at': {'$lte': now}}],
        },
        {
            '_id': 1,
            'scope': 1,
            'scope_ref_id': 1,
            'seen_by': 1,
            'expires_at': 1,
            'scheduled_at': 1,
        },
    ).to_list(length=5000)
    items = [item for item in items if not _notice_is_expired(item, now)]
    items = await _filter_visible_notices(items, current_user)
    current_user_id = str(current_user['_id'])
    hydrated = await _attach_notice_delivery_context(items, current_user_id=current_user_id)
    count = sum(1 for item in hydrated if not notice_public(item, current_user_id=current_user_id).get('is_read'))
    return {'count': count}


@router.get('/unread-count')
async def get_unread_notice_count(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    return await get_unread_notice_count_payload(current_user)


@router.post('/', response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def create_notice(
    request: Request,
    background_tasks: BackgroundTasks,
    images: list[UploadFile] | None = File(default=None),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
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
            'is_pinned': bool(payload.is_pinned),
            'template_key': payload.template_key,
            'scheduled_at': scheduled_at,
            'read_count': 0,
            'seen_by': [],
            'fanout_status': 'scheduled' if scheduled_at and _to_aware_utc(scheduled_at) > datetime.now(timezone.utc) else 'queued',
            'fanout_attempts': 0,
            'fanout_last_attempt_at': None,
            'fanout_next_retry_at': None,
            'fanout_count': 0,
            'fanout_dispatched_at': None,
            'fanout_failed_at': None,
            'fanout_error': None,
            'fanout_processing_started_at': None,
            'fanout_processing_expires_at': None,
            'created_by': str(current_user['_id']),
            'is_active': True,
            'created_at': datetime.now(timezone.utc),
            'schema_version': NOTICE_SCHEMA_VERSION,
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
        hydrated = await _attach_notice_delivery_context([created], current_user_id=str(current_user['_id']))
        return NoticeOut(**notice_public(hydrated[0], current_user_id=str(current_user['_id'])))
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


@router.patch('/{notice_id}', response_model=NoticeOut)
async def update_notice(
    notice_id: str,
    payload: NoticeUpdate,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> NoticeOut:
    notice_obj_id = parse_object_id(notice_id)
    current = await db.notices.find_one({'_id': notice_obj_id, 'is_active': True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')

    if current_user.get('role') == 'teacher' and current.get('created_by') != str(current_user['_id']):
        if current.get('scope') != 'club':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this notice')
        club = await db.clubs.find_one({'_id': parse_object_id(current.get('scope_ref_id'))})
        if not club or not can_manage_club(current_user, club):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this notice')
    if current_user.get('role') == 'student':
        if current.get('scope') != 'club':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this notice')
        club = await db.clubs.find_one({'_id': parse_object_id(current.get('scope_ref_id'))})
        if not club or club.get('president_user_id') != str(current_user['_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this notice')

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    update_data['schema_version'] = NOTICE_SCHEMA_VERSION
    await db.notices.update_one({'_id': notice_obj_id}, {'$set': update_data})
    updated = await db.notices.find_one({'_id': notice_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='update',
        entity_type='notice',
        entity_id=notice_id,
        detail='Updated notice settings',
        old_value={'is_pinned': current.get('is_pinned', False)},
        new_value={'is_pinned': update_data.get('is_pinned', current.get('is_pinned', False))},
    )
    hydrated = await _attach_notice_delivery_context([updated], current_user_id=str(current_user['_id']))
    return NoticeOut(**notice_public(hydrated[0], current_user_id=str(current_user['_id'])))


@router.delete('/{notice_id}')
async def delete_notice(
    notice_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    notice_obj_id = parse_object_id(notice_id)
    current = await db.notices.find_one({'_id': notice_obj_id, 'is_active': True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notice not found')

    if current_user.get('role') == 'teacher' and current.get('created_by') != str(current_user['_id']):
        if current.get('scope') != 'club':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this notice')
        club = await db.clubs.find_one({'_id': parse_object_id(current.get('scope_ref_id'))})
        if not club or not can_manage_club(current_user, club):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this notice')
    if current_user.get('role') == 'student':
        if current.get('scope') != 'club':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this notice')
        club = await db.clubs.find_one({'_id': parse_object_id(current.get('scope_ref_id'))})
        if not club or club.get('president_user_id') != str(current_user['_id']):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this notice')

    for file_item in current.get('images', []) or []:
        mime = str(file_item.get('mime_type') or '').lower()
        resource_type = 'image' if mime.startswith('image/') else 'raw'
        delete_cloudinary_asset(file_item.get('public_id') or '', resource_type=resource_type)

    await db.notices.update_one(
        {'_id': notice_obj_id},
        {
            '$set': {
                'is_active': False,
                'is_deleted': True,
                'deleted_at': datetime.now(timezone.utc),
                'deleted_by': str(current_user['_id']),
                'schema_version': NOTICE_SCHEMA_VERSION,
            }
        },
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
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
    dispatched = await dispatch_scheduled_notice_notifications(limit=200)
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='process_scheduled_notices',
        entity_type='notice',
        detail=f'Dispatched {dispatched} scheduled notices',
    )
    return {'success': True, 'dispatched': dispatched}


@router.post('/{notice_id}/read', response_model=NoticeOut)
async def mark_notice_read(
    notice_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> NoticeOut:
    notice = await _get_visible_notice_or_404(current_user, notice_id)
    updated = await _mark_notice_read_for_user(notice, current_user)
    hydrated = await _attach_notice_delivery_context([updated], current_user_id=str(current_user['_id']))
    return NoticeOut(**notice_public(hydrated[0], current_user_id=str(current_user['_id'])))


@router.post('/read')
async def mark_notices_read(
    payload: NoticeReadBatchRequest,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    updated_notices: list[dict] = []
    for notice_id in payload.notice_ids:
        try:
            notice = await _get_visible_notice_or_404(current_user, notice_id)
        except HTTPException:
            continue
        updated_notices.append(await _mark_notice_read_for_user(notice, current_user))

    hydrated = await _attach_notice_delivery_context(updated_notices, current_user_id=str(current_user['_id']))
    return {
        'marked_count': len(updated_notices),
        'items': [
            notice_public(item, current_user_id=str(current_user['_id']))
            for item in hydrated
        ],
    }

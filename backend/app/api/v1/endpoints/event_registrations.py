from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLUB_EVENT_SCHEMA_VERSION, EVENT_REGISTRATION_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.event_registrations import event_registration_public
from app.schemas.event_registration import (
    EventRegistrationBulkUpdate,
    EventRegistrationCreate,
    EventRegistrationOut,
    EventRegistrationReminder,
    EventRegistrationUpdate,
)
from app.schemas.queue_insights import SharedQueueSnapshotOut, SharedQueueViewCreate, SharedQueueViewOut
from app.services.audit import log_audit_event
from app.services.club_queue_insights import (
    delete_shared_queue_view,
    list_shared_queue_snapshots,
    list_shared_queue_views,
    record_event_queue_snapshot,
    save_shared_queue_view,
)
from app.services.club_permissions import is_admin, student_is_club_president_for_event, teacher_managed_event_ids
from app.services.notifications import create_notifications_bulk
from app.services.public_ids import build_public_id, persist_public_id, persist_public_id_update

router = APIRouter()

RECEIPT_UPLOAD_DIR = Path('uploads/event_registrations')
MAX_RECEIPT_SIZE = 10 * 1024 * 1024
ALLOWED_RECEIPT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf'}


def _normalize_datetime_to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _current_user_identity_fields(current_user: dict, *, prefix: str) -> dict:
    return {
        prefix: str(current_user['_id']),
        f'{prefix}_name': current_user.get('full_name'),
        f'{prefix}_email': current_user.get('email'),
    }


async def _resolve_user_document(user_id: str | None) -> dict | None:
    owner_id = _normalize_optional_text(user_id)
    if not owner_id or not ObjectId.is_valid(owner_id):
        return None
    return await db.users.find_one({'_id': ObjectId(owner_id)})


async def _resolve_event_queue_owner(event: dict, owner_user_id: str | None) -> dict | None:
    owner_id = _normalize_optional_text(owner_user_id)
    if not owner_id:
        return None
    owner = await _resolve_user_document(owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Queue owner not found')
    club = await db.clubs.find_one({'_id': parse_object_id(event.get('club_id'))}) if event.get('club_id') else None
    owner_role = owner.get('role')
    if owner_role == 'admin':
        return owner
    if club and owner_role == 'teacher' and club.get('coordinator_user_id') == str(owner.get('_id')):
        return owner
    if club and owner_role == 'student' and club.get('president_user_id') == str(owner.get('_id')):
        return owner
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Queue owner must be a club manager for this event',
    )


def _require_payment_reference_if_needed(event: dict, payment_reference: str | None) -> None:
    if event.get('payment_required') and not payment_reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Payment reference is required for this event',
        )


async def _student_has_club_access(student_user_id: str, club_id: str) -> bool:
    club = await db.clubs.find_one({'_id': parse_object_id(club_id)})
    if not club:
        return False
    if club.get('president_user_id') == student_user_id:
        return True
    membership = await db.club_members.find_one(
        {'club_id': club_id, 'student_user_id': student_user_id, 'status': 'active'}
    )
    return membership is not None


async def _count_confirmed_registrations(event_id: str, *, exclude_registration_id=None) -> int:
    query = {'event_id': event_id, 'status': {'$in': ['registered', 'approved']}}
    if exclude_registration_id is not None:
        query['_id'] = {'$ne': exclude_registration_id}
    return await db.event_registrations.count_documents(query)


async def _registration_has_capacity(event_id: str, *, exclude_registration_id=None) -> bool:
    event = await db.club_events.find_one({'_id': parse_object_id(event_id)})
    if not event:
        return False
    capacity = int(event.get('capacity') or 0)
    if capacity <= 0:
        return True
    confirmed = await _count_confirmed_registrations(event_id, exclude_registration_id=exclude_registration_id)
    return confirmed < capacity


def _next_active_registration_status(event: dict, *, has_capacity: bool) -> str:
    if not has_capacity:
        return 'waitlisted'
    return 'pending' if event.get('approval_required') else 'registered'


async def _validate_and_prepare_registration(event_id: str, student_user_id: str) -> dict:
    event = await db.club_events.find_one({'_id': parse_object_id(event_id)})
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Event not found for provided event_id')

    if event.get('visibility') == 'members_only':
        has_access = await _student_has_club_access(student_user_id, event.get('club_id'))
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only active club members can register for this event',
            )

    duplicate = await db.event_registrations.find_one(
        {
            'event_id': event_id,
            'student_user_id': student_user_id,
            'status': {'$in': ['registered', 'pending', 'approved', 'waitlisted']},
        }
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Already registered for this event')

    if not event.get('registration_enabled', True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Registration is disabled for this event')
    if event.get('status') != 'open':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Event is closed for registration')

    now = datetime.now(timezone.utc)
    registration_start = _normalize_datetime_to_utc(event.get('registration_start'))
    registration_end = _normalize_datetime_to_utc(event.get('registration_end'))

    if registration_start:
        if now < registration_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Registration has not started yet',
            )

    if registration_end:
        if now > registration_end:
            if event.get('status') == 'open':
                await db.club_events.update_one(
                    {'_id': event['_id']},
                    {'$set': {'status': 'closed', 'schema_version': CLUB_EVENT_SCHEMA_VERSION}},
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Registration deadline has passed',
            )

    return event


async def _promote_waitlisted_registration(event_id: str) -> None:
    event = await db.club_events.find_one({'_id': parse_object_id(event_id)})
    if not event:
        return

    has_capacity = await _registration_has_capacity(event_id)
    if not has_capacity:
        return

    waitlisted = await db.event_registrations.find_one(
        {'event_id': event_id, 'status': 'waitlisted'},
        sort=[('created_at', 1)],
    )
    if not waitlisted:
        return

    promoted_status = _next_active_registration_status(event, has_capacity=True)
    await db.event_registrations.update_one(
        {'_id': waitlisted['_id']},
        {'$set': {'status': promoted_status, 'schema_version': EVENT_REGISTRATION_SCHEMA_VERSION}},
    )
    await log_audit_event(
        actor_user_id=None,
        action='promote_waitlisted_registration',
        entity_type='event_registration',
        entity_id=str(waitlisted['_id']),
        detail=f'Promoted waitlisted registration to {promoted_status}',
        old_value={'status': 'waitlisted'},
        new_value={'status': promoted_status},
        severity='low',
    )
    await record_event_queue_snapshot(
        event_id=event_id,
        changed_by_user_id=None,
        source_action='promote_waitlisted_registration',
    )


async def _ensure_registration_manage_access(current_user: dict, event_id: str) -> None:
    if is_admin(current_user):
        return

    role = current_user.get('role')
    if role == 'teacher':
        managed_event_ids = await teacher_managed_event_ids(str(current_user['_id']))
        if event_id in managed_event_ids:
            return
    elif role == 'student':
        if await student_is_club_president_for_event(str(current_user.get('_id')), event_id):
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail='Not allowed to manage registrations for this event',
    )


async def _build_registration_out(document: dict) -> EventRegistrationOut:
    row = dict(document)
    student_user_id = row.get('student_user_id')
    if student_user_id:
        try:
            user = await db.users.find_one({'_id': parse_object_id(student_user_id)})
        except HTTPException:
            user = None
        if user:
            row.setdefault('student_name', user.get('full_name'))
            row.setdefault('student_email', user.get('email'))
    return EventRegistrationOut(**event_registration_public(row))


async def _reuse_terminal_registration(existing: dict, update_data: dict) -> dict:
    persist_public_id_update(existing, update_data, kind='event_registration')
    await db.event_registrations.update_one({'_id': existing['_id']}, {'$set': update_data})
    return await db.event_registrations.find_one({'_id': existing['_id']})


async def _apply_registration_update(
    *,
    registration: dict,
    event: dict,
    update_data: dict,
    current_user: dict,
) -> dict:
    current_status = registration.get('status', 'registered')
    next_status = update_data.get('status', current_status)
    effective_status = next_status
    effective_attendance = update_data.get('attendance_status', registration.get('attendance_status'))
    effective_certificate = update_data.get('certificate_issued', registration.get('certificate_issued', False))
    normalized_update_data = dict(update_data)

    if 'queue_owner_user_id' in normalized_update_data:
        owner = await _resolve_event_queue_owner(event, normalized_update_data.get('queue_owner_user_id'))
        normalized_update_data['queue_owner_user_id'] = str(owner['_id']) if owner else None
        normalized_update_data['queue_owner_name'] = owner.get('full_name') if owner else None
        normalized_update_data['queue_owner_email'] = owner.get('email') if owner else None

    if 'coordinator_note' in normalized_update_data:
        normalized_update_data['coordinator_note'] = _normalize_optional_text(normalized_update_data.get('coordinator_note'))

    if 'status' in normalized_update_data:
        allowed_status_transitions = {
            'pending': {'approved', 'rejected', 'waitlisted'},
            'waitlisted': {'cancelled', 'pending', 'approved', 'registered'},
            'registered': {'cancelled'},
            'approved': {'cancelled'},
        }
        allowed = allowed_status_transitions.get(current_status, set())
        if next_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid registration status transition: {current_status} -> {next_status}',
            )

        if next_status in {'approved', 'registered', 'pending'} and current_status == 'waitlisted':
            if next_status == 'pending' and not event.get('approval_required'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Pending is only valid for approval-based events',
                )
            if next_status == 'registered' and event.get('approval_required'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Approval-based events must promote waitlisted registrations to pending or approved',
                )

        if next_status in {'approved', 'registered'}:
            has_capacity = await _registration_has_capacity(
                registration.get('event_id'),
                exclude_registration_id=registration['_id'],
            )
            if not has_capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Event registration capacity reached',
                )

    if 'attendance_status' in normalized_update_data and effective_status not in {'registered', 'approved'}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Attendance can be marked only for approved or registered attendees',
        )

    if 'certificate_issued' in normalized_update_data and effective_certificate:
        if not event.get('certificate_enabled'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Certificates are not enabled for this event',
            )
        if effective_status not in {'registered', 'approved'}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Certificate can be issued only for approved or registered attendees',
            )
        if effective_attendance != 'present':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Attendance must be marked present before issuing a certificate',
            )

    normalized_update_data.update(_current_user_identity_fields(current_user, prefix='last_touched_by'))
    normalized_update_data['last_touched_at'] = datetime.now(timezone.utc)
    normalized_update_data['schema_version'] = EVENT_REGISTRATION_SCHEMA_VERSION
    old_value_snapshot = {
        'status': current_status,
        'queue_owner_user_id': registration.get('queue_owner_user_id'),
        'coordinator_note': registration.get('coordinator_note'),
        'attendance_status': registration.get('attendance_status'),
        'certificate_issued': registration.get('certificate_issued', False),
    }
    await db.event_registrations.update_one({'_id': registration['_id']}, {'$set': normalized_update_data})
    updated = await db.event_registrations.find_one({'_id': registration['_id']})

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='update_event_registration',
        entity_type='event_registration',
        entity_id=str(registration['_id']),
        detail='Updated event registration lifecycle state'
        if {'status', 'attendance_status', 'certificate_issued'} & set(normalized_update_data)
        else 'Updated event registration queue context',
        old_value=old_value_snapshot,
        new_value={
            'status': updated.get('status'),
            'queue_owner_user_id': updated.get('queue_owner_user_id'),
            'coordinator_note': updated.get('coordinator_note'),
            'attendance_status': updated.get('attendance_status'),
            'certificate_issued': updated.get('certificate_issued', False),
        },
        severity='medium',
    )

    if current_status in {'registered', 'approved'} and updated.get('status') == 'cancelled':
        await _promote_waitlisted_registration(registration.get('event_id'))
    else:
        await record_event_queue_snapshot(
            event_id=registration.get('event_id'),
            changed_by_user_id=str(current_user['_id']),
            source_action='update_event_registration',
        )

    return updated


@router.get('/', response_model=List[EventRegistrationOut])
async def list_event_registrations(
    event_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[EventRegistrationOut]:
    query = {}
    role = current_user.get('role')

    if role == 'student':
        if event_id:
            query['event_id'] = event_id
        query['student_user_id'] = str(current_user['_id'])
    elif role == 'teacher':
        teacher_user_id = str(current_user['_id'])
        managed_event_ids = await teacher_managed_event_ids(teacher_user_id)
        if event_id:
            if event_id not in managed_event_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view registrations for this event')
            query['event_id'] = event_id
        else:
            if not managed_event_ids:
                return []
            query['event_id'] = {'$in': managed_event_ids}
    else:
        if event_id:
            query['event_id'] = event_id

    items = await db.event_registrations.find(query).skip(skip).limit(limit).to_list(length=limit)

    enriched = []
    for item in items:
        row = dict(item)
        student_user_id = row.get('student_user_id')
        if student_user_id:
            try:
                user = await db.users.find_one({'_id': parse_object_id(student_user_id)})
            except HTTPException:
                user = None
            if user:
                if not row.get('student_name'):
                    row['student_name'] = user.get('full_name')
                if not row.get('student_email'):
                    row['student_email'] = user.get('email')
        enriched.append(row)

    return [EventRegistrationOut(**event_registration_public(item)) for item in enriched]


@router.patch('/{registration_id}', response_model=EventRegistrationOut)
async def update_event_registration(
    registration_id: str,
    payload: EventRegistrationUpdate,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> EventRegistrationOut:
    registration_obj_id = parse_object_id(registration_id)
    registration = await db.event_registrations.find_one({'_id': registration_obj_id})
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Event registration not found')

    await _ensure_registration_manage_access(current_user, registration.get('event_id'))

    event = await db.club_events.find_one({'_id': parse_object_id(registration.get('event_id'))})
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Parent event not found')

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    updated = await _apply_registration_update(
        registration=registration,
        event=event,
        update_data=update_data,
        current_user=current_user,
    )
    return await _build_registration_out(updated)


@router.post('/bulk-update')
async def bulk_update_event_registrations(
    payload: EventRegistrationBulkUpdate,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    update_data = payload.model_dump(exclude_unset=True)
    registration_ids = update_data.pop('registration_ids', [])
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    updated_ids: list[str] = []
    touched_event_ids: set[str] = set()
    for registration_id in registration_ids:
        registration = await db.event_registrations.find_one({'_id': parse_object_id(registration_id)})
        if not registration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Event registration not found')
        await _ensure_registration_manage_access(current_user, registration.get('event_id'))
        if registration.get('event_id'):
            touched_event_ids.add(str(registration.get('event_id')))
        event = await db.club_events.find_one({'_id': parse_object_id(registration.get('event_id'))})
        if not event:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Parent event not found')
        updated = await _apply_registration_update(
            registration=registration,
            event=event,
            update_data=dict(update_data),
            current_user=current_user,
        )
        updated_ids.append(str(updated['_id']))

    for event_id in touched_event_ids:
        await record_event_queue_snapshot(
            event_id=event_id,
            changed_by_user_id=str(current_user['_id']),
            source_action='bulk_update_event_registrations',
        )

    return {
        'updated_count': len(updated_ids),
        'updated_ids': updated_ids,
    }


@router.post('/remind')
async def remind_event_registrations(
    payload: EventRegistrationReminder,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    await _ensure_registration_manage_access(current_user, payload.event_id)
    event = await db.club_events.find_one({'_id': parse_object_id(payload.event_id)})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Parent event not found')

    query: dict = {'event_id': payload.event_id}
    if payload.registration_ids:
        query['_id'] = {'$in': [parse_object_id(item) for item in payload.registration_ids]}
    elif payload.status_filter:
        query['status'] = payload.status_filter
    else:
        query['status'] = {'$in': ['pending', 'waitlisted']}

    registrations = await db.event_registrations.find(query).to_list(length=1000)
    if not registrations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No matching registrations found')

    target_user_ids = [str(item.get('student_user_id')) for item in registrations if item.get('student_user_id')]
    if not target_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No notification recipients found')

    status_label = payload.status_filter or ('selected queue' if payload.registration_ids else 'event queue')
    message = payload.message or (
        f"{event.get('title', 'This event')} still has your registration in the {status_label}. "
        "Open clubs to review the latest registration status."
    )
    inserted = await create_notifications_bulk(
        title=f"{event.get('title', 'Event')} registration update",
        message=message,
        priority='normal',
        scope='club',
        target_user_ids=target_user_ids,
        created_by=str(current_user['_id']),
    )
    return {
        'reminded_count': inserted,
        'target_count': len(target_user_ids),
        'event_id': payload.event_id,
    }


@router.get('/views', response_model=List[SharedQueueViewOut])
async def list_event_queue_views(
    event_id: str = Query(..., min_length=1),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[SharedQueueViewOut]:
    await _ensure_registration_manage_access(current_user, event_id)
    rows = await list_shared_queue_views(scope_type='event', scope_id=event_id, queue_type='enrollment')
    return [SharedQueueViewOut(**row) for row in rows]


@router.post('/views', response_model=SharedQueueViewOut, status_code=status.HTTP_201_CREATED)
async def create_event_queue_view(
    payload: SharedQueueViewCreate,
    event_id: str = Query(..., min_length=1),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> SharedQueueViewOut:
    await _ensure_registration_manage_access(current_user, event_id)
    created = await save_shared_queue_view(
        scope_type='event',
        scope_id=event_id,
        queue_type='enrollment',
        name=payload.name,
        filters=payload.filters.model_dump(),
        current_user_id=str(current_user['_id']),
    )
    return SharedQueueViewOut(**created)


@router.delete('/views/{view_id}')
async def delete_event_queue_view(
    view_id: str,
    event_id: str = Query(..., min_length=1),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    await _ensure_registration_manage_access(current_user, event_id)
    deleted = await delete_shared_queue_view(
        view_id=view_id,
        scope_type='event',
        scope_id=event_id,
        queue_type='enrollment',
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Shared queue view not found')
    return {'deleted': True, 'view_id': view_id}


@router.get('/history', response_model=List[SharedQueueSnapshotOut])
async def list_event_queue_history(
    event_id: str = Query(..., min_length=1),
    limit: int = Query(default=12, ge=1, le=24),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[SharedQueueSnapshotOut]:
    await _ensure_registration_manage_access(current_user, event_id)
    rows = await list_shared_queue_snapshots(scope_type='event', scope_id=event_id, queue_type='enrollment', limit=limit)
    return [SharedQueueSnapshotOut(**row) for row in rows]


@router.post('/', response_model=EventRegistrationOut, status_code=status.HTTP_201_CREATED)
async def create_event_registration(
    payload: EventRegistrationCreate,
    current_user=Depends(require_roles(['student'])),
) -> EventRegistrationOut:
    student_user_id = str(current_user['_id'])
    event = await _validate_and_prepare_registration(payload.event_id, student_user_id)
    _require_payment_reference_if_needed(event, payload.payment_qr_code)
    has_capacity = await _registration_has_capacity(payload.event_id)

    document = {
        'event_id': payload.event_id,
        'student_user_id': student_user_id,
        'enrollment_number': payload.enrollment_number,
        'full_name': payload.full_name,
        'email': payload.email,
        'year': payload.year,
        'course_branch': payload.course_branch,
        'class_name': payload.class_name,
        'phone_number': payload.phone_number,
        'whatsapp_number': payload.whatsapp_number,
        'payment_qr_code': payload.payment_qr_code,
        'payment_receipt_original_filename': None,
        'payment_receipt_stored_filename': None,
        'payment_receipt_mime_type': None,
        'payment_receipt_size_bytes': None,
        'status': _next_active_registration_status(event, has_capacity=has_capacity),
        'attendance_status': None,
        'certificate_issued': False,
        'created_at': datetime.now(timezone.utc),
        'schema_version': EVENT_REGISTRATION_SCHEMA_VERSION,
    }
    terminal_registration = await db.event_registrations.find_one(
        {
            'event_id': payload.event_id,
            'student_user_id': student_user_id,
            'status': {'$in': ['rejected', 'cancelled']},
        }
    )
    if terminal_registration:
        created = await _reuse_terminal_registration(terminal_registration, document)
        await record_event_queue_snapshot(
            event_id=payload.event_id,
            changed_by_user_id=student_user_id,
            source_action='create_event_registration',
        )
        await log_audit_event(
            actor_user_id=student_user_id,
            action='register_event',
            entity_type='event_registration',
            entity_id=str(terminal_registration['_id']),
            detail=(
                f"Re-registered for event {payload.event_id}"
                if document['status'] != 'waitlisted'
                else f"Re-registered for event {payload.event_id} and joined the waitlist"
            ),
        )
        return EventRegistrationOut(**event_registration_public(created))
    persist_public_id(document, kind='event_registration')
    result = await db.event_registrations.insert_one(document)
    public_id = build_public_id('event_registration', {**document, '_id': result.inserted_id}, prefer_existing=False)
    if public_id:
        await db.event_registrations.update_one({'_id': result.inserted_id}, {'$set': {'public_id': public_id}})
    created = await db.event_registrations.find_one({'_id': result.inserted_id})
    await record_event_queue_snapshot(
        event_id=payload.event_id,
        changed_by_user_id=student_user_id,
        source_action='create_event_registration',
    )

    await log_audit_event(
        actor_user_id=student_user_id,
        action='register_event',
        entity_type='event_registration',
        entity_id=str(result.inserted_id),
        detail=(
            f"Registered for event {payload.event_id}"
            if document['status'] != 'waitlisted'
            else f"Registered for event {payload.event_id} and joined the waitlist"
        ),
    )
    return EventRegistrationOut(**event_registration_public(created))


@router.post('/submit', response_model=EventRegistrationOut, status_code=status.HTTP_201_CREATED)
async def submit_event_registration(
    event_id: str = Form(...),
    enrollment_number: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    year: str = Form(...),
    course_branch: str = Form(...),
    class_name: str = Form(...),
    phone_number: str = Form(...),
    whatsapp_number: str = Form(...),
    payment_qr_code: str | None = Form(default=None),
    payment_receipt: UploadFile | None = File(default=None),
    current_user=Depends(require_roles(['student'])),
) -> EventRegistrationOut:
    student_user_id = str(current_user['_id'])
    event = await _validate_and_prepare_registration(event_id, student_user_id)
    _require_payment_reference_if_needed(event, payment_qr_code)
    has_capacity = await _registration_has_capacity(event_id)

    document = {
        'event_id': event_id,
        'student_user_id': student_user_id,
        'enrollment_number': enrollment_number.strip(),
        'full_name': full_name.strip(),
        'email': email.strip(),
        'year': year.strip(),
        'course_branch': course_branch.strip(),
        'class_name': class_name.strip(),
        'phone_number': phone_number.strip(),
        'whatsapp_number': whatsapp_number.strip(),
        'payment_qr_code': payment_qr_code.strip() if payment_qr_code else None,
        'status': _next_active_registration_status(event, has_capacity=has_capacity),
        'attendance_status': None,
        'certificate_issued': False,
        'created_at': datetime.now(timezone.utc),
        'schema_version': EVENT_REGISTRATION_SCHEMA_VERSION,
        'payment_receipt_original_filename': None,
        'payment_receipt_stored_filename': None,
        'payment_receipt_mime_type': None,
        'payment_receipt_size_bytes': None,
    }

    if payment_receipt:
        suffix = Path(payment_receipt.filename or '').suffix.lower()
        if suffix not in ALLOWED_RECEIPT_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported receipt file type. Allowed: png, jpg, jpeg, pdf')

        content = await payment_receipt.read()
        size = len(content)
        if size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded receipt is empty')
        if size > MAX_RECEIPT_SIZE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Receipt file exceeds 10MB limit')

        await run_in_threadpool(RECEIPT_UPLOAD_DIR.mkdir, parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{suffix}"
        saved_path = RECEIPT_UPLOAD_DIR / stored_name
        await run_in_threadpool(saved_path.write_bytes, content)

        document['payment_receipt_original_filename'] = payment_receipt.filename or 'receipt'
        document['payment_receipt_stored_filename'] = stored_name
        document['payment_receipt_mime_type'] = payment_receipt.content_type
        document['payment_receipt_size_bytes'] = size

    terminal_registration = await db.event_registrations.find_one(
        {
            'event_id': event_id,
            'student_user_id': student_user_id,
            'status': {'$in': ['rejected', 'cancelled']},
        }
    )
    if terminal_registration:
        created = await _reuse_terminal_registration(terminal_registration, document)
        await record_event_queue_snapshot(
            event_id=event_id,
            changed_by_user_id=student_user_id,
            source_action='submit_event_registration',
        )
        await log_audit_event(
            actor_user_id=student_user_id,
            action='register_event',
            entity_type='event_registration',
            entity_id=str(terminal_registration['_id']),
            detail=(
                f"Re-registered for event {event_id}"
                if document['status'] != 'waitlisted'
                else f"Re-registered for event {event_id} and joined the waitlist"
            ),
        )
        return EventRegistrationOut(**event_registration_public(created))

    persist_public_id(document, kind='event_registration')
    result = await db.event_registrations.insert_one(document)
    public_id = build_public_id('event_registration', {**document, '_id': result.inserted_id}, prefer_existing=False)
    if public_id:
        await db.event_registrations.update_one({'_id': result.inserted_id}, {'$set': {'public_id': public_id}})
    created = await db.event_registrations.find_one({'_id': result.inserted_id})
    await record_event_queue_snapshot(
        event_id=event_id,
        changed_by_user_id=student_user_id,
        source_action='submit_event_registration',
    )

    await log_audit_event(
        actor_user_id=student_user_id,
        action='register_event',
        entity_type='event_registration',
        entity_id=str(result.inserted_id),
        detail=(
            f"Registered for event {event_id}"
            if document['status'] != 'waitlisted'
            else f"Registered for event {event_id} and joined the waitlist"
        ),
    )
    return EventRegistrationOut(**event_registration_public(created))


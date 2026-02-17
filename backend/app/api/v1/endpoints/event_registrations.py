from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.event_registrations import event_registration_public
from app.schemas.event_registration import EventRegistrationCreate, EventRegistrationOut
from app.services.audit import log_audit_event

router = APIRouter()

RECEIPT_UPLOAD_DIR = Path('uploads/event_registrations')
MAX_RECEIPT_SIZE = 10 * 1024 * 1024
ALLOWED_RECEIPT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf'}


async def _teacher_managed_event_ids(teacher_user_id: str) -> list[str]:
    clubs = await db.clubs.find({'coordinator_user_id': teacher_user_id}).to_list(length=1000)
    club_ids = [str(item.get('_id')) for item in clubs if item.get('_id')]
    if not club_ids:
        return []
    events = await db.club_events.find({'club_id': {'$in': club_ids}}).to_list(length=2000)
    return [str(item.get('_id')) for item in events if item.get('_id')]


async def _validate_and_prepare_registration(event_id: str, student_user_id: str) -> dict:
    event = await db.club_events.find_one({'_id': parse_object_id(event_id)})
    if not event:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Event not found for provided event_id')
    if event.get('status') != 'open':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Event is closed for registration')

    duplicate = await db.event_registrations.find_one({'event_id': event_id, 'student_user_id': student_user_id, 'status': 'registered'})
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Already registered for this event')

    registration_count = await db.event_registrations.count_documents({'event_id': event_id, 'status': 'registered'})
    if registration_count >= int(event.get('capacity', 0)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Event registration capacity reached')

    return event


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
        managed_event_ids = await _teacher_managed_event_ids(teacher_user_id)
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


@router.post('/', response_model=EventRegistrationOut, status_code=status.HTTP_201_CREATED)
async def create_event_registration(
    payload: EventRegistrationCreate,
    current_user=Depends(require_roles(['student'])),
) -> EventRegistrationOut:
    student_user_id = str(current_user['_id'])
    await _validate_and_prepare_registration(payload.event_id, student_user_id)

    document = {
        'event_id': payload.event_id,
        'student_user_id': student_user_id,
        'enrollment_number': payload.enrollment_number,
        'full_name': payload.full_name,
        'email': payload.email,
        'year': payload.year,
        'course_branch': payload.course_branch,
        'section': payload.section,
        'phone_number': payload.phone_number,
        'whatsapp_number': payload.whatsapp_number,
        'payment_qr_code': payload.payment_qr_code,
        'status': 'registered',
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.event_registrations.insert_one(document)
    created = await db.event_registrations.find_one({'_id': result.inserted_id})

    await log_audit_event(
        actor_user_id=student_user_id,
        action='register_event',
        entity_type='event_registration',
        entity_id=str(result.inserted_id),
        detail=f"Registered for event {payload.event_id}",
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
    section: str = Form(...),
    phone_number: str = Form(...),
    whatsapp_number: str = Form(...),
    payment_qr_code: str | None = Form(default=None),
    payment_receipt: UploadFile | None = File(default=None),
    current_user=Depends(require_roles(['student'])),
) -> EventRegistrationOut:
    student_user_id = str(current_user['_id'])
    await _validate_and_prepare_registration(event_id, student_user_id)

    document = {
        'event_id': event_id,
        'student_user_id': student_user_id,
        'enrollment_number': enrollment_number.strip(),
        'full_name': full_name.strip(),
        'email': email.strip(),
        'year': year.strip(),
        'course_branch': course_branch.strip(),
        'section': section.strip(),
        'phone_number': phone_number.strip(),
        'whatsapp_number': whatsapp_number.strip(),
        'payment_qr_code': payment_qr_code.strip() if payment_qr_code else None,
        'status': 'registered',
        'created_at': datetime.now(timezone.utc),
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

        RECEIPT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{suffix}"
        saved_path = RECEIPT_UPLOAD_DIR / stored_name
        saved_path.write_bytes(content)

        document['payment_receipt_original_filename'] = payment_receipt.filename or 'receipt'
        document['payment_receipt_stored_filename'] = stored_name
        document['payment_receipt_mime_type'] = payment_receipt.content_type
        document['payment_receipt_size_bytes'] = size

    result = await db.event_registrations.insert_one(document)
    created = await db.event_registrations.find_one({'_id': result.inserted_id})

    await log_audit_event(
        actor_user_id=student_user_id,
        action='register_event',
        entity_type='event_registration',
        entity_id=str(result.inserted_id),
        detail=f"Registered for event {event_id}",
    )
    return EventRegistrationOut(**event_registration_public(created))


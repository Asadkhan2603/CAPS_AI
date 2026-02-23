from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.security import require_permission

router = APIRouter()


@router.get('/health')
async def admin_system_health(
    _current_user=Depends(require_permission('system.read')),
) -> dict:
    db_status = 'ok'
    try:
        await db.command('ping')
    except Exception:
        db_status = 'error'

    collection_counts = {}
    for name in ['users', 'students', 'assignments', 'submissions', 'evaluations', 'clubs', 'club_events']:
        try:
            collection_counts[name] = await db[name].count_documents({})
        except Exception:
            collection_counts[name] = -1

    return {
        'timestamp': datetime.now(timezone.utc),
        'db_status': db_status,
        'collection_counts': collection_counts,
    }

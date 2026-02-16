from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_audit_logs() -> dict:
    return {'module': 'audit_logs', 'items': []}

from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_notifications() -> dict:
    return {'module': 'notifications', 'items': []}

from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_users() -> dict:
    return {'module': 'users', 'items': []}

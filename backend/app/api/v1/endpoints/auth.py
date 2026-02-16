from fastapi import APIRouter

router = APIRouter()


@router.get('/status')
async def auth_status() -> dict:
    return {'module': 'auth', 'status': 'ready'}

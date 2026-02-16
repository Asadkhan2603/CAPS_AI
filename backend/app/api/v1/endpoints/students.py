from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_students() -> dict:
    return {'module': 'students', 'items': []}

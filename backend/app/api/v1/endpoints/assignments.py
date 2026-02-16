from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_assignments() -> dict:
    return {'module': 'assignments', 'items': []}

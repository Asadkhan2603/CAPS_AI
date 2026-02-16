from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_subjects() -> dict:
    return {'module': 'subjects', 'items': []}

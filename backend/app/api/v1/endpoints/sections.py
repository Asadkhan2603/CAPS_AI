from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_sections() -> dict:
    return {'module': 'sections', 'items': []}

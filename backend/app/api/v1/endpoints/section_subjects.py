from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_section_subjects() -> dict:
    return {'module': 'section_subjects', 'items': []}

from fastapi import APIRouter

router = APIRouter()


@router.get('/')
async def list_evaluations() -> dict:
    return {'module': 'evaluations', 'items': []}

from fastapi import APIRouter

router = APIRouter()


@router.get('/summary')
async def analytics_summary() -> dict:
    return {'module': 'analytics', 'summary': {}}

from fastapi import APIRouter

router = APIRouter()


@router.get('/checks')
async def similarity_checks() -> dict:
    return {'module': 'similarity', 'checks': []}

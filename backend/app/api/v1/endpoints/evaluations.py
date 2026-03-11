from fastapi import APIRouter

from app.core.database import db as core_db

from . import evaluations_ai, evaluations_lifecycle, evaluations_read

db = core_db

router = APIRouter()
router.include_router(evaluations_read.router)
router.include_router(evaluations_ai.router)
router.include_router(evaluations_lifecycle.router)

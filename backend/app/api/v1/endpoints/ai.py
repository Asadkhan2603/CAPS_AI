from fastapi import APIRouter

from . import ai_admin, ai_chat, ai_ops
from app.core.database import db as core_db
from app.services.ai_chat_service import generate_evaluation_chat_reply as _generate_evaluation_chat_reply

db = core_db
generate_evaluation_chat_reply = _generate_evaluation_chat_reply

router = APIRouter()
router.include_router(ai_admin.router)
router.include_router(ai_ops.router)
router.include_router(ai_chat.router)

from typing import List

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.security import require_roles
from app.models.users import user_public
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/", response_model=List[UserOut])
async def list_users(
    _current_user=Depends(require_roles(["admin"])),
) -> List[UserOut]:
    users = await db.users.find({}).to_list(length=1000)
    return [UserOut(**user_public(user)) for user in users]

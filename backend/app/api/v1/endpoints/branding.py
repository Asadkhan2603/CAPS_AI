from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.security import require_roles
from app.core.schema_versions import SETTINGS_SCHEMA_VERSION

router = APIRouter()

BRANDING_DIR = Path("uploads/branding")
MAX_LOGO_SIZE = 2 * 1024 * 1024
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


def _logo_file_path() -> Path | None:
    if not BRANDING_DIR.exists():
        return None
    matches = [path for path in BRANDING_DIR.glob("logo.*") if path.is_file()]
    if not matches:
        return None
    return matches[0]


async def _logo_file_path_async() -> Path | None:
    return await run_in_threadpool(_logo_file_path)


@router.get("/logo/meta")
async def get_logo_meta() -> dict:
    record = await db.settings.find_one({"key": "branding_logo"})
    path = await _logo_file_path_async()
    if not record or not path:
        return {"has_logo": False}
    return {
        "has_logo": True,
        "updated_at": record.get("updated_at"),
        "filename": path.name,
    }


@router.get("/logo")
async def get_logo_file() -> FileResponse:
    path = await _logo_file_path_async()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo not found")
    return FileResponse(path)


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user=Depends(require_roles(["admin"])),
) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_LOGO_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported logo type")

    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded logo is empty")
    if size > MAX_LOGO_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Logo exceeds 2MB limit")

    await run_in_threadpool(BRANDING_DIR.mkdir, parents=True, exist_ok=True)
    for existing in await run_in_threadpool(lambda: list(BRANDING_DIR.glob("logo.*"))):
        if await run_in_threadpool(existing.is_file):
            await run_in_threadpool(existing.unlink)

    saved_name = f"logo{suffix}"
    saved_path = BRANDING_DIR / saved_name
    await run_in_threadpool(saved_path.write_bytes, content)

    now = datetime.now(timezone.utc)
    await db.settings.update_one(
        {"key": "branding_logo"},
        {
            "$set": {
                "key": "branding_logo",
                "filename": saved_name,
                "mime_type": file.content_type,
                "size_bytes": size,
                "updated_at": now,
                "updated_by": str(current_user["_id"]),
                "schema_version": SETTINGS_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )

    return {"message": "Logo uploaded", "filename": saved_name, "updated_at": now}

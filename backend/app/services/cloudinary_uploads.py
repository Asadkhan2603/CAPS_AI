from __future__ import annotations

import os
import re
from typing import Any

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status

from app.core.config import settings

MAX_NOTICE_FILES = 3
MAX_NOTICE_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_NOTICE_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'application/pdf',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


def _configured() -> bool:
    return bool(settings.cloudinary_cloud_name and settings.cloudinary_api_key and settings.cloudinary_api_secret)


def _ensure_configured() -> None:
    if not _configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET.',
        )

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def sanitize_filename(filename: str) -> str:
    base = (filename or 'file').strip()
    base = re.sub(r'[^A-Za-z0-9._ -]+', '_', base)
    return base[:120] or 'file'


async def upload_notice_file(content: bytes, mime_type: str, filename: str) -> dict[str, Any]:
    _ensure_configured()
    if mime_type not in ALLOWED_NOTICE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported file type: {mime_type}',
        )

    resource_type = 'image' if mime_type.startswith('image/') else 'raw'
    public_id = f"notice-{int.from_bytes(os.urandom(4), 'big')}-{int.from_bytes(os.urandom(4), 'big')}"

    upload_options: dict[str, Any] = {
        'folder': 'caps-ai/notices/files',
        'public_id': public_id,
        'resource_type': resource_type,
    }
    if resource_type == 'image':
        upload_options['transformation'] = [{'quality': 'auto'}, {'fetch_format': 'auto'}]

    result = cloudinary.uploader.upload(content, **upload_options)
    return {
        'url': result.get('secure_url') or result.get('url'),
        'public_id': result.get('public_id'),
        'name': sanitize_filename(filename),
        'size': len(content),
        'mime_type': mime_type,
    }


def delete_cloudinary_asset(public_id: str, resource_type: str = 'image') -> None:
    if not public_id or not _configured():
        return
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    cloudinary.uploader.destroy(public_id, resource_type=resource_type)

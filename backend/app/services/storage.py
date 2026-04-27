from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "uploads")).resolve()


def ensure_upload_root() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in value)
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized.strip("-") or "archivo"


def guess_mime_type(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def url_to_path(relative_url: Optional[str]) -> Optional[Path]:
    if not relative_url:
        return None
    clean = relative_url.lstrip("/")
    if not clean.startswith("uploads/"):
        return None
    relative_parts = Path(clean).parts[1:]
    path = (UPLOAD_ROOT / Path(*relative_parts)).resolve()
    try:
        path.relative_to(UPLOAD_ROOT)
    except ValueError:
        return None
    return path


async def save_upload_file(
    *,
    upload: UploadFile,
    category: str,
    prefix: str,
) -> str:
    ensure_upload_root()
    extension = Path(upload.filename or "").suffix or ""
    folder = UPLOAD_ROOT / category
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{_slugify(prefix)}-{uuid4().hex}{extension}"
    destination = folder / filename
    contents = await upload.read()
    destination.write_bytes(contents)
    return f"/uploads/{category}/{filename}"


def delete_relative_url(relative_url: Optional[str]) -> None:
    path = url_to_path(relative_url)
    if path and path.exists():
        path.unlink(missing_ok=True)

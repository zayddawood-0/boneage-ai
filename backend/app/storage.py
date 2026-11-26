"""Local filesystem storage for uploaded X-rays and generated heatmaps.

Hackathon-scope local storage per docs/architecture.md — swap for object
storage later if needed; nothing above this module should know the
difference (callers only see paths/URLs). Files are keyed by the case's
numeric id, matching the `/cases/{id}/...` route style used everywhere else.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from .config import get_settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload_bytes(case_id: int, filename: str, data: bytes) -> Path:
    settings = get_settings()
    case_dir = settings.upload_dir / str(case_id)
    _ensure_dir(case_dir)
    suffix = Path(filename).suffix or ".bin"
    dest = case_dir / f"xray_{uuid.uuid4().hex[:8]}{suffix}"
    dest.write_bytes(data)
    return dest


def save_heatmap_image(case_id: int, image: Image.Image) -> Path:
    settings = get_settings()
    case_dir = settings.upload_dir / str(case_id)
    _ensure_dir(case_dir)
    dest = case_dir / "heatmap.png"
    image.save(dest)
    return dest


def heatmap_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/heatmap"


def heatmap_path_for_case(case_id: int) -> Path:
    settings = get_settings()
    return settings.upload_dir / str(case_id) / "heatmap.png"

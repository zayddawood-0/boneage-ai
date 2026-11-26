"""Local filesystem storage for uploaded X-rays and generated images.

Hackathon-scope local storage per docs/architecture.md — swap for object
storage later if needed; nothing above this module should know the
difference (callers only see paths/URLs). Files are keyed by the case's
numeric id, matching the `/cases/{id}/...` route style used everywhere else.

Three derived images per case, all the same size (see
backend/app/inference_adapter.py / ml/boneage/inference.py):
- display.png   — the plain preprocessed X-ray alone (RGB)
- heatmap_layer.png — the Grad-CAM heatmap alone (RGBA, transparent where
  there's no attention) — real or a visibly-marked mock, see inference_adapter.py
- heatmap.png   — the two pre-blended into one flat image, used for the PDF
  report (GET /cases/{id}/report.pdf) and kept for backward compatibility
"""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image

from .config import get_settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _case_dir(case_id: int) -> Path:
    settings = get_settings()
    case_dir = settings.upload_dir / str(case_id)
    _ensure_dir(case_dir)
    return case_dir


def save_upload_bytes(case_id: int, filename: str, data: bytes) -> Path:
    case_dir = _case_dir(case_id)
    suffix = Path(filename).suffix or ".bin"
    dest = case_dir / f"xray_{uuid.uuid4().hex[:8]}{suffix}"
    dest.write_bytes(data)
    return dest


def save_heatmap_image(case_id: int, image: Image.Image) -> Path:
    dest = _case_dir(case_id) / "heatmap.png"
    image.save(dest)
    return dest


def save_display_image(case_id: int, image: Image.Image) -> Path:
    dest = _case_dir(case_id) / "display.png"
    image.save(dest)
    return dest


def save_heatmap_layer_image(case_id: int, image: Image.Image) -> Path:
    dest = _case_dir(case_id) / "heatmap_layer.png"
    image.save(dest)
    return dest


def heatmap_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/heatmap"


def image_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/image"


def heatmap_layer_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/heatmap-layer"


def heatmap_path_for_case(case_id: int) -> Path:
    return _case_dir(case_id) / "heatmap.png"


def display_image_path_for_case(case_id: int) -> Path:
    return _case_dir(case_id) / "display.png"


def heatmap_layer_path_for_case(case_id: int) -> Path:
    return _case_dir(case_id) / "heatmap_layer.png"

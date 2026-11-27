"""Image storage for uploaded X-rays and generated heatmaps.

Two backends, selected automatically by whether `BLOB_READ_WRITE_TOKEN` is
set (see `config.py`'s `Settings.use_blob_storage`) — nothing above this
module needs to know which one is active:

- **Local disk** (default, used for local dev and tests) — files under
  `UPLOAD_DIR`, keyed by the case's numeric id.
- **Vercel Blob** (production, see docs/architecture.md#deployment-notes) —
  blobs stored `access="private"` (never a public URL — the frontend
  reaches images only through the backend's own, already-authenticated
  `/cases/{id}/...` endpoints, same as the local-disk path, see
  `backend/app/routers/cases.py`), via the official `vercel-blob` Python SDK.

Either way, every `save_*` function returns an opaque string "handle" —
a local filesystem path, or a Blob pathname — meant to be stored verbatim
in the `Case` row's `*_path` column and handed back unchanged to
`read_case_image_bytes`/`delete_case_image`. Callers never need an `if
local/blob` branch of their own.

Three derived images per case, all the same size (see
backend/app/inference_adapter.py / ml/boneage/inference.py):
- display.png   — the plain preprocessed X-ray alone (RGB)
- heatmap_layer.png — the attention heatmap alone (RGBA, transparent where
  there's no attention) — real or a visibly-marked mock, see inference_adapter.py
- heatmap.png   — the two pre-blended into one flat image, used for the PDF
  report (GET /cases/{id}/report.pdf) and kept for backward compatibility

All three are fixed filenames per case (re-predicting the same case
overwrites them) — the frontend's opacity/side-by-side viewer only ever
re-renders the already-stored images client-side, it never triggers a
backend recompute (see backend/app/routers/cases.py's `predict_case`, the
only place these are written).
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image

from .config import get_settings


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# ---- local disk backend ----


def _local_case_dir(case_id: int) -> Path:
    settings = get_settings()
    case_dir = settings.upload_dir / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


def _local_save(case_id: int, filename: str, data: bytes) -> str:
    dest = _local_case_dir(case_id) / filename
    dest.write_bytes(data)
    return str(dest)


def _local_read(handle: str) -> bytes | None:
    path = Path(handle)
    if not path.exists():
        return None
    return path.read_bytes()


def _local_delete(handle: str) -> None:
    path = Path(handle)
    if path.exists():
        path.unlink()


# ---- Vercel Blob backend ----


def _blob_pathname(case_id: int, filename: str) -> str:
    return f"cases/{case_id}/{filename}"


def _blob_save(case_id: int, filename: str, data: bytes, content_type: str | None = None) -> str:
    from vercel.blob import sync as blob

    result = blob.put_blob(
        _blob_pathname(case_id, filename),
        data,
        access="private",
        content_type=content_type,
        allow_overwrite=True,
    )
    return result.pathname


def _blob_read(handle: str) -> bytes | None:
    from vercel.blob import sync as blob

    try:
        result = blob.get_blob(handle, access="private")
    except blob.BlobNotFoundError:
        return None
    return result.body


def _blob_delete(handle: str) -> None:
    from vercel.blob import sync as blob

    blob.delete_blob(handle)  # deleting an already-missing blob succeeds (SDK docs)


# ---- dispatch ----


def _save(case_id: int, filename: str, data: bytes, content_type: str | None = None) -> str:
    if get_settings().use_blob_storage:
        return _blob_save(case_id, filename, data, content_type)
    return _local_save(case_id, filename, data)


# ---- public API ----


def save_upload_bytes(case_id: int, filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix or ".bin"
    unique_name = f"xray_{uuid.uuid4().hex[:8]}{suffix}"
    return _save(case_id, unique_name, data)


def save_heatmap_image(case_id: int, image: Image.Image) -> str:
    return _save(case_id, "heatmap.png", _image_to_png_bytes(image), content_type="image/png")


def save_display_image(case_id: int, image: Image.Image) -> str:
    return _save(case_id, "display.png", _image_to_png_bytes(image), content_type="image/png")


def save_heatmap_layer_image(case_id: int, image: Image.Image) -> str:
    return _save(case_id, "heatmap_layer.png", _image_to_png_bytes(image), content_type="image/png")


def read_case_image_bytes(handle: str | None) -> bytes | None:
    """`handle` is whatever a `save_*` function above returned (or `None`,
    e.g. a case that hasn't been predicted/uploaded yet) — reads it back
    through whichever backend produced it."""
    if not handle:
        return None
    if get_settings().use_blob_storage:
        return _blob_read(handle)
    return _local_read(handle)


def delete_case_image(handle: str | None) -> None:
    """Used by the data-retention cleanup task (app/retention.py) — a no-op
    if `handle` is already `None`."""
    if not handle:
        return
    if get_settings().use_blob_storage:
        _blob_delete(handle)
    else:
        _local_delete(handle)


def heatmap_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/heatmap"


def image_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/image"


def heatmap_layer_url_for_case(case_id: int) -> str:
    return f"/cases/{case_id}/heatmap-layer"

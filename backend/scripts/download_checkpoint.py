#!/usr/bin/env python
"""Downloads the trained model checkpoint from CHECKPOINT_DOWNLOAD_URL (if
set) to ML_CHECKPOINT_PATH before the API starts. The checkpoint itself is
gitignored (see ml/README.md), so a host with an ephemeral filesystem
(Render's free tier) needs this on every deploy.

Never fatal: if the env var is unset, the URL is unreachable, or the
download fails for any reason, this prints a warning and exits 0.
app/inference_adapter.py already falls back to a clearly-labelled mock
predictor (the "Demo model" chip in the frontend) whenever no checkpoint
file exists at that path — which is the correct, hackathon-safe behaviour
(see docs/safety-and-ethics.md) — so a failed download must never crash
startup.

Usage (as a Render start-command step; see render.yaml):
    python backend/scripts/download_checkpoint.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    url = settings.checkpoint_download_url
    dest = settings.ml_checkpoint_path

    if not url:
        print(
            "CHECKPOINT_DOWNLOAD_URL not set — skipping checkpoint download; "
            "the API will use the mock predictor."
        )
        return

    if dest.exists():
        print(f"Checkpoint already present at {dest} — skipping download.")
        return

    tmp_dest = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, tmp_dest)  # noqa: S310 - trusted, operator-configured URL
        tmp_dest.rename(dest)
        print(f"Downloaded model checkpoint to {dest}.")
    except Exception as exc:  # noqa: BLE001 - startup must never fail over this
        tmp_dest.unlink(missing_ok=True)
        print(f"Could not download model checkpoint ({exc}) — falling back to the mock predictor.")


if __name__ == "__main__":
    main()

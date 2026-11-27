"""Vercel Python Function entrypoint.

Vercel's builder looks for Serverless Functions under `api/` and matches
them against `vercel.json`'s `functions` key (see `backend/vercel.json`) —
this file just re-exports the real FastAPI app (`app/main.py`) so Vercel has
something to find there; all the actual routes/logic live in `app/`, same as
running `uvicorn app.main:app` locally (see backend/README.md).
"""
from app.main import app  # noqa: F401

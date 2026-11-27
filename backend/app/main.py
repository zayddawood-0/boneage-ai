"""BoneAge AI backend — FastAPI app. See docs/api.md, docs/architecture.md.

This is decision support only — never a diagnosis. See
docs/safety-and-ethics.md.

Before running: `alembic upgrade head` from backend/ to create the schema
(SQLite for the hackathon — see docs/architecture.md). See backend/README.md.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from .config import get_settings
from .database import engine
from .routers import auth, cases, model_performance, patients, settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        logger.warning(
            "Database schema not found. Run `alembic upgrade head` from backend/ "
            "before using the API — see backend/README.md."
        )
    yield


app = FastAPI(
    title="BoneAge AI API",
    description=(
        "Decision support only — never a diagnosis. See docs/safety-and-ethics.md "
        "in the repo for the full disclaimer."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Local dev talks to the backend through the Vite proxy (same origin, no CORS
# needed) — this only matters once frontend and backend are on separate
# origins (Vercel + Render, see docs/architecture.md#deployment-notes).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(cases.router)
app.include_router(settings.router)
app.include_router(model_performance.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}

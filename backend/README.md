# backend/ — BoneAge AI API

FastAPI backend implementing [docs/api.md](../docs/api.md) and [docs/architecture.md](../docs/architecture.md): auth + roles, patients, cases, X-ray upload, prediction, the growth review agent, doctor decisions, PDF export, and settings. SQLite for local dev/tests, Postgres (Neon) in production, both managed with the same Alembic migrations (see [docs/tasks.md](../docs/tasks.md)). Deploys as a Vercel Python Function — see [Deployment](#deployment-vercel) below.

**This is decision support only — never a diagnosis.** See [../docs/safety-and-ethics.md](../docs/safety-and-ethics.md).

## What's here

```
backend/
├── app/
│   ├── main.py              # FastAPI app + routers + CORS
│   ├── config.py             # Settings (env vars / .env)
│   ├── database.py            # SQLAlchemy engine/session; Postgres URL normalisation
│   ├── models.py               # ORM models (User, Patient, Case, GrowthReviewSettings)
│   ├── schemas.py               # Pydantic request/response shapes
│   ├── security.py               # password hashing + JWT
│   ├── deps.py                    # auth + role-based access control
│   ├── codes.py                     # BA-xxxx / P-xxxx code generation
│   ├── serializers.py                # ORM -> response shaping
│   ├── storage.py                     # image storage: local disk or Vercel Blob
│   ├── quality.py                      # image quality check heuristics
│   ├── inference_adapter.py             # real ml/boneage/onnx_inference.py, or a labelled mock
│   ├── pdf.py                             # case report PDF export
│   ├── settings_store.py                   # the singleton GrowthReviewSettings row
│   ├── retention.py                          # data-retention cleanup (deletes expired images/heatmaps)
│   ├── agent/                                # the growth review agent — see AGENTS.md
│   │   ├── tools.py                           # deterministic flag decision
│   │   ├── reference_table.py                  # SD-based reference table loader
│   │   ├── note_writer.py                       # the one LLM-authored step (+ template fallback)
│   │   └── review.py                              # orchestrates the above
│   └── routers/                                     # auth, patients, cases, settings, model_performance, internal
├── migrations/                 # Alembic — see "Database" below
├── data/reference_tables/        # greulich_pyle_sd_reference.json — EMPTY [TBD] template, see below
├── scripts/
│   ├── seed_demo_data.py            # demo users + BA-1037..1042 sample cases
│   └── cleanup_retention.py           # manual/local-dev equivalent of the Vercel Cron job
├── tests/                             # pytest — see "Tests" below
├── alembic.ini, pytest.ini
├── api/index.py                        # Vercel Function entrypoint — re-exports app/main.py's app
├── vercel.json, .python-version       # Vercel Python Function config — see "Deployment" below
├── requirements.txt                    # what Vercel actually deploys — torch-free, see below
├── requirements-dev.txt                 # + test-only extras (torch, for test_inference_adapter.py)
└── .env.example
```

## Setup

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # defaults work for local dev as-is
cd backend
alembic upgrade head                   # creates the schema (SQLite by default)
python scripts/seed_demo_data.py       # optional: demo users + sample cases
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for the interactive Swagger UI (or **/redoc**).

Demo login (only if you ran the seed script): `doctor@boneage.ai` / `radiographer@boneage.ai` / `admin@boneage.ai`, all with password `demo-password`.

## Database (SQLite locally, Postgres in production — Alembic migrations)

Schema changes go through Alembic, not `Base.metadata.create_all()`:

```bash
cd backend
alembic upgrade head                                   # apply migrations
alembic revision --autogenerate -m "add some_column"    # after changing app/models.py
alembic downgrade -1                                      # roll back one step
```

`DATABASE_URL` (backend/.env) controls where — defaults to `sqlite:///./backend/boneage.db`, gitignored. In production this is a Postgres connection string (Neon, via the Vercel Marketplace — see [Deployment](#deployment-vercel)); a bare `postgres://` or `postgresql://` URL is normalised to use the `psycopg` driver automatically (`app/database.py`'s `normalize_database_url`, applied the same way in `migrations/env.py` so `alembic upgrade head` and the running app always agree).

## Real model vs. mock predictor

`POST /cases/{id}/predict` calls [`ml/boneage/onnx_inference.py`](../ml/boneage/onnx_inference.py) (ONNX Runtime — no `torch`/`torchvision` at request time, see [docs/architecture.md#deployment-notes](../docs/architecture.md#deployment-notes) for why) if an exported model exists at `ML_ONNX_DIR` (see [ml/README.md](../ml/README.md) — no real training has been run yet, see [docs/model.md](../docs/model.md)). If it doesn't, the API transparently falls back to a clearly-labelled mock predictor (`app/inference_adapter.py`) so the app is demoable before training finishes. Every prediction response includes `prediction_source: "real" | "mock"` — the mock path also always carries a deliberately wide uncertainty, so the growth review agent flags mock results as `"uncertain"` rather than letting them look like a trusted real measurement.

It generates three same-sized images per case (`app/storage.py`): `GET /cases/{id}/heatmap` (pre-blended, for the PDF), `GET /cases/{id}/image` (the plain X-ray alone — always real, even in mock mode), and `GET /cases/{id}/heatmap-layer` (the heatmap alone, transparent PNG, so the frontend can composite the two independently — adjustable opacity, side-by-side view). In mock mode only the heatmap layer is fabricated (a visibly-marked flat amber tint + "MOCK HEATMAP" text), never the X-ray itself. The heatmap itself is Grad-CAM when running the PyTorch model directly (training/evaluation), Score-CAM on this ONNX path — see [docs/model.md#explainability](../docs/model.md#explainability).

## Image storage: local disk or Vercel Blob

`app/storage.py` picks automatically, based on whether Blob is configured (`BLOB_STORE_ID` — set by `vercel storage connect`, OIDC credentials, no static token — or `BLOB_READ_WRITE_TOKEN`): local disk under `UPLOAD_DIR` (local dev/tests default) or Vercel Blob (production). Either way every `save_*` function returns an opaque string "handle" stored in the `Case` row's `*_path` column; callers (`routers/cases.py`, `app/pdf.py`, `app/retention.py`) never need to know which backend produced it. Blobs are stored `access="private"` — the frontend only ever reaches images through the backend's own authenticated endpoints, same as local disk.

## CORS (deployment)

Locally, the frontend talks to the backend through the Vite dev proxy (same origin, no CORS needed). Once frontend and backend are on separate origins (two Vercel projects), the backend needs `CORS_ORIGIN` (backend/.env, comma-separated) set to the frontend's URL — enforced in `app/main.py` via `CORSMiddleware`.

## Model delivery (deployment)

The exported ONNX model (`ml/export_onnx.py`'s output directory) is gitignored, like the old `.pt` checkpoint. Since Vercel's Python Functions have no pre-start hook to run a download step from ahead of time, `app/inference_adapter.py` fetches it lazily — on the first real prediction request after a cold start — from `ONNX_DOWNLOAD_URL` if set (a zip containing `backbone.onnx`, `head_part1.onnx`, `head_part2.onnx`, `metadata.json` at its root). This never fails the request: if the URL is unset or the download fails, it falls back to the mock predictor, same as local dev without an exported model, and only tries once per cold start (not on every request).

**Caching in `/tmp`:** the deployed function's own filesystem is read-only — only `/tmp` is writable, and it persists across invocations handled by the same warm instance (reset on the next cold start). `ML_ONNX_DIR` defaults to `/tmp/boneage-onnx` automatically on Vercel (detected via `VERCEL=1`, which Vercel sets itself — see `app/config.py`), so a warm function reuses the already-downloaded model instead of re-fetching it on every request; only a genuine cold start pays the download cost.

**Cold-start timing:** `vercel.json` sets `maxDuration: 90` for the whole app — comfortably above a worst-case cold start (ONNX Runtime import, a model download if `/tmp` is empty, 20 MC-dropout passes, and Score-CAM's ~32 extra masked forward passes), without claiming the Hobby plan's full ceiling. With [Fluid compute](https://vercel.com/docs/fluid-compute) (default for new Vercel projects), Hobby's default **and** maximum `maxDuration` is 300s — Pro/Enterprise can go to 800s (or 1800s in beta) — so 90s leaves ample headroom; raise it if cold-start predictions ever time out in practice.

## Data retention cleanup

Deletes the X-ray image and heatmap files (local disk or Blob — and clears the matching DB path columns) for any case older than the configured `retention_days` (Settings > Data & privacy, default 30 — see [docs/safety-and-ethics.md](../docs/safety-and-ethics.md#privacy)). The case record itself (prediction, flag status, doctor decision) is kept for review history; only the images are removed, and `GET /cases/{id}/image` etc. 404 afterwards.

In production this runs automatically via **Vercel Cron** (`vercel.json`'s `crons`, daily) calling `GET /internal/retention-cleanup` (`app/routers/internal.py`), guarded by a shared secret (`CRON_SECRET`) rather than a user JWT, since Vercel sends it as `Authorization: Bearer <CRON_SECRET>` on every cron invocation. `backend/scripts/cleanup_retention.py` is the manual/local-dev equivalent — useful for testing the cleanup logic without waiting for the schedule:

```bash
cd backend
python scripts/cleanup_retention.py
```

## The growth review agent

See [AGENTS.md](../AGENTS.md#the-growth-review-agent) for the full spec. In short: `app/agent/tools.py` makes the flag decision in plain, deterministic Python (never the LLM); `app/agent/note_writer.py` is the one LLM-authored step (OpenAI Agents SDK, only ever given structured numbers/labels — never the image or patient name), falling back to a fixed template note when `OPENAI_API_KEY` is unset or the call fails.

**SD-based reference table:** `data/reference_tables/greulich_pyle_sd_reference.json` ships as an **empty `[TBD — to verify]` template** — no SD values have been filled in. Until it's populated, selecting the "sd" rule type in Settings will make every case come back `flag_status: "needs_review"` (`gap_direction: "uncertain"`) rather than guess at a normal range. The "fixed_months" rule type (± N months around chronological age) works immediately and is the default.

## Deployment (Vercel)

The backend deploys as its own Vercel project (Root Directory `backend`), separate from the frontend's. `api/index.py` re-exports `app/main.py`'s FastAPI `app` — Vercel's Python builder looks for Serverless Functions under `api/` — and `vercel.json` routes every path to it (`rewrites`), sets `maxDuration`, and adds the retention-cleanup cron schedule; `.python-version` pins the runtime. No Docker.

Three things worth knowing:
- **Always run `vercel link`/`pull`/`build`/`deploy` from the repo root, never from inside `backend/`** (as a shell `cd` or `--cwd`). The CLI combines the project's Root Directory setting with the directory it's invoked from, so running it from inside `backend/` produces an invalid doubled path (`backend/backend`) and fails — confirmed by actually hitting this. `.github/workflows/deploy.yml`'s Vercel CLI steps have no `working-directory:` override for exactly this reason.
- **The backend imports `ml/boneage/*` from the sibling `ml/` directory at runtime** (`sys.path` manipulation in `app/inference_adapter.py`) — this only works if the Vercel project's "Include files outside the Root Directory in the Build Step" setting stays enabled (it's the default; see [README.md#deployment-setup-vercel--github-actions](../README.md#deployment-setup-vercel--github-actions)).
- **`requirements.txt` is what Vercel actually installs and deploys** — it's deliberately torch-free (ONNX Runtime only) to stay under Vercel's 500 MB uncompressed Python Function limit (`torch`+`torchvision` alone measure ~750 MB — see [docs/architecture.md#deployment-notes](../docs/architecture.md#deployment-notes)). `requirements-dev.txt` adds `torch`/`torchvision`/`pandas`/`matplotlib`/`onnx` back on top, for the test suite only (`test_inference_adapter.py` trains and ONNX-exports a tiny throwaway checkpoint) — never installed in production.

## Tests

```bash
pip install -r backend/requirements-dev.txt   # not requirements.txt — see above
cd backend
pytest
```

Each test run gets its own temp SQLite database, migrated with the real Alembic chain (not `create_all`). Covers: the agent's deterministic rules at threshold boundaries (both sexes, delayed/advanced/uncertain, both rule types), that no image or patient-identifying value ever reaches the LLM payload, role-based access on every endpoint, the real-vs-mock inference adapter (training a tiny throwaway checkpoint and ONNX-exporting it the same way `ml/tests` does, to exercise the "real" path honestly), the full upload → predict → agent-review → doctor-decision → PDF-export flow, the retention cleanup task (expired cases lose their images, recent cases and already-cleaned cases are left alone), the storage backend dispatch (local disk and a faked Vercel Blob module, no real network/credentials needed), and the Postgres URL normalisation.

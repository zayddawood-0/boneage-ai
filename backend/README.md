# backend/ — BoneAge AI API

FastAPI backend implementing [docs/api.md](../docs/api.md) and [docs/architecture.md](../docs/architecture.md): auth + roles, patients, cases, X-ray upload, prediction, the growth review agent, doctor decisions, PDF export, and settings. SQLite for the hackathon, managed with Alembic migrations (see [docs/tasks.md](../docs/tasks.md)).

**This is decision support only — never a diagnosis.** See [../docs/safety-and-ethics.md](../docs/safety-and-ethics.md).

## What's here

```
backend/
├── app/
│   ├── main.py              # FastAPI app + routers
│   ├── config.py             # Settings (env vars / .env)
│   ├── database.py            # SQLAlchemy engine/session
│   ├── models.py               # ORM models (User, Patient, Case, GrowthReviewSettings)
│   ├── schemas.py               # Pydantic request/response shapes
│   ├── security.py               # password hashing + JWT
│   ├── deps.py                    # auth + role-based access control
│   ├── codes.py                     # BA-xxxx / P-xxxx code generation
│   ├── serializers.py                # ORM -> response shaping
│   ├── storage.py                     # local image/heatmap storage
│   ├── quality.py                      # image quality check heuristics
│   ├── inference_adapter.py             # real ml/boneage/inference.py, or a labelled mock
│   ├── pdf.py                             # case report PDF export
│   ├── settings_store.py                   # the singleton GrowthReviewSettings row
│   ├── agent/                                # the growth review agent — see AGENTS.md
│   │   ├── tools.py                           # deterministic flag decision
│   │   ├── reference_table.py                  # SD-based reference table loader
│   │   ├── note_writer.py                       # the one LLM-authored step (+ template fallback)
│   │   └── review.py                              # orchestrates the above
│   └── routers/                                     # auth, patients, cases, settings, model_performance
├── migrations/                 # Alembic — see "Database" below
├── data/reference_tables/        # greulich_pyle_sd_reference.json — EMPTY [TBD] template, see below
├── scripts/seed_demo_data.py       # demo users + BA-1037..1042 sample cases
├── tests/                             # pytest — see "Tests" below
├── alembic.ini, pytest.ini
├── requirements.txt
└── .env.example
```

## Setup

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # defaults work for local dev as-is
cd backend
alembic upgrade head                   # creates the SQLite schema
python scripts/seed_demo_data.py       # optional: demo users + sample cases
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for the interactive Swagger UI (or **/redoc**).

Demo login (only if you ran the seed script): `doctor@boneage.ai` / `radiographer@boneage.ai` / `admin@boneage.ai`, all with password `demo-password`.

## Database (SQLite + Alembic migrations)

Schema changes go through Alembic, not `Base.metadata.create_all()`:

```bash
cd backend
alembic upgrade head                                   # apply migrations
alembic revision --autogenerate -m "add some_column"    # after changing app/models.py
alembic downgrade -1                                      # roll back one step
```

`DATABASE_URL` (backend/.env) controls where — defaults to `sqlite:///./backend/boneage.db`, gitignored.

## Real model vs. mock predictor

`POST /cases/{id}/predict` calls [`ml/boneage/inference.py`](../ml/boneage/inference.py) if a trained checkpoint exists at `ML_CHECKPOINT_PATH` (see [ml/README.md](../ml/README.md) — no real training has been run yet, see [docs/model.md](../docs/model.md)). If it doesn't, the API transparently falls back to a clearly-labelled mock predictor (`app/inference_adapter.py`) so the app is demoable before training finishes. Every prediction response includes `prediction_source: "real" | "mock"` — the mock path also always carries a deliberately wide uncertainty, so the growth review agent flags mock results as `"uncertain"` rather than letting them look like a trusted real measurement.

It generates three same-sized images per case (`app/storage.py`): `GET /cases/{id}/heatmap` (pre-blended, for the PDF), `GET /cases/{id}/image` (the plain X-ray alone — always real, even in mock mode), and `GET /cases/{id}/heatmap-layer` (the heatmap alone, transparent PNG, so the frontend can composite the two independently — adjustable opacity, side-by-side view). In mock mode only the heatmap layer is fabricated (a visibly-marked flat amber tint + "MOCK HEATMAP" text), never the X-ray itself.

## The growth review agent

See [AGENTS.md](../AGENTS.md#the-growth-review-agent) for the full spec. In short: `app/agent/tools.py` makes the flag decision in plain, deterministic Python (never the LLM); `app/agent/note_writer.py` is the one LLM-authored step (OpenAI Agents SDK, only ever given structured numbers/labels — never the image or patient name), falling back to a fixed template note when `OPENAI_API_KEY` is unset or the call fails.

**SD-based reference table:** `data/reference_tables/greulich_pyle_sd_reference.json` ships as an **empty `[TBD — to verify]` template** — no SD values have been filled in. Until it's populated, selecting the "sd" rule type in Settings will make every case come back `flag_status: "needs_review"` (`gap_direction: "uncertain"`) rather than guess at a normal range. The "fixed_months" rule type (± N months around chronological age) works immediately and is the default.

## Tests

```bash
cd backend
pytest
```

Each test run gets its own temp SQLite database, migrated with the real Alembic chain (not `create_all`). Covers: the agent's deterministic rules at threshold boundaries (both sexes, delayed/advanced/uncertain, both rule types), that no image or patient-identifying value ever reaches the LLM payload, role-based access on every endpoint, the real-vs-mock inference adapter (training a tiny throwaway checkpoint the same way `ml/tests` does, to exercise the "real" path honestly), and the full upload → predict → agent-review → doctor-decision → PDF-export flow.

# CLAUDE.md

Context for Claude Code sessions working in this repository. Keep this file in sync with [AGENTS.md](AGENTS.md) — they should never contradict each other. If you update one, check the other.

## What this project is

**BoneAge AI** (working name) is a hackathon healthcare project. A CNN trained on the RSNA Bone Age dataset estimates a child's bone age from a left-hand X-ray (using the child's sex as an extra input) and compares it with chronological age computed from date of birth and X-ray date. A **growth review agent** flags cases where the gap falls outside a configurable normal range and writes a short note for a doctor explaining what to check. A doctor always makes the final call.

**This is decision support only — never a diagnosis.** Any code, copy, log message, or docstring that implies the system diagnoses a condition is a bug. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md).

Full product description: [README.md](README.md). Requirements: [docs/requirements.md](docs/requirements.md).

## Current state

`ml/`, `backend/`, and `frontend/` all have real code now, plus CI/CD (`.github/workflows/`) and deployment config (`backend/vercel.json`, `frontend/vercel.json` — both deploy to Vercel, no Render).

- **`ml/`** — the RSNA data pipeline (config, preprocessing, augmentation, `Dataset`/`DataLoader`) and the model itself (architecture, training loop, evaluation, Grad-CAM, MC-dropout inference, ONNX export, a Kaggle training notebook), with unit tests. See [ml/README.md](ml/README.md). **No real training has been run yet** — every metric in [docs/model.md](docs/model.md) is still `[TBD]`; do not fill those in until a real checkpoint has actually been trained and evaluated and the numbers copied in by hand.
- **`backend/`** — a working FastAPI app: auth + role-based access control, patients, cases, upload + image quality checks, prediction (real via ONNX Runtime if an exported model exists — see [docs/model.md#explainability](docs/model.md#explainability) for why ONNX, not PyTorch — otherwise a clearly-labelled mock), the growth review agent (deterministic rules + OpenAI-Agents-SDK note-writing with a template fallback), doctor decisions, PDF export, settings, a data-retention cleanup task (runs via Vercel Cron in production), and a demo-data seed script. SQLite (local dev/tests) or Postgres (Neon, production) via the same Alembic migrations; local disk or Vercel Blob for images. CORS configured for a deployed frontend origin. See [backend/README.md](backend/README.md). The SD-based reference table is an intentionally empty `[TBD — to verify]` template — no SD values have been filled in.
- **`frontend/`** — a React + TypeScript + Vite + Tailwind app translating every `design/` screen pixel-for-pixel: sign in, dashboard, new analysis, review queue, case report, patients, model performance, settings. See [frontend/README.md](frontend/README.md).
- **CI/CD** — GitHub Actions run the ml/backend/frontend test suites and the frontend build on every push/PR (`.github/workflows/ci.yml`); a deploy workflow (`.github/workflows/deploy.yml`) applies DB migrations and deploys both the frontend and backend to Vercel (two separate projects) after CI passes on `main`. See [README.md#deployment-setup-vercel--github-actions](README.md#deployment-setup-vercel--github-actions).

Check the repo layout below before assuming a path exists.

## Repo layout (planned)

```
/
├── CLAUDE.md                 # this file
├── AGENTS.md                 # agent guidance (coding agents + the in-product growth review agent)
├── README.md                 # project overview
├── docs/
│   ├── requirements.md       # functional + non-functional requirements, user stories
│   ├── design.md              # UI/UX spec: screens, states, design tokens, accessibility
│   ├── architecture.md       # system components, data flow, Mermaid diagram, deployment
│   ├── data.md                # datasets, fields, splits, preprocessing, licensing
│   ├── model.md               # model architecture, training plan, metrics, model card
│   ├── api.md                  # REST endpoints and payloads
│   ├── tasks.md                # implementation phases, task breakdown
│   ├── testing.md              # test strategy, demo script
│   └── safety-and-ethics.md   # disclaimer, bias, privacy, human-in-the-loop
├── design/                    # APPROVED UI design — frontend must match these files exactly (see below)
├── backend/                   # FastAPI app — real code, see backend/README.md
│   ├── app/                    # routers, models, agent/ (growth review agent), inference_adapter, storage, etc.
│   ├── migrations/              # Alembic (SQLite or Postgres)
│   ├── data/reference_tables/    # SD reference table — empty [TBD] template
│   ├── scripts/                   # seed_demo_data.py, cleanup_retention.py (manual/local-dev)
│   ├── vercel.json, .python-version  # Vercel Python Function config
│   └── tests/                      # pytest — real DB via migrations, no network/LLM needed
├── frontend/                  # React + TypeScript + Vite + Tailwind app, see frontend/README.md
├── ml/                         # data pipeline + model — real code, see ml/README.md
│   ├── boneage/                # config, seed, splits, transforms, datasets, dataloaders, model,
│   │                            # metrics, training, evaluation, gradcam, inference (PyTorch);
│   │                            # onnx_export, onnx_inference, numpy_transforms, score_cam,
│   │                            # colormap, prediction_result (torch-free ONNX inference path)
│   ├── config/                 # config.example.yaml (tracked) / config.yaml (gitignored, local paths)
│   ├── notebooks/               # train_kaggle.ipynb — GPU training/evaluation on Kaggle
│   ├── train.py / evaluate.py    # CLI entry points
│   ├── export_onnx.py             # exports a trained checkpoint to ONNX (see onnx_export.py)
│   ├── compare_heatmaps.py         # Grad-CAM vs Score-CAM side-by-side sanity check
│   └── tests/                  # unit tests against a small fake dataset — no real data needed
└── .gitignore                 # excludes datasets, model weights, uploads, .env
```

## Frontend design (locked)

The approved UI design for every screen lives in `design/` (see `design/README.md` for how to read the files, and [docs/design.md](docs/design.md#design-file-map) for the file-to-screen-to-route mapping).

> The frontend must match the files in design/ exactly: same layout, spacing, sizes, colours, fonts (IBM Plex Sans and IBM Plex Mono), copy, icons, states and light/dark themes. Use the LIGHT and DARK token strings in each file's renderVals() as the theme CSS variables. Do not redesign, restyle or "improve" any screen. If something in design/ is unclear or cannot be built as drawn, ask before changing it.

## How to run things

**ML tests** (real, works today — no dataset download or network access required; uses a small fake dataset and `pretrained=False` models):
```bash
pip install -r ml/requirements.txt
pytest ml
```

**Train/evaluate the model locally** (CPU or GPU) — requires the real RSNA dataset and `ml/config/config.yaml` filled in (copy from `ml/config/config.example.yaml`; see [docs/data.md](docs/data.md)):
```bash
python ml/train.py --config ml/config/config.yaml
python ml/evaluate.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt
```

**Train on Kaggle (GPU):** see `ml/notebooks/train_kaggle.ipynb` and [ml/README.md](ml/README.md#training-on-kaggle).

**Export a trained checkpoint to ONNX** (what the deployed backend actually runs — see [docs/model.md#explainability](docs/model.md#explainability) for why):
```bash
python ml/export_onnx.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --out-dir ml/checkpoints/onnx
python ml/compare_heatmaps.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --onnx-dir ml/checkpoints/onnx --out-dir ml/results/heatmap_comparison
```

**Backend API** (see [backend/README.md](backend/README.md) for full details):
```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
alembic upgrade head                   # creates the schema (SQLite by default; Postgres if DATABASE_URL is set)
python scripts/seed_demo_data.py       # optional: demo users + BA-1037..1042 sample cases
uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000/docs for the Swagger UI.

**Backend tests** (real, works today — own temp SQLite DB per run, migrated with Alembic, no network/LLM calls needed; trains + ONNX-exports a tiny throwaway checkpoint, so install `backend/requirements-dev.txt`, not `requirements.txt`, to run these):
```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest
```

**Frontend** (see [frontend/README.md](frontend/README.md) for full details):
```bash
cd frontend
npm install
npm run dev     # dev server at http://localhost:5173, proxies /api to the backend
npm run test    # vitest
npm run build   # tsc -b && vite build
npm run lint     # oxlint
```

**CI/CD:** `.github/workflows/ci.yml` runs all three test suites + the frontend build on every push/PR; `.github/workflows/deploy.yml` applies DB migrations and deploys both the frontend and backend to Vercel (two separate projects) after CI passes on `main`. See [README.md#deployment-setup-vercel--github-actions](README.md#deployment-setup-vercel--github-actions) for the one-time setup checklist and required GitHub secrets.

## Coding conventions

*Tech stack confirmed; see [README.md](README.md#tech-stack) and [docs/model.md](docs/model.md), [docs/architecture.md](docs/architecture.md).*

- **Model (Python/PyTorch, training):** pretrained CNN backbone with sex concatenated into the regression head (`ml/boneage/model.py`); Grad-CAM for explainability (`ml/boneage/gradcam.py`); uncertainty via MC dropout (`ml/boneage/inference.py`). Keep training/inference code separate from the FastAPI service.
- **Model (ONNX, deployed inference):** `ml/export_onnx.py` exports a trained checkpoint to three ONNX graphs (`ml/boneage/onnx_export.py`); the backend calls `boneage.onnx_inference.predict_single_image_onnx`, not `boneage.inference` — never reimplement model logic in `backend/`, and never let the backend import anything that pulls `torch`/`torchvision` in (see [docs/architecture.md#deployment-notes](docs/architecture.md#deployment-notes) for why that matters: Vercel's Python Functions cap out at 500 MB uncompressed). Score-CAM (`ml/boneage/score_cam.py`) is the gradient-free Grad-CAM stand-in used there — see [docs/model.md#explainability](docs/model.md#explainability) for the formula.
- **Backend (FastAPI):** the growth review agent's *flag decision* must stay in deterministic, testable Python functions/tools (`compute_chronological_age`, `get_normal_range`, `compare_gap` — `backend/app/agent/tools.py`) — never let the LLM decide the flag itself. The LLM's role is limited to writing the explanatory note (`backend/app/agent/note_writer.py`), built on the **OpenAI Agents SDK**, given only structured numbers/labels. See [AGENTS.md](AGENTS.md#the-growth-review-agent) for the full contract. Role checks go through `backend/app/deps.py`'s `require_roles(...)` on every endpoint — never rely on the frontend alone.
- **Frontend (React + TypeScript + Vite + Tailwind):** build every screen by translating its corresponding file in `design/` pixel-for-pixel — see [Frontend design (locked)](#frontend-design-locked) above. Theme via CSS variables taken from each design file's LIGHT/DARK token strings (see [docs/design.md](docs/design.md#design-tokens)), never hard-code hex colours in components. Status (normal/flagged) must always carry a text label, never colour alone.
- **No invented medical facts or numbers.** Do not hard-code clinical thresholds, accuracy figures, or normal ranges as "truth" in code or docs — they are configuration, sourced from settings/reference tables (Greulich & Pyle–based SD reference; exact tables `[TBD, to verify]`), and marked `[TBD]` until the team supplies real values.
- Naming: use **BoneAge AI**, **growth review agent**, **review queue**, **case report** consistently across code, UI copy, and docs — matches the terms used throughout `docs/`.

## Rules for this project

1. **Decision support only.** Never write code or copy that states or implies a diagnosis. Phrase clinical content as "possible causes the doctor may consider," not as fact.
2. **No fabricated numbers.** No made-up accuracy, MAE, or clinical thresholds anywhere — use `[TBD]` and point to [docs/model.md](docs/model.md) for where real values will go.
3. **Keep the growth review agent auditable.** The flag decision is rule-based; only the explanation is LLM-generated. Never let the agent change the model's predicted bone age.
4. **Cross-link, don't duplicate.** When adding documentation, link to the relevant `docs/*.md` file rather than re-explaining it inline.
5. **Dataset licensing.** RSNA is non-commercial research/education use with attribution — don't introduce code or docs implying commercial redistribution. See [docs/data.md](docs/data.md).

## Pointers

- Product/requirements: [docs/requirements.md](docs/requirements.md)
- UI/UX and design tokens: [docs/design.md](docs/design.md)
- System design: [docs/architecture.md](docs/architecture.md)
- Datasets: [docs/data.md](docs/data.md)
- Model: [docs/model.md](docs/model.md)
- API: [docs/api.md](docs/api.md)
- Task breakdown: [docs/tasks.md](docs/tasks.md)
- Testing: [docs/testing.md](docs/testing.md)
- Safety & ethics: [docs/safety-and-ethics.md](docs/safety-and-ethics.md)
- Growth review agent spec (detailed): [AGENTS.md](AGENTS.md#the-growth-review-agent)

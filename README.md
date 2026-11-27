# BoneAge AI (working name)

> **Decision support only — not a diagnostic device.** BoneAge AI never produces a diagnosis. It estimates skeletal (bone) age from an X-ray and flags cases where the gap to chronological age falls outside a configurable normal range, for a qualified clinician to review and decide on. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md).

## Problem

Assessing a child's bone age from a hand X-ray is a standard way to check whether skeletal development matches chronological (real) age. Large gaps can be an early signal of growth or hormone conditions (e.g. growth hormone deficiency, hypothyroidism, constitutional delay of growth, early puberty) — but manual bone age reading (e.g. Greulich-Pyle or Tanner-Whitehouse atlas comparison) is slow, requires experience, and results vary between readers. Many cases where bone age and chronological age diverge meaningfully are easy to miss in a busy clinic.

## Solution

BoneAge AI is a web app for a radiology/paediatric workflow:

1. A clinician enters patient details and uploads a left-hand X-ray.
2. A CNN predicts bone age from the image plus the patient's sex, with an uncertainty estimate and an attention heatmap (Grad-CAM when training/evaluating on PyTorch, Score-CAM — a gradient-free stand-in — on the deployed ONNX Runtime backend; see [docs/model.md#explainability](docs/model.md#explainability)).
3. A **growth review agent** compares predicted bone age against chronological age (computed from date of birth and X-ray date) using a configurable, sex- and age-specific normal range. Cases outside range, or where the model is uncertain, are flagged with a short explanatory note and possible causes for the doctor to check — cases inside range can be auto-cleared.
4. A doctor reviews flagged (and, if desired, cleared) cases in a **review queue**, opens a **case report** (X-ray, heatmap, measurements, agent reasoning, history), and records a decision: confirm the flag, mark within expected range, or flag the model's read as wrong and re-read manually. The doctor's decision is always final.

## Key features

- Patient intake with automatic chronological age calculation from date of birth + X-ray date.
- Image quality checks before inference (hand detected, orientation, resolution, burned-in patient identifiers removed).
- CNN bone age prediction using image + sex, with uncertainty estimate and an attention heatmap.
- Configurable normal-range rules, based on Greulich & Pyle–derived SD reference data (exact tables `[TBD, to verify]`); demo default shown as ±2 SD in the UI, with the threshold and reference tables configurable in Settings, not hard-coded medical facts.
- Growth review agent: rule-based flag decision (auditable), LLM-written explanation of what to check — never a diagnosis.
- Review queue with status tabs, search, sex filter, sorting, and pagination.
- Case report with export to PDF and follow-up scan scheduling.
- Patients list, model performance dashboard (MAE overall / by sex / by age band, predicted-vs-true chart, model card, limitations).
- Settings for flagging rules, agent behaviour, theme (light/dark) and age units, data & privacy, account.
- Full light/dark theming via CSS variables; status is always shown with a text label, never colour alone.

## Datasets

| Dataset | Size | Labels | Notes | Link |
|---|---|---|---|---|
| RSNA Pediatric Bone Age Challenge 2017 (main training set) | 14,236 left-hand radiographs (12,611 train / 1,425 validation / 200 test) | Bone age (months), sex | No chronological age included. Non-commercial research/education use with attribution. | [RSNA](https://www.rsna.org/artificial-intelligence/ai-image-challenge/RSNA-Pediatric-Bone-Age-Challenge-2017) · [Kaggle mirror](https://www.kaggle.com/datasets/kmader/rsna-bone-age) (`kaggle datasets download -d kmader/rsna-bone-age`) |
| Digital Hand Atlas (USC) | ~1,400 hand X-rays of healthy children (Asian, African American, Caucasian, Hispanic) | Chronological age, sex, Tanner stage, height, weight, two bone age readings | Used to evaluate the bone-age-vs-chronological-age gap and as an external check. | [USC IPILab](https://ipilab.usc.edu/BAAweb) |
| RHPE (Radiological Hand Pose Estimation), Universidad de los Andes | 6,288 hand X-rays, Colombian patients | Chronological age; hand bounding boxes/keypoints (also for RSNA) | | [BCV Uniandes](https://bcv-uniandes.github.io/baar-wp/) |

Plan: train on RSNA; evaluate the gap-flagging agent and generalisation on DHA and/or RHPE. See [docs/data.md](docs/data.md) for fields, splits, preprocessing, and licensing/attribution requirements in full.

## Architecture (summary)

```
Clinician → Frontend (React) → Backend (FastAPI)
                                   ├── Image quality checks
                                   ├── CNN inference (bone age, uncertainty, attention heatmap)
                                   ├── Growth review agent (deterministic tools + LLM note)
                                   └── Case storage (DB + image storage)
                                   → Review queue → Doctor decision → PDF export / follow-up scheduling
```

Full component breakdown, data flow, and a Mermaid diagram are in [docs/architecture.md](docs/architecture.md).

## Tech stack

*Confirmed by the team — proposed stack below, now final for the hackathon build.*

- **Model (training):** Python, PyTorch, pretrained CNN backbone (e.g. EfficientNet/ResNet) with sex concatenated into the regression head; Grad-CAM for heatmaps; uncertainty via MC dropout. Trained/evaluated/exported entirely within `ml/` (see [ml/README.md](ml/README.md)).
- **Model (deployed inference):** ONNX Runtime, not PyTorch — `ml/export_onnx.py` exports a trained checkpoint to three ONNX graphs; the backend runs MC-dropout uncertainty and Score-CAM (a gradient-free Grad-CAM stand-in) purely via ONNX Runtime + numpy, with zero `torch`/`torchvision` at request time. See [docs/model.md#explainability](docs/model.md#explainability) and [docs/architecture.md#deployment-notes](docs/architecture.md#deployment-notes) for why.
- **Backend:** FastAPI serving inference, case storage, and the agent — deployed as a Vercel Python Function (see [docs/architecture.md#deployment-notes](docs/architecture.md#deployment-notes)).
- **Agent:** LLM agent built on the **OpenAI Agents SDK**, calling deterministic tools (`compute_chronological_age`, `get_normal_range`, `compare_gap`, `write_doctor_note`) so the flag decision is rule-based and auditable; the LLM only writes the explanation, and only ever receives structured numbers/labels — never images or patient names (see [docs/safety-and-ethics.md](docs/safety-and-ethics.md#privacy)).
- **Frontend:** React + TypeScript + Vite + Tailwind, theming via CSS variables.
- **Storage:** SQLite for local dev/tests; Postgres (Neon, via the Vercel Marketplace) in production. Images: local disk for local dev/tests; Vercel Blob in production. Default case/image retention: 30 days, enforced by a Vercel Cron job.
- **Hosting:** frontend and backend are two separate Vercel projects (frontend static + Vite build; backend a Python Function); local fallback for the live demo. See [docs/architecture.md](docs/architecture.md#deployment-notes).

See [docs/model.md](docs/model.md), [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md).

## Setup

`ml/` (data pipeline + model), `backend/` (API + growth review agent), and `frontend/` all have real code. See [docs/tasks.md](docs/tasks.md) for what's next.

**ML data pipeline + model** (see [ml/README.md](ml/README.md) for details):
```bash
pip install -r ml/requirements.txt
cp ml/config/config.example.yaml ml/config/config.yaml   # then fill in your real RSNA dataset paths
pytest ml                                                  # runs against a small fake dataset — no download needed
```

**Backend API** (see [backend/README.md](backend/README.md) for details):
```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
alembic upgrade head                   # creates the SQLite schema
python scripts/seed_demo_data.py       # optional: demo users + sample cases
uvicorn app.main:app --reload          # Swagger UI at http://127.0.0.1:8000/docs
```

This repo does not include or download the RSNA/DHA/RHPE datasets — get them yourself per [docs/data.md](docs/data.md).

- [ ] TODO: model training (code is ready — see `ml/train.py` — but no real training run has happened yet)

**Frontend** (see [frontend/README.md](frontend/README.md)):
```bash
cd frontend
npm install
npm run dev       # dev server at http://localhost:5173, proxies /api to the backend (vite.config.ts)
npm run test      # vitest
npm run build     # production build (tsc -b && vite build)
```

## Deployment setup (Vercel + GitHub Actions)

Frontend **and** backend are both deployed to **Vercel**, as two separate projects from this one repo — the backend as a Python Function (see `backend/vercel.json`, `backend/.python-version`; no Docker/Render involved). Both deploy only through `.github/workflows/deploy.yml`, after `.github/workflows/ci.yml` passes on `main` (see [docs/architecture.md](docs/architecture.md#deployment-notes)). Do this once, in order:

1. **Create the backend Vercel project.** New Project → import this repo → set its **Root Directory** to `backend`. Vercel auto-detects it as a Python project (`app/main.py`'s `app` — see `backend/vercel.json`); no Build/Output Directory overrides needed.
2. **Keep "Include files outside the Root Directory in the Build Step" enabled** (Project Settings → Build and Deployment → Root Directory — it's the default). The backend imports `ml/boneage/*` from the sibling `ml/` directory at runtime; turning this off breaks the real (non-mock) prediction path.
3. **Add a Postgres database.** Project → Storage → Marketplace → Neon (or your own Neon project, connected the same way) → connect it to this project. Vercel sets `DATABASE_URL` automatically (a bare `postgres://`/`postgresql://` URL is fine — `app/database.py` normalises it to use `psycopg` itself).
4. **Add a Blob store.** Project → Storage → Blob → create one → connect it to this project. Vercel sets `BLOB_READ_WRITE_TOKEN` automatically — its mere presence is what switches `app/storage.py` from local disk to Blob.
5. **Set the backend project's remaining env vars** (Settings → Environment Variables, Production): `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`), `CRON_SECRET` (any random 16+ character string — secures the retention-cleanup cron, see `app/routers/internal.py`), `CORS_ORIGIN` (fill in after step 8, once you have the frontend's URL), and optionally `ONNX_DOWNLOAD_URL` and `OPENAI_API_KEY`.
6. **Turn off the backend project's auto-deploy from Git.** Project Settings → Git → disconnect/disable automatic deployments — deploys should only come from the workflow's `vercel deploy`, not Vercel's own push listener.
7. **Create the frontend Vercel project.** New Project → import this repo again → set its **Root Directory** to `frontend`. Framework preset: Vite. Add a Production environment variable `VITE_API_BASE_URL` pointing at the backend project's URL from step 1, e.g. `https://boneage-ai-backend.vercel.app`.
8. **Turn off the frontend project's auto-deploy from Git**, same as step 6.
9. **Get Vercel's token and IDs:**
   - `VERCEL_TOKEN`: Vercel → Account Settings → Tokens → create one.
   - `VERCEL_ORG_ID`: the same for both projects — read it from either project's `.vercel/project.json` after running `vercel link` locally once, or from Settings → General.
   - `VERCEL_PROJECT_ID` (frontend) and a second, separate project id for the backend project — same place, per project.
10. **Go back to the backend project and fill in `CORS_ORIGIN`** with the frontend project's URL from step 7 (e.g. `https://boneage-ai.vercel.app`).
11. **Add the GitHub repo secrets** (Settings → Secrets and variables → Actions): `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (frontend), `VERCEL_BACKEND_PROJECT_ID`, and `DATABASE_URL` (the same Postgres connection string from step 3 — needed separately here so the deploy workflow's migration job can run `alembic upgrade head` against production from the GitHub Actions runner; see `.github/workflows/deploy.yml`'s `migrate-backend-db` job).
12. **Push to `main`.** CI runs; once it's green, the deploy workflow applies DB migrations, then builds/deploys both Vercel projects.

Never put any of the above tokens/URLs/keys in code or the workflow files — they're GitHub secrets and Vercel environment variables only.

Notes:
- **Exporting a trained model:** once you have a real checkpoint, run `python ml/export_onnx.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --out-dir ml/checkpoints/onnx`, upload the resulting directory as a zip somewhere reachable, and set `ONNX_DOWNLOAD_URL` on the backend project — it's fetched lazily on the first real prediction request after a cold start (see `app/inference_adapter.py`). Until then, the API transparently falls back to the clearly-labelled mock predictor.
- **Retention cleanup** runs automatically via Vercel Cron (`backend/vercel.json`'s `crons`, daily) — see [backend/README.md](backend/README.md#data-retention-cleanup).
- Vercel Functions can cold-start — the first request after a period of inactivity may take a few seconds longer, most noticeably for a real (ONNX) prediction. Open the app a minute before a live demo.
- See [docs/demo-script.md](docs/demo-script.md) for the judge walkthrough once it's deployed (or running locally as a fallback).

## Documentation map

- [CLAUDE.md](CLAUDE.md) — context for Claude Code sessions working on this repo.
- [AGENTS.md](AGENTS.md) — same context for other coding agents, plus the in-product growth review agent spec.
- [docs/requirements.md](docs/requirements.md) — functional & non-functional requirements, user roles, user stories.
- [docs/design.md](docs/design.md) — UI/UX spec, screens, design tokens, accessibility.
- [docs/architecture.md](docs/architecture.md) — system components, data flow, deployment notes.
- [docs/data.md](docs/data.md) — dataset fields, splits, preprocessing, licensing.
- [docs/model.md](docs/model.md) — model architecture, training plan, evaluation metrics, model card template.
- [docs/api.md](docs/api.md) — REST API endpoints and payloads.
- [docs/tasks.md](docs/tasks.md) — implementation phases and task breakdown.
- [docs/testing.md](docs/testing.md) — test strategy.
- [docs/demo-script.md](docs/demo-script.md) — 3–4 minute judge walkthrough for the live demo.
- [docs/safety-and-ethics.md](docs/safety-and-ethics.md) — disclaimer, bias, privacy, human-in-the-loop.

## Disclaimer

BoneAge AI is a hackathon prototype intended for **decision support only**. It does not diagnose any medical condition. All outputs (bone age estimate, uncertainty, flags, agent notes) are intended to assist a qualified clinician, who makes the final call. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md) for full details.

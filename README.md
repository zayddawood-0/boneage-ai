# BoneAge AI (working name)

> **Decision support only — not a diagnostic device.** BoneAge AI never produces a diagnosis. It estimates skeletal (bone) age from an X-ray and flags cases where the gap to chronological age falls outside a configurable normal range, for a qualified clinician to review and decide on. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md).

## Problem

Assessing a child's bone age from a hand X-ray is a standard way to check whether skeletal development matches chronological (real) age. Large gaps can be an early signal of growth or hormone conditions (e.g. growth hormone deficiency, hypothyroidism, constitutional delay of growth, early puberty) — but manual bone age reading (e.g. Greulich-Pyle or Tanner-Whitehouse atlas comparison) is slow, requires experience, and results vary between readers. Many cases where bone age and chronological age diverge meaningfully are easy to miss in a busy clinic.

## Solution

BoneAge AI is a web app for a radiology/paediatric workflow:

1. A clinician enters patient details and uploads a left-hand X-ray.
2. A CNN predicts bone age from the image plus the patient's sex, with an uncertainty estimate and a Grad-CAM attention heatmap.
3. A **growth review agent** compares predicted bone age against chronological age (computed from date of birth and X-ray date) using a configurable, sex- and age-specific normal range. Cases outside range, or where the model is uncertain, are flagged with a short explanatory note and possible causes for the doctor to check — cases inside range can be auto-cleared.
4. A doctor reviews flagged (and, if desired, cleared) cases in a **review queue**, opens a **case report** (X-ray, heatmap, measurements, agent reasoning, history), and records a decision: confirm the flag, mark within expected range, or flag the model's read as wrong and re-read manually. The doctor's decision is always final.

## Key features

- Patient intake with automatic chronological age calculation from date of birth + X-ray date.
- Image quality checks before inference (hand detected, orientation, resolution, burned-in patient identifiers removed).
- CNN bone age prediction using image + sex, with uncertainty estimate and Grad-CAM heatmap.
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
                                   ├── CNN inference (bone age, uncertainty, Grad-CAM)
                                   ├── Growth review agent (deterministic tools + LLM note)
                                   └── Case storage (DB + image storage)
                                   → Review queue → Doctor decision → PDF export / follow-up scheduling
```

Full component breakdown, data flow, and a Mermaid diagram are in [docs/architecture.md](docs/architecture.md).

## Tech stack

*Confirmed by the team — proposed stack below, now final for the hackathon build.*

- **Model:** Python, PyTorch, pretrained CNN backbone (e.g. EfficientNet/ResNet) with sex concatenated into the regression head; Grad-CAM for heatmaps; uncertainty via MC dropout.
- **Backend:** FastAPI serving inference, case storage, and the agent.
- **Agent:** LLM agent built on the **OpenAI Agents SDK**, calling deterministic tools (`compute_chronological_age`, `get_normal_range`, `compare_gap`, `write_doctor_note`) so the flag decision is rule-based and auditable; the LLM only writes the explanation, and only ever receives structured numbers/labels — never images or patient names (see [docs/safety-and-ethics.md](docs/safety-and-ethics.md#privacy)).
- **Frontend:** React + TypeScript + Vite + Tailwind, theming via CSS variables.
- **Storage:** SQLite or Postgres for cases; local/object storage for images. Default case/image retention: 30 days.
- **Hosting:** frontend on Vercel; backend + model on Render; local fallback for the live demo. See [docs/architecture.md](docs/architecture.md#deployment-notes-hackathon-demo).

See [docs/model.md](docs/model.md), [docs/architecture.md](docs/architecture.md), [docs/api.md](docs/api.md).

## Setup

The repo is scaffolded (`backend/`, `frontend/`, `ml/`) — `ml/` (data pipeline + model) and `backend/` (API + growth review agent) both have real code; frontend is still a placeholder. See [docs/tasks.md](docs/tasks.md) for what's next.

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

- [ ] TODO: frontend setup (`npm install`, dev server) — not yet implemented; must match [`design/`](design/README.md) exactly, see [docs/design.md](docs/design.md#design-lock)
- [ ] TODO: model training (code is ready — see `ml/train.py` — but no real training run has happened yet)
- [ ] TODO: running the full stack locally (needs the frontend)

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
- [docs/testing.md](docs/testing.md) — test strategy and demo script.
- [docs/safety-and-ethics.md](docs/safety-and-ethics.md) — disclaimer, bias, privacy, human-in-the-loop.

## Disclaimer

BoneAge AI is a hackathon prototype intended for **decision support only**. It does not diagnose any medical condition. All outputs (bone age estimate, uncertainty, flags, agent notes) are intended to assist a qualified clinician, who makes the final call. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md) for full details.

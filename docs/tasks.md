# Tasks

Part of the [BoneAge AI](../README.md) documentation set. Implementation plan organized by phase and functional area: **ML**, **Backend + Agent**, **Frontend**. See also: [requirements.md](requirements.md), [architecture.md](architecture.md), [testing.md](testing.md).

Every **Frontend** task below means translating that screen's file in [`design/`](../design/README.md) into React + Tailwind pixel-for-pixel — same layout, spacing, colours, fonts, copy, icons and states, using the file's LIGHT/DARK token strings for theming (see [design.md#design-lock](design.md#design-lock) and [design.md#design-file-map](design.md#design-file-map)). Do not redesign, restyle, or "improve" a screen while building it.

## Phase 0 — Setup

- [ ] Download RSNA dataset (Kaggle mirror)
- [ ] Download DHA and/or RHPE for evaluation
- [x] Scaffold repo structure (`backend/`, `frontend/`, `ml/`)
- [ ] Agree on API contract draft from [api.md](api.md)

## Phase 1 — Core pipeline

### ML
- [x] Preprocessing pipeline (resize+pad, normalise, orientation, grayscale handling) per [data.md](data.md#preprocessing) — `ml/boneage/transforms.py`
- [x] Training-only augmentation (small rotations, shifts, zoom, brightness/contrast; no horizontal flips) — `ml/boneage/transforms.py`
- [x] Encode sex as the extra model input — `ml/boneage/datasets.py`
- [x] Train/validation/test splits with a fixed random seed — `ml/boneage/splits.py`, `ml/boneage/seed.py`
- [x] PyTorch `Dataset`/`DataLoader` returning `(image, sex, bone_age_months)` — `ml/boneage/datasets.py`, `ml/boneage/dataloaders.py`
- [x] Unit tests for the pipeline against a small fake dataset (no real data needed) — `ml/tests/`
- [x] Model architecture: pretrained backbone + sex concatenated into the regression head, with dropout for MC dropout — `ml/boneage/model.py`
- [x] Training script: L1 loss, AdamW, LR schedule, early stopping on val MAE, best-checkpoint saving, mixed precision when a GPU is available, all settings from config — `ml/train.py`, `ml/boneage/training.py`
- [x] Evaluation script: MAE overall/by sex/by age band, % within ±12 months, on val + test; saves JSON + predicted-vs-true scatter plot — `ml/evaluate.py`, `ml/boneage/evaluation.py`
- [x] Implement uncertainty estimate via MC dropout — `ml/boneage/model.py` (`set_mc_dropout_mode`), `ml/boneage/inference.py`
- [x] Implement Grad-CAM heatmap generation — `ml/boneage/gradcam.py`
- [x] Inference module: checkpoint → bone age + MC-dropout uncertainty (mean/spread over N passes) + Grad-CAM heatmap overlaid on the X-ray — `ml/boneage/inference.py`
- [x] Kaggle notebook: installs the `boneage` package, points config at the Kaggle `kmader/rsna-bone-age` input, trains on GPU, evaluates, saves checkpoint + results for download — `ml/notebooks/train_kaggle.ipynb`
- [x] Unit tests: model forward-pass shapes, 1-epoch CPU smoke training run, evaluation output format, inference (age + uncertainty + heatmap) — `ml/tests/`
- [ ] Train baseline CNN (backbone + sex input) on RSNA — **not run yet; real training only, via `ml/train.py` or the Kaggle notebook**
- [ ] Baseline evaluation (MAE overall/by sex/by age band) on RSNA test split — **not run yet; depends on the item above**

### Backend + Agent
- [x] Auth (sign in) endpoint + session/token handling — `backend/app/routers/auth.py`, `backend/app/security.py` (bcrypt + JWT)
- [x] Patient + case data models and CRUD endpoints — `backend/app/models.py`, `backend/app/routers/patients.py`, `backend/app/routers/cases.py`; SQLite via Alembic migrations (`backend/migrations/`)
- [x] Image upload endpoint + image quality checks (hand detected, orientation, resolution, burned-in detail removal) — `backend/app/routers/cases.py` (`/upload`), `backend/app/quality.py`
- [x] Integrate model inference endpoint (calls ML's inference interface) — `backend/app/routers/cases.py` (`/predict`), `backend/app/inference_adapter.py`; falls back to a clearly-labelled mock predictor when no checkpoint exists yet, and the response always reports `prediction_source: real|mock`
- [x] Implement growth review agent (OpenAI Agents SDK) deterministic tools: `compute_chronological_age`, `get_normal_range`, `compare_gap` — `backend/app/agent/tools.py`; supports both SD-based (reference table in `backend/data/reference_tables/greulich_pyle_sd_reference.json`, shipped as an empty `[TBD — to verify]` template) and fixed-months rule types
- [x] Implement `write_doctor_note` (LLM call via OpenAI Agents SDK) per [AGENTS.md](../AGENTS.md#the-growth-review-agent) — pass only structured numbers/labels, never images or patient names — `backend/app/agent/note_writer.py`; falls back to a fixed template note when `OPENAI_API_KEY` is unset or the call fails
- [x] Settings endpoints (normal-range config, auto-clear, uncertainty threshold, retention) — `backend/app/routers/settings.py` (admin only)
- [x] Role-based access control enforcing the permission matrix in [requirements.md](requirements.md#user-roles) — `backend/app/deps.py` (`require_roles`), applied to every endpoint

### Frontend
- [x] Set up design tokens (CSS variables) + theme toggle using the LIGHT/DARK strings from `design/Main.html`/`design/Dark.html` per [design.md](design.md#design-tokens) — `frontend/src/index.css`, `frontend/src/theme/ThemeContext.tsx`
- [x] Sign in screen — translate `design/Login.html` — `frontend/src/pages/LoginPage.tsx`
- [x] New analysis 3-step flow (patient details → upload → result) — translate `design/NewAnalysis.html` — `frontend/src/pages/NewAnalysisPage.tsx`
- [x] Dashboard shell — translate `design/Main.html` (light) and `design/Dark.html` (dark reference) — `frontend/src/pages/DashboardPage.tsx`

## Phase 2 — Review workflow

### ML
- [ ] Source and verify the Greulich & Pyle–based SD reference tables used for `get_normal_range` (currently `[TBD, to verify]`)
- [ ] Evaluate gap-flagging behaviour on DHA and/or RHPE (external chronological-age data) per [data.md](data.md#handling-chronological-age-rsna-gap)
- [ ] Tune/finalise uncertainty threshold recommendation (feeds into agent config)
- [ ] Draft model card ([model.md](model.md#model-card-template)) with real results once available

### Backend + Agent
- [x] Review queue endpoint (filter/sort/paginate) per [api.md](api.md#cases) — `GET /cases` in `backend/app/routers/cases.py`
- [x] Case report endpoint (full payload incl. prior scans) — `GET /cases/{id}`
- [x] Doctor decision endpoint — `POST /cases/{id}/decision` (doctor role only, per the permission matrix)
- [x] PDF export endpoint — `GET /cases/{id}/report.pdf`, `backend/app/pdf.py` (reportlab)
- [x] Follow-up scheduling endpoint — `POST /cases/{id}/follow-up`
- [x] Agent auditability: ensure every flag decision is traceable to `compare_gap` output, not just the LLM note — `flag_status`/`gap_direction`/`flag_reason` are stored on the case independently of `doctor_note`; covered by `backend/tests/test_agent_rules.py`

### Frontend
- [x] Review queue screen (status tabs, search, sex filter, sort, pagination) — translate `design/Queue.html` — `frontend/src/pages/QueuePage.tsx`
- [x] Case report screen (X-ray + heatmap viewer, measurements, agent reasoning, decision controls, PDF export, follow-up scheduling) — translate `design/Case.html` — `frontend/src/pages/CaseReportPage.tsx`, `frontend/src/components/HeatmapViewer.tsx`
- [x] Patients screen — translate `design/Patients.html` — `frontend/src/pages/PatientsPage.tsx`
- [x] Dashboard: summary cards, growth review agent panel, bone age vs. chronological age chart, review queue preview — refine from `design/Main.html`/`design/Dark.html` — `frontend/src/pages/DashboardPage.tsx`, `frontend/src/lib/scanChart.ts`

## Phase 3 — Model performance, settings, polish

### ML
- [ ] Finalise evaluation numbers for the Model performance screen
- [ ] Document limitations for the model card and UI limitations section

### Backend + Agent
- [x] Model performance endpoint — `GET /model/performance`, `backend/app/routers/model_performance.py` (returns real numbers if `ml/evaluate.py` has produced results, otherwise `[TBD]` — never fabricated)
- [x] Settings persistence + validation — `backend/app/routers/settings.py` (Pydantic-validated `PUT /settings`, persisted to the `growth_review_settings` row)
- [ ] Data & privacy settings (retention, de-identification controls) per [safety-and-ethics.md](safety-and-ethics.md) — `retention_days` is a stored, configurable setting, but no scheduled job actually enforces/deletes data past retention yet; de-identification is currently an always-on heuristic check (`backend/app/quality.py`), not a separate configurable toggle

### Frontend
- [x] Model performance screen (MAE breakdowns, predicted-vs-true chart, model card, limitations) — translate `design/Model.html` — `frontend/src/pages/ModelPerformancePage.tsx` (shows `[TBD]` for every metric the API has no real value for yet, per task instructions)
- [x] Settings screen (flagging rules, agent behaviour, theme + age units, data & privacy, account) — translate `design/Settings.html` — `frontend/src/pages/SettingsPage.tsx`
- [x] Accessibility pass (WCAG AA, status labels, keyboard nav) per [design.md](design.md#accessibility-rules) — real buttons/links/labels throughout, status never colour-only (`StatusChip`), global `:focus-visible` ring in `frontend/src/index.css`
- [x] Dark theme pass across all screens, checked against each file's DARK token string — `[data-theme="dark"]` variables in `frontend/src/index.css`; verified by browser smoke test across Login/Dashboard/Queue/Case/Patients/Model/Settings

## Phase 4 — Integration, testing, demo prep

- [x] End-to-end run-through of the full flow (sign in → intake → upload → predict → agent → queue → decision → export) — backend-only, automated in `backend/tests/test_api_flow.py`; a real manual run-through still needs the frontend
- [x] Seed demo data: a handful of cases spanning flagged/normal, both sexes, a few age bands — `backend/scripts/seed_demo_data.py`, matching `design/Queue.html`/`design/Patients.html` exactly (BA-1037..BA-1042), clearly marked `is_demo=True`
- [ ] Run through [testing.md](testing.md) test plan
- [ ] Rehearse demo script ([testing.md](testing.md#demo-script))
- [ ] Final check of disclaimers/safety copy across UI and docs per [safety-and-ethics.md](safety-and-ethics.md)
- [ ] Deploy frontend to Vercel and backend + model to Render; verify the local fallback runs end-to-end
- [ ] Side-by-side check of each screen against its design/ file in light and dark themes

## Phase 5 — CI/CD, deployment, and demo readiness

*Superseded by Phase 6: the backend no longer deploys to Render — see below. CI, the demo script, and the retention-cleanup logic itself are unchanged.*

- [x] CI workflow (`.github/workflows/ci.yml`): ml tests, backend tests, frontend tests, and the frontend build on every push/PR — CPU-only, `pretrained=False` where relevant, pip/npm caching, no dataset or checkpoint downloads needed
- [x] ~~Deploy workflow deploys the frontend to Vercel and triggers a Render deploy~~ — see Phase 6, both the frontend and backend now deploy to Vercel
- [x] `frontend/vercel.json` SPA rewrite so client-side routes (`react-router-dom`'s `BrowserRouter`) survive a deep link/refresh
- [x] ~~`render.yaml`~~ — removed in Phase 6
- [x] CORS middleware (`backend/app/main.py`, `CORS_ORIGIN` setting) — not needed for local dev (Vite proxy), required once frontend/backend are on separate origins
- [x] ~~Startup checkpoint download step (`backend/scripts/download_checkpoint.py`)~~ — replaced in Phase 6 by a lazy, per-cold-start download inside `app/inference_adapter.py` (Vercel Functions have no pre-start hook to run a separate script from)
- [x] Data-retention cleanup task (`backend/app/retention.py`) — deletes X-ray images/heatmaps for cases past the configured `retention_days`, keeps the case record itself; in Phase 6 this runs automatically via Vercel Cron (`backend/scripts/cleanup_retention.py` is the manual/local-dev equivalent)
- [x] `docs/demo-script.md` — 3–4 minute judge walkthrough using the seeded demo cases
- [x] ~~README.md setup checklist for creating the Vercel/Render projects~~ — superseded by Phase 6's all-Vercel checklist
- [ ] Rehearse the demo script live against the deployed (not just local) environment

## Phase 6 — Backend on Vercel: ONNX inference, Postgres, Blob storage

- [x] **Measured the backend's deployed dependency size** before changing anything: `torch`+`torchvision` alone are ~750 MB uncompressed (actual Linux wheels extracted and measured), total ~1023 MB — well over Vercel's 500 MB Python Function limit
- [x] ONNX export (`ml/boneage/onnx_export.py`, `ml/export_onnx.py`): a trained checkpoint → three ONNX graphs (backbone+activations, and the two head layers either side of each Dropout — see the module's docstring for why three, not one) + `metadata.json`
- [x] Torch-free ONNX inference (`ml/boneage/onnx_inference.py`, `ml/boneage/numpy_transforms.py`): MC-dropout uncertainty reproduced exactly via numpy-side Bernoulli masking between the two head graphs (not via ONNX Runtime's own Dropout-training-mode behaviour, which can't cleanly separate "dropout active" from "BatchNorm frozen" the way `set_mc_dropout_mode` does); verified torch-free with a subprocess import check
- [x] Score-CAM (`ml/boneage/score_cam.py`) — gradient-free Grad-CAM stand-in for the ONNX path (no backprop in ONNX Runtime); regression-appropriate channel weighting (`softmax(-|f(masked) - f(full)|)`), top-k channel limit (`InferenceConfig.score_cam_top_k`), verified numerically against the real model and checked that it dominates toward the channel that reproduces the full prediction
- [x] Shared `ml/boneage/colormap.py` (hardcoded inferno LUT, checked against matplotlib) replaces the old per-call matplotlib colourisation in `gradcam.py` — keeps Grad-CAM and Score-CAM pixel-identically coloured, and removes matplotlib from the backend's path entirely
- [x] `ml/compare_heatmaps.py` — runs PyTorch Grad-CAM and ONNX Score-CAM side by side on sample images (or auto-generated synthetic ones) for a visual sanity check before trusting Score-CAM in a demo
- [x] `backend/app/inference_adapter.py` rewritten: real path calls `boneage.onnx_inference`, not `boneage.inference`; mock path switched to the torch-free `boneage.numpy_transforms`; lazy, once-per-cold-start model download from `ONNX_DOWNLOAD_URL`
- [x] `backend/requirements.txt` is now torch-free (ONNX Runtime, psycopg, vercel-blob added); `backend/requirements-dev.txt` adds torch/torchvision/pandas/matplotlib/onnx back for the test suite only (never installed in production)
- [x] Postgres support (`app/database.py`'s `normalize_database_url`, same normalisation applied in `migrations/env.py`) — SQLite stays the local dev/test default; Neon (Vercel Marketplace) in production, same Alembic chain
- [x] Vercel Blob image storage (`app/storage.py`) — local disk (default) or Blob, selected automatically by `BLOB_READ_WRITE_TOKEN`; `app/pdf.py` and the case image endpoints updated to read bytes through the same abstraction instead of assuming a local filesystem path
- [x] Retention cleanup as a Vercel Cron job (`backend/vercel.json`'s `crons`, `app/routers/internal.py`'s `GET /internal/retention-cleanup`, guarded by `CRON_SECRET`) instead of a background task
- [x] `backend/vercel.json` + `backend/.python-version` (zero-config Python detection of `app/main.py`'s `app`); `render.yaml` removed
- [x] `.github/workflows/deploy.yml`: migration job (`alembic upgrade head` + demo reseed against production Postgres, run from the Actions runner) + two Vercel deploy jobs (frontend, backend) — the Render deploy-hook job removed
- [x] Docs updated: `docs/model.md#explainability` (Score-CAM formula, written up in full), `docs/safety-and-ethics.md`, `docs/api.md`, `docs/requirements.md`, `docs/design.md`, `docs/testing.md`, `docs/demo-script.md`, `README.md`, `CLAUDE.md`, `AGENTS.md`, `backend/README.md`, `ml/README.md`
- [ ] **Frontend's Model performance model card** — intentionally *not* updated to name Score-CAM: the screen is pixel-locked to `design/Model.html`, which has no row for an explainability method (only a generic `[Backbone, e.g. CNN name]` Architecture placeholder and a fixed 4-bullet Limitations list) — adding one would mean amending the locked design file first. Flagged for a decision, not silently skipped or silently done.
- [ ] Actually create the two Vercel projects (frontend + backend), the Neon Postgres integration, and the Blob store, and run through the README setup checklist end-to-end on the real services (the workflows/config are written and verified locally — including an empirical check of Vercel's documented Root-Directory file-inclusion and Python-entrypoint-detection behaviour against their current docs — but nobody has clicked through Vercel/Neon yet)
- [ ] Rehearse the demo script live against the deployed (not just local) environment, once deployed

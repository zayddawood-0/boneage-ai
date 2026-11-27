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

- [x] CI workflow (`.github/workflows/ci.yml`): ml tests, backend tests, frontend tests, and the frontend build on every push/PR — CPU-only, `pretrained=False` where relevant, pip/npm caching, no dataset or checkpoint downloads needed
- [x] Deploy workflow (`.github/workflows/deploy.yml`): fires after CI passes on `main` (`workflow_run`); deploys the frontend to Vercel via the Vercel CLI (`VERCEL_TOKEN`/`VERCEL_ORG_ID`/`VERCEL_PROJECT_ID`) and triggers a Render deploy via `RENDER_DEPLOY_HOOK_URL` — see the setup checklist in [README.md](../README.md#deployment-setup-vercel--render--github-actions)
- [x] `frontend/vercel.json` SPA rewrite so client-side routes (`react-router-dom`'s `BrowserRouter`) survive a deep link/refresh
- [x] `render.yaml`: start command runs the checkpoint download step, Alembic migrations, and the demo seed on every deploy; env vars for the JWT secret (generated), optional `OPENAI_API_KEY`, and `CORS_ORIGIN` (set to the Vercel URL)
- [x] CORS middleware (`backend/app/main.py`, `CORS_ORIGIN` setting) — not needed for local dev (Vite proxy), required once frontend/backend are on separate origins
- [x] Startup checkpoint download step (`backend/scripts/download_checkpoint.py`) — best-effort fetch from `CHECKPOINT_DOWNLOAD_URL`; never fails the deploy, falls back to the mock predictor (the "Demo model" chip) automatically if unset or the download fails
- [x] Data-retention cleanup task (`backend/app/retention.py`, `backend/scripts/cleanup_retention.py`) — deletes X-ray images/heatmaps for cases past the configured `retention_days`, keeps the case record itself; not wired into an automatic scheduler for the hackathon build, run manually or via an external cron
- [x] `docs/demo-script.md` — 3–4 minute judge walkthrough using the seeded demo cases
- [x] README.md setup checklist for creating the Vercel/Render projects, getting each token/hook, and adding the GitHub secrets
- [ ] Actually create the Vercel and Render projects and run through the checklist end-to-end on the real services (the workflows/config are written and validated locally; nobody has clicked through Vercel/Render yet)
- [ ] Rehearse the demo script live against the deployed (not just local) environment

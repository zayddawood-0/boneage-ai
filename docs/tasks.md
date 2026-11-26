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
- [ ] Auth (sign in) endpoint + session/token handling
- [ ] Patient + case data models and CRUD endpoints
- [ ] Image upload endpoint + image quality checks (hand detected, orientation, resolution, burned-in detail removal)
- [ ] Integrate model inference endpoint (calls ML's inference interface)
- [ ] Implement growth review agent (OpenAI Agents SDK) deterministic tools: `compute_chronological_age`, `get_normal_range`, `compare_gap`
- [ ] Implement `write_doctor_note` (LLM call via OpenAI Agents SDK) per [AGENTS.md](../AGENTS.md#the-growth-review-agent) — pass only structured numbers/labels, never images or patient names
- [ ] Settings endpoints (normal-range config, auto-clear, uncertainty threshold, retention)
- [ ] Role-based access control enforcing the permission matrix in [requirements.md](requirements.md#user-roles)

### Frontend
- [ ] Set up design tokens (CSS variables) + theme toggle using the LIGHT/DARK strings from `design/Main.html`/`design/Dark.html` per [design.md](design.md#design-tokens)
- [ ] Sign in screen — translate `design/Login.html`
- [ ] New analysis 3-step flow (patient details → upload → result) — translate `design/NewAnalysis.html`
- [ ] Dashboard shell — translate `design/Main.html` (light) and `design/Dark.html` (dark reference)

## Phase 2 — Review workflow

### ML
- [ ] Source and verify the Greulich & Pyle–based SD reference tables used for `get_normal_range` (currently `[TBD, to verify]`)
- [ ] Evaluate gap-flagging behaviour on DHA and/or RHPE (external chronological-age data) per [data.md](data.md#handling-chronological-age-rsna-gap)
- [ ] Tune/finalise uncertainty threshold recommendation (feeds into agent config)
- [ ] Draft model card ([model.md](model.md#model-card-template)) with real results once available

### Backend + Agent
- [ ] Review queue endpoint (filter/sort/paginate) per [api.md](api.md#cases)
- [ ] Case report endpoint (full payload incl. prior scans)
- [ ] Doctor decision endpoint
- [ ] PDF export endpoint
- [ ] Follow-up scheduling endpoint
- [ ] Agent auditability: ensure every flag decision is traceable to `compare_gap` output, not just the LLM note

### Frontend
- [ ] Review queue screen (status tabs, search, sex filter, sort, pagination) — translate `design/Queue.html`
- [ ] Case report screen (X-ray + heatmap viewer, measurements, agent reasoning, decision controls, PDF export, follow-up scheduling) — translate `design/Case.html`
- [ ] Patients screen — translate `design/Patients.html`
- [ ] Dashboard: summary cards, growth review agent panel, bone age vs. chronological age chart, review queue preview — refine from `design/Main.html`/`design/Dark.html`

## Phase 3 — Model performance, settings, polish

### ML
- [ ] Finalise evaluation numbers for the Model performance screen
- [ ] Document limitations for the model card and UI limitations section

### Backend + Agent
- [ ] Model performance endpoint
- [ ] Settings persistence + validation
- [ ] Data & privacy settings (retention, de-identification controls) per [safety-and-ethics.md](safety-and-ethics.md)

### Frontend
- [ ] Model performance screen (MAE breakdowns, predicted-vs-true chart, model card, limitations) — translate `design/Model.html`
- [ ] Settings screen (flagging rules, agent behaviour, theme + age units, data & privacy, account) — translate `design/Settings.html`
- [ ] Accessibility pass (WCAG AA, status labels, keyboard nav) per [design.md](design.md#accessibility-rules)
- [ ] Dark theme pass across all screens, checked against each file's DARK token string

## Phase 4 — Integration, testing, demo prep

- [ ] End-to-end run-through of the full flow (sign in → intake → upload → predict → agent → queue → decision → export)
- [ ] Seed demo data: a handful of cases spanning flagged/normal, both sexes, a few age bands
- [ ] Run through [testing.md](testing.md) test plan
- [ ] Rehearse demo script ([testing.md](testing.md#demo-script))
- [ ] Final check of disclaimers/safety copy across UI and docs per [safety-and-ethics.md](safety-and-ethics.md)
- [ ] Deploy frontend to Vercel and backend + model to Render; verify the local fallback runs end-to-end
- [ ] Side-by-side check of each screen against its design/ file in light and dark themes

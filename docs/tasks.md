# Tasks

Part of the [BoneAge AI](../README.md) documentation set. Implementation plan organized by phase and functional area: **ML**, **Backend + Agent**, **Frontend**. See also: [requirements.md](requirements.md), [architecture.md](architecture.md), [testing.md](testing.md).

## Phase 0 — Setup

- [ ] Download RSNA dataset (Kaggle mirror)
- [ ] Download DHA and/or RHPE for evaluation
- [ ] Scaffold repo structure (`backend/`, `frontend/`, `model/`)
- [ ] Agree on API contract draft from [api.md](api.md)

## Phase 1 — Core pipeline

### ML
- [ ] Preprocessing pipeline (resize, normalise, orientation) per [data.md](data.md#preprocessing)
- [ ] Train baseline CNN (backbone + sex input) on RSNA
- [ ] Implement uncertainty estimate via MC dropout
- [ ] Implement Grad-CAM heatmap generation
- [ ] Baseline evaluation (MAE overall/by sex/by age band) on RSNA test split

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
- [ ] Set up design tokens (CSS variables) + theme toggle per [design.md](design.md#design-tokens)
- [ ] Sign in screen
- [ ] New analysis 3-step flow (patient details → upload → result)
- [ ] Dashboard shell

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
- [ ] Review queue screen (status tabs, search, sex filter, sort, pagination)
- [ ] Case report screen (X-ray + heatmap viewer, measurements, agent reasoning, decision controls, PDF export, follow-up scheduling)
- [ ] Patients screen
- [ ] Dashboard: summary cards, growth review agent panel, bone age vs. chronological age chart, review queue preview

## Phase 3 — Model performance, settings, polish

### ML
- [ ] Finalise evaluation numbers for the Model performance screen
- [ ] Document limitations for the model card and UI limitations section

### Backend + Agent
- [ ] Model performance endpoint
- [ ] Settings persistence + validation
- [ ] Data & privacy settings (retention, de-identification controls) per [safety-and-ethics.md](safety-and-ethics.md)

### Frontend
- [ ] Model performance screen (MAE breakdowns, predicted-vs-true chart, model card, limitations)
- [ ] Settings screen (flagging rules, agent behaviour, theme + age units, data & privacy, account)
- [ ] Accessibility pass (WCAG AA, status labels, keyboard nav) per [design.md](design.md#accessibility-rules)
- [ ] Dark theme pass across all screens

## Phase 4 — Integration, testing, demo prep

- [ ] End-to-end run-through of the full flow (sign in → intake → upload → predict → agent → queue → decision → export)
- [ ] Seed demo data: a handful of cases spanning flagged/normal, both sexes, a few age bands
- [ ] Run through [testing.md](testing.md) test plan
- [ ] Rehearse demo script ([testing.md](testing.md#demo-script))
- [ ] Final check of disclaimers/safety copy across UI and docs per [safety-and-ethics.md](safety-and-ethics.md)
- [ ] Deploy frontend to Vercel and backend + model to Render; verify the local fallback runs end-to-end

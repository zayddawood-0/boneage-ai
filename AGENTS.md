# AGENTS.md

Guidance for coding agents (Codex, Cursor, Copilot Workspace, etc.) working in this repository. This mirrors [CLAUDE.md](CLAUDE.md) — if you need to update one, update both so they stay consistent.

## What this project is

**BoneAge AI** (working name) is a hackathon healthcare project, 3-person team. A CNN trained on the RSNA Bone Age dataset estimates a child's bone age from a left-hand X-ray (image + sex as inputs) and compares it with chronological age (computed from date of birth and X-ray date). A **growth review agent** flags cases where the gap is outside a configurable normal range and writes a short note for a doctor explaining what to check. The doctor always makes the final decision.

**This is decision support only — never a diagnosis.** See [docs/safety-and-ethics.md](docs/safety-and-ethics.md). Full product description: [README.md](README.md). Requirements: [docs/requirements.md](docs/requirements.md).

## Current state

`ml/`, `backend/`, and `frontend/` all have real code now, plus CI/CD (`.github/workflows/`) and deployment config (`render.yaml`, `frontend/vercel.json`).

- **`ml/`** — the RSNA data pipeline and the model itself (architecture, training loop, evaluation, Grad-CAM, MC-dropout inference, a Kaggle training notebook), with unit tests (see [ml/README.md](ml/README.md)). **No real training has been run yet** — every metric in [docs/model.md](docs/model.md) stays `[TBD]` until a real checkpoint is trained and evaluated and the numbers copied in by hand; never fabricate them.
- **`backend/`** — a working FastAPI app: auth + role-based access control, patients, cases, upload + image quality checks, prediction (real model if a checkpoint exists, otherwise a clearly-labelled mock), the growth review agent (see below), doctor decisions, PDF export, settings, a data-retention cleanup task, and a demo-data seed script. SQLite via Alembic migrations (see [backend/README.md](backend/README.md)). The SD-based reference table is an intentionally empty `[TBD — to verify]` template.
- **`frontend/`** — a React + TypeScript + Vite + Tailwind app translating every `design/` screen pixel-for-pixel (see [frontend/README.md](frontend/README.md)).
- **CI/CD** — GitHub Actions run all three test suites + the frontend build on every push/PR (`.github/workflows/ci.yml`); a deploy workflow ships the frontend to Vercel and triggers a Render deploy after CI passes on `main` (`.github/workflows/deploy.yml`). See [README.md#deployment-setup-vercel--render--github-actions](README.md#deployment-setup-vercel--render--github-actions).

## Repo layout (planned)

See [CLAUDE.md](CLAUDE.md#repo-layout-planned) for the full layout (`docs/`, `design/`, `backend/`, `frontend/`, `ml/`).

## How to run things

```bash
pip install -r ml/requirements.txt
pytest ml
```

runs the ML unit tests (small fake dataset, `pretrained=False` — no RSNA download or network access needed).

```bash
python ml/train.py --config ml/config/config.yaml
python ml/evaluate.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt
```

trains/evaluates against the real dataset (config.yaml must point at it first — see [docs/data.md](docs/data.md)). For GPU training, see `ml/notebooks/train_kaggle.ipynb`.

```bash
pip install -r backend/requirements.txt
cd backend && alembic upgrade head && uvicorn app.main:app --reload
```

runs the backend API (Swagger UI at `/docs`); `pytest` from `backend/` runs its tests (own temp SQLite DB, migrated with Alembic, no network/LLM calls needed). See [backend/README.md](backend/README.md) for the seed script and full details.

```bash
cd frontend && npm install && npm run dev    # dev server, proxies /api to the backend
npm run test                                 # vitest, from frontend/
npm run build                                # tsc -b && vite build
```

See [frontend/README.md](frontend/README.md). CI (`.github/workflows/ci.yml`) runs all three test suites + the frontend build on every push/PR; deploys (`.github/workflows/deploy.yml`) go to Vercel + Render after CI passes on `main` — see [README.md#deployment-setup-vercel--render--github-actions](README.md#deployment-setup-vercel--render--github-actions) for the one-time setup checklist.

## Frontend design (locked)

The approved UI design for every screen lives in `design/` (see `design/README.md` and [docs/design.md](docs/design.md#design-file-map) for the file-to-screen-to-route mapping).

> The frontend must match the files in design/ exactly: same layout, spacing, sizes, colours, fonts (IBM Plex Sans and IBM Plex Mono), copy, icons, states and light/dark themes. Use the LIGHT and DARK token strings in each file's renderVals() as the theme CSS variables. Do not redesign, restyle or "improve" any screen. If something in design/ is unclear or cannot be built as drawn, ask before changing it.

## Coding conventions

Same as [CLAUDE.md](CLAUDE.md#coding-conventions):

- Model: Python/PyTorch, pretrained CNN backbone, sex concatenated into the regression head (`ml/boneage/model.py`), Grad-CAM for heatmaps (`ml/boneage/gradcam.py`), uncertainty via MC dropout (`ml/boneage/inference.py`). Stack confirmed.
- Backend: FastAPI (`backend/app/`). The growth review agent (`backend/app/agent/`) is built on the **OpenAI Agents SDK**. Its flag decision (`tools.py`) must be deterministic and testable; the LLM only writes the explanatory note (`note_writer.py`), given only structured numbers/labels. Role checks go through `backend/app/deps.py`'s `require_roles(...)` on every endpoint.
- Frontend: React + TypeScript + Vite + Tailwind, built by translating each `design/` file pixel-for-pixel (see [Frontend design (locked)](#frontend-design-locked) above), theming via CSS variables, status always labelled with text (never colour alone).
- No fabricated medical facts, thresholds, or accuracy numbers — use `[TBD]`.
- Consistent naming: **BoneAge AI**, **growth review agent**, **review queue**, **case report**.

## Project rules

1. Decision support only — never state or imply a diagnosis.
2. No invented numbers — mark unknowns `[TBD]`.
3. The growth review agent's flag/no-flag decision is rule-based and auditable; it never alters the model's predicted bone age.
4. Cross-link documentation rather than duplicating it.
5. Respect dataset licensing (RSNA: non-commercial research/education use with attribution). See [docs/data.md](docs/data.md).

---

## The growth review agent

This section is the authoritative spec for the in-product agent that reviews each case after the CNN produces a bone age estimate. Any agent framework code (prompts, tool definitions, orchestration) should implement this contract.

**Implemented** in `backend/app/agent/` (`tools.py`, `reference_table.py`, `note_writer.py`, `review.py`) — see [backend/README.md#the-growth-review-agent](backend/README.md#the-growth-review-agent). It supports two configurable rule types for `get_normal_range` (both described generically as `normal_range_settings` below): **SD-based**, looking up a mean/SD reference table (`backend/data/reference_tables/greulich_pyle_sd_reference.json` — shipped as an empty `[TBD — to verify]` template, so this rule type currently returns "cannot determine" for every case until populated) and **fixed-months**, a flat ± N months around chronological age (works immediately, and is the default).

### Goal

Given a case's predicted bone age (with uncertainty) and the patient's chronological age, decide whether the case needs a doctor's attention, and if so, explain *why* in plain clinical language — without ever diagnosing the patient or overriding the model's number.

### Inputs

- `bone_age_months` — model's predicted bone age, in months.
- `bone_age_uncertainty` — model's uncertainty estimate for that prediction.
- `sex` — patient's sex (used both by the model and by the normal-range lookup).
- `date_of_birth`, `xray_date` — used to compute chronological age.
- `normal_range_settings` — the configured reference table/threshold, based on Greulich & Pyle–derived SD reference data (exact tables `[TBD, to verify]`); demo default shown in the UI as ±2 SD; both table and threshold are admin-configurable settings, not hard-coded in the agent. See [docs/requirements.md](docs/requirements.md) and [docs/model.md](docs/model.md).
- `auto_clear_enabled` — whether in-range cases should be auto-cleared or always routed to a human (configurable).
- Optional: prior scans for the same patient, referral reason, height/weight.

### Tools (deterministic, auditable — the LLM calls these, never substitutes its own arithmetic)

| Tool | Purpose |
|---|---|
| `compute_chronological_age(date_of_birth, xray_date)` | Returns chronological age in months from the two dates. |
| `get_normal_range(sex, chronological_age_months)` | Looks up the configured normal range for this sex/age band from the reference table in settings. Returns the acceptable gap range (e.g. in SD or months) — never a hard-coded value in code. |
| `compare_gap(bone_age_months, chronological_age_months, normal_range)` | Rule-based comparison: returns whether the gap is within range, delayed (bone age lags chronological age), or advanced (bone age exceeds chronological age), plus the magnitude. |
| `write_doctor_note(comparison_result, possible_causes_reference, model_uncertainty)` | The one LLM-authored step: drafts a short note for the doctor summarising the finding and possible causes to check. Does not decide the flag — it explains a decision already made by `compare_gap`. Receives only structured numbers and labels (sex, ages, gap, threshold, flag) — never the image or patient name/ID (see Guardrails below). |

### Decision rules

1. Compute chronological age via `compute_chronological_age`.
2. Look up the applicable normal range via `get_normal_range(sex, chronological_age_months)`.
3. Compare via `compare_gap`. 
   - **Within range** → case is marked "within expected range." If `auto_clear_enabled`, it is auto-cleared; otherwise it still appears in the queue marked as such.
   - **Outside range (delayed or advanced)** → case is flagged.
   - **Model uncertainty too high** (per configured threshold) → case is flagged regardless of the gap, noting the uncertainty as the reason.
4. On flag, call `write_doctor_note` to produce a short explanation naming the direction (delayed/advanced), magnitude, and possible causes the doctor may consider (e.g. growth hormone deficiency, hypothyroidism, constitutional delay, early puberty) — phrased as possibilities to check, never as a diagnosis.
5. Flagged cases enter the review queue. The doctor's decision (confirm flag / within expected range / model looks wrong — re-read manually) is recorded against the case and is the final word; the agent's flag is advisory only.

### Outputs

- `flag_status`: `cleared` | `flagged` | `needs_review` (uncertain).
- `gap_direction`: `within_range` | `delayed` | `advanced`.
- `gap_magnitude`: numeric gap vs. chronological age (and vs. the configured range).
- `doctor_note`: short, plain-language explanation + possible causes to check (LLM-authored, grounded in the rule-based result — never free-floating).
- Case enters or bypasses the review queue per `flag_status` and `auto_clear_enabled`.

### Guardrails

- **Never diagnose.** Output phrasing is always "possible causes the doctor may consider," never a diagnosis or clinical conclusion.
- **Never change the model's number.** The agent reads `bone_age_months`; it cannot edit, override, or re-run the prediction.
- **Always defer to the doctor.** The agent's flag is advisory; the doctor's recorded decision is authoritative and final.
- **Flag when uncertain.** If the model's uncertainty exceeds the configured threshold, the agent must flag for review rather than silently clearing, even if the point estimate looks in-range.
- **No hard-coded medical thresholds in agent code.** All ranges/thresholds come from `normal_range_settings`, which is admin-configurable (see [docs/requirements.md](docs/requirements.md) and the Settings screen in [docs/design.md](docs/design.md)).
- **Auditability.** Every flag decision must be traceable to the deterministic tool outputs (`compare_gap` result), not to an opaque LLM judgment call.
- **Data minimisation in the LLM call.** `write_doctor_note` must only be passed structured numbers and labels (sex, ages, gap, threshold, flag) — never the X-ray image or the patient's name/ID. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md#privacy).

### Example input/output

**Input:**
```json
{
  "sex": "female",
  "date_of_birth": "2016-03-10",
  "xray_date": "2026-11-20",
  "bone_age_months": 150,
  "bone_age_uncertainty_months": 4,
  "normal_range_settings": { "reference_table": "Greulich & Pyle-based SD reference [TBD, to verify]", "threshold": "±2 SD (default, configurable)" },
  "auto_clear_enabled": true
}
```

**Output:**
```json
{
  "chronological_age_months": 128,
  "gap_direction": "advanced",
  "gap_magnitude_months": 22,
  "flag_status": "flagged",
  "doctor_note": "Predicted bone age (150 months) is notably advanced relative to chronological age (128 months), outside the configured normal range for this patient's sex and age. Possible causes the doctor may consider include early puberty or other causes of advanced skeletal maturation. Model uncertainty for this case is low (±4 months). Please review alongside clinical history."
}
```

This is an illustrative example only — no real thresholds, reference tables, or statistics are implied beyond what is written in [docs/requirements.md](docs/requirements.md) and [docs/model.md](docs/model.md) (both marked `[TBD]` where not yet decided).

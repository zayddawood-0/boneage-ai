# CLAUDE.md

Context for Claude Code sessions working in this repository. Keep this file in sync with [AGENTS.md](AGENTS.md) — they should never contradict each other. If you update one, check the other.

## What this project is

**BoneAge AI** (working name) is a hackathon healthcare project. A CNN trained on the RSNA Bone Age dataset estimates a child's bone age from a left-hand X-ray (using the child's sex as an extra input) and compares it with chronological age computed from date of birth and X-ray date. A **growth review agent** flags cases where the gap falls outside a configurable normal range and writes a short note for a doctor explaining what to check. A doctor always makes the final call.

**This is decision support only — never a diagnosis.** Any code, copy, log message, or docstring that implies the system diagnoses a condition is a bug. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md).

Full product description: [README.md](README.md). Requirements: [docs/requirements.md](docs/requirements.md).

## Current state

The repo is scaffolded (`backend/`, `frontend/`, `ml/`, `design/`), but only `ml/` has real code so far: the RSNA data pipeline (config, preprocessing, augmentation, `Dataset`/`DataLoader`) **and** the model itself — architecture, training loop, evaluation, Grad-CAM, MC-dropout inference, a Kaggle training notebook, and unit tests (see [ml/README.md](ml/README.md)). **No real training has been run yet** — every metric in [docs/model.md](docs/model.md) is still `[TBD]`; do not fill those in until a real checkpoint has actually been trained and evaluated (e.g. via the Kaggle notebook) and the numbers copied in by hand. `backend/` and `frontend/` are placeholders (a README + a bare config file each) — no FastAPI app and no React app exist yet. Check the repo layout below before assuming a path exists.

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
├── backend/                   # placeholder only (README + requirements.txt) — FastAPI app not yet written
├── frontend/                  # placeholder only (README + package.json) — React app not yet written
├── ml/                         # data pipeline + model — real code, see ml/README.md
│   ├── boneage/                # config, seed, splits, transforms, datasets, dataloaders,
│   │                            # model, metrics, training, evaluation, gradcam, inference
│   ├── config/                 # config.example.yaml (tracked) / config.yaml (gitignored, local paths)
│   ├── notebooks/               # train_kaggle.ipynb — GPU training/evaluation on Kaggle
│   ├── train.py / evaluate.py    # CLI entry points
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

Everything else is still a placeholder — do not invent commands that don't exist yet, update this file the moment real tooling lands instead:

- [ ] TODO: backend dev server command
- [ ] TODO: frontend dev server command
- [ ] TODO: backend/frontend test commands
- [ ] TODO: lint/typecheck commands

## Coding conventions

*Tech stack confirmed; see [README.md](README.md#tech-stack) and [docs/model.md](docs/model.md), [docs/architecture.md](docs/architecture.md).*

- **Model (Python/PyTorch):** pretrained CNN backbone with sex concatenated into the regression head (`ml/boneage/model.py`); Grad-CAM for explainability (`ml/boneage/gradcam.py`); uncertainty via MC dropout (`ml/boneage/inference.py`). Keep training/inference code separate from the FastAPI service; the backend should call `boneage.inference.predict`/`predict_single_image`, not reimplement model logic.
- **Backend (FastAPI):** the growth review agent's *flag decision* must stay in deterministic, testable Python functions/tools (`compute_chronological_age`, `get_normal_range`, `compare_gap`) — never let the LLM decide the flag itself. The LLM's role is limited to writing the explanatory note. The agent is built on the **OpenAI Agents SDK**. See [AGENTS.md](AGENTS.md#the-growth-review-agent) for the full contract.
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

# CLAUDE.md

Context for Claude Code sessions working in this repository. Keep this file in sync with [AGENTS.md](AGENTS.md) — they should never contradict each other. If you update one, check the other.

## What this project is

**BoneAge AI** (working name) is a hackathon healthcare project. A CNN trained on the RSNA Bone Age dataset estimates a child's bone age from a left-hand X-ray (using the child's sex as an extra input) and compares it with chronological age computed from date of birth and X-ray date. A **growth review agent** flags cases where the gap falls outside a configurable normal range and writes a short note for a doctor explaining what to check. A doctor always makes the final call.

**This is decision support only — never a diagnosis.** Any code, copy, log message, or docstring that implies the system diagnoses a condition is a bug. See [docs/safety-and-ethics.md](docs/safety-and-ethics.md).

Full product description: [README.md](README.md). Requirements: [docs/requirements.md](docs/requirements.md).

## Current state

As of this writing, **no application code exists yet** — this repo contains planning and design docs only. Do not assume a frontend, backend, or model pipeline is scaffolded. Check the repo layout below before assuming a path exists.

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
├── backend/                   # TODO — not yet created (FastAPI proposed)
├── frontend/                  # TODO — not yet created (React + TS + Vite proposed)
└── model/                      # TODO — not yet created (PyTorch training code, proposed)
```

## How to run things

No code exists yet, so there is nothing to run. Once scaffolding begins, update this section with real commands. Until then, treat every command below as a placeholder:

- [ ] TODO: backend dev server command
- [ ] TODO: frontend dev server command
- [ ] TODO: model training command
- [ ] TODO: test commands (backend, frontend, model)
- [ ] TODO: lint/typecheck commands

Do not invent commands that don't exist yet — update this file the moment real tooling lands instead.

## Coding conventions

*Tech stack confirmed; see [README.md](README.md#tech-stack) and [docs/model.md](docs/model.md), [docs/architecture.md](docs/architecture.md).*

- **Model (Python/PyTorch):** pretrained CNN backbone with sex concatenated into the regression head; Grad-CAM for explainability; uncertainty via MC dropout. Keep training/inference code separate from the FastAPI service; the backend should call a thin inference interface, not reimplement model logic.
- **Backend (FastAPI):** the growth review agent's *flag decision* must stay in deterministic, testable Python functions/tools (`compute_chronological_age`, `get_normal_range`, `compare_gap`) — never let the LLM decide the flag itself. The LLM's role is limited to writing the explanatory note. The agent is built on the **OpenAI Agents SDK**. See [AGENTS.md](AGENTS.md#the-growth-review-agent) for the full contract.
- **Frontend (React + TypeScript + Vite + Tailwind):** theme via CSS variables (see [docs/design.md](docs/design.md#design-tokens)), never hard-code hex colours in components. Status (normal/flagged) must always carry a text label, never colour alone.
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

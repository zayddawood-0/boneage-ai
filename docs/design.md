# Design (UI/UX Spec)

Part of the [BoneAge AI](../README.md) documentation set. See also: [requirements.md](requirements.md), [architecture.md](architecture.md).

This document specifies the interactive mockup already designed for BoneAge AI: every screen, its components and states, the navigation map, design tokens, typography, accessibility rules, and the light/dark theming approach.

## Design lock

The approved UI design for every screen is the set of files in [`design/`](../design/README.md) — this document describes them, it does not supersede them.

> The frontend must match the files in design/ exactly: same layout, spacing, sizes, colours, fonts (IBM Plex Sans and IBM Plex Mono), copy, icons, states and light/dark themes. Use the LIGHT and DARK token strings in each file's renderVals() as the theme CSS variables. Do not redesign, restyle or "improve" any screen. If something in design/ is unclear or cannot be built as drawn, ask before changing it.

See [CLAUDE.md](../CLAUDE.md#frontend-design-locked) / [AGENTS.md](../AGENTS.md#frontend-design-locked) for the same rule in agent-facing form.

## Design file map

Each design file maps to one screen and route, as listed in [`design/README.md`](../design/README.md):

| Design file | Screen (this doc) | Route (suggested) |
|---|---|---|
| `design/Login.html` | [1. Sign in](#1-sign-in) | `/login` |
| `design/Main.html` | [2. Dashboard](#2-dashboard) (light theme) | `/` |
| `design/Dark.html` | [2. Dashboard](#2-dashboard) (dark theme reference — same markup as `Main.html`) | — |
| `design/NewAnalysis.html` | [3. New analysis](#3-new-analysis-3-step-flow) (3-step flow) | `/analysis/new` |
| `design/Queue.html` | [4. Review queue](#4-review-queue) | `/queue` |
| `design/Case.html` | [5. Case report](#5-case-report) | `/cases/:id` |
| `design/Patients.html` | [6. Patients](#6-patients) | `/patients` |
| `design/Model.html` | [7. Model performance](#7-model-performance) | `/model` |
| `design/Settings.html` | [8. Settings](#8-settings) | `/settings` |

Links between design files use `href="X.dc.html"` — map each to the route above. See `design/README.md` for how to read the `<x-dc>`/`renderVals()` format.

## Visual direction

- **Tone:** warm and clinical, no blue.
- **Typography:** IBM Plex Sans (UI text), IBM Plex Mono (numbers — ages, measurements, MAE figures, etc.).
- **Status colour:** pine green = normal / primary actions; amber/ochre = flagged. **Status is never shown by colour alone — always paired with a text label** (e.g. a pill reading "Flagged" or "Normal," not just a coloured dot).
- **Heatmap colour scale:** inferno-style — `#3B0F70 → #B73779 → #FC8961 → #FCFDBF`.
- Every screen supports light and dark themes via a toggle.

## Design tokens

CSS variables, shared across all screens — components must reference these, never hard-code hex values.

| Token | Light | Dark |
|---|---|---|
| `--bg` | `#F5F3EF` | `#12110F` |
| `--surface` | `#FFFFFF` | `#1C1A17` |
| `--ink` | `#1C1917` | `#EDE9E3` |
| `--muted` | `#5C5650` | `#A8A097` |
| `--border` | `#E5E0D8` | `#2E2A25` |
| `--accent-text` | `#24614B` | `#7CC4A4` |
| primary button background | `#24614B` (white text) | `#24614B` (white text) |
| `--ok-bg` / `--ok-text` | `#E3F0E9` / `#1A4D3A` | `#1E3A30` / `#B5E3CC` |
| `--flag` | `#B45309` | `#F2A65A` |
| `--flag-bg` / `--flag-text` | `#FDF0DC` / `#7A3E00` | `#3A2610` / `#FFC98A` |
| sidebar background | `#1C1917` (both themes) | `#1C1917` (both themes) |

Heatmap scale (not theme-dependent — same in light and dark): `#3B0F70 → #B73779 → #FC8961 → #FCFDBF`.

## Typography

- UI text: **IBM Plex Sans**, weights `[TBD — team to confirm: likely 400/500/600]`.
- Numeric data (ages, MAE, measurements, counts): **IBM Plex Mono**, tabular figures where supported.
- Heading scale, line-height, and exact size steps: `[TBD]`.

## Screens

For each screen: components, and states it must handle (empty, loading, error, flagged, normal — where applicable).

### 1. Sign in
- **Components:** email/credential fields, sign-in button, BoneAge AI branding, theme toggle.
- **States:** default, loading (authenticating), error (invalid credentials).

### 2. Dashboard
- **Components:** summary cards (e.g. cases today, flagged count, pending review — exact metrics `[TBD]`), new analysis panel (entry point into the 3-step flow), result preview (large X-ray + heatmap for the most recent case), growth review agent panel (latest agent note), bone age vs. chronological age chart, review queue preview.
- **States:** empty (no cases yet), loading (cards/chart fetching), error (data fetch failed), normal.
- **Access:** doctor only (see [requirements.md](requirements.md#user-roles)).

### 3. New analysis (3-step flow)
- **Step 1 — Patient details:** name/ID, sex, date of birth, X-ray date (chronological age computed and shown live), optional height/weight, referral reason.
- **Step 2 — Upload:** drag-and-drop or file picker for PNG/JPG/DICOM; runs image quality checks (hand detected, orientation, resolution, burned-in details removed) and surfaces failures before proceeding.
- **Step 3 — Result:** large X-ray + Grad-CAM heatmap, predicted bone age + uncertainty, growth review agent panel with flag status and note, action to send to review queue or auto-clear.
- **States:** empty (step not started), loading (quality check running / inference running), error (quality check failed, upload failed, inference failed), flagged result, normal/cleared result.
- **Access:** doctor and radiographer.

### 4. Review queue
- **Components:** status tabs (e.g. Flagged / Within range / All — exact set `[TBD]`), search, sex filter, sort control, table (patient, sex, chronological age, bone age, gap, status, date), pagination.
- **States:** empty (no cases matching filter), loading, error, populated (mixed flagged/normal rows — status always shown as a text label pill, e.g. "Flagged" in `--flag-text` on `--flag-bg`, "Normal" in `--ok-text` on `--ok-bg`).
- **Access:** doctor (full) and radiographer (read-only — no decision/export/follow-up actions).

### 5. Case report
- **Components:** X-ray + heatmap viewer, measurements (bone age, chronological age, gap, uncertainty), growth review agent reasoning/note, previous scans for the patient (if any), doctor decision control (confirm flag / within expected range / model looks wrong — re-read manually), manual bone age reading field, notes field, PDF export action, follow-up scheduling action.
- **States:** loading, error, flagged (amber/ochre treatment + "Flagged" label), normal (pine green + "Normal" label), decision-recorded (shows doctor's saved decision + timestamp).
- **Access:** doctor (full) and radiographer (read-only — decision controls, PDF export, and follow-up scheduling are hidden/disabled).

### 6. Patients
- **Components:** patient list/search, per-patient case history.
- **States:** empty, loading, error, populated.
- **Access:** doctor and radiographer.

### 7. Model performance
- **Components:** MAE overall / by sex / by age band, predicted-vs-true scatter/line chart, model card summary, stated limitations section.
- **States:** loading, error, populated. All figures shown here are placeholders (`[TBD]`) until real evaluation exists — see [model.md](model.md). The empty/placeholder state should read `[TBD]`/"pending evaluation," not a fabricated number.
- **Access:** doctor and admin only (see [requirements.md](requirements.md#user-roles)).

### 8. Settings
- **Components:** flagging rules (normal-range threshold, Greulich & Pyle–based reference table selection, auto-clear toggle), agent behaviour (e.g. uncertainty threshold for forced review), theme toggle + age unit selection, data & privacy (retention — default 30 days, de-identification controls), account/user management.
- **States:** default, saving, saved confirmation, error (save failed).
- **Access:** admin only (see [requirements.md](requirements.md#user-roles)). The theme toggle and age-unit preference are personal settings and remain available to all roles outside this screen (e.g. from the header), even though they're also shown here.

## Navigation map

```
Sign in
  └─ Dashboard (home after login)
       ├─ New analysis (3-step) ──→ Result (step 3) ──→ (sent to) Review queue or auto-cleared
       ├─ Review queue ──→ Case report ──→ (export PDF / schedule follow-up)
       ├─ Patients ──→ Patient detail ──→ Case report
       ├─ Model performance
       └─ Settings
Sidebar: persistent across all post-login screens (Dashboard, New analysis, Review queue, Patients, Model performance, Settings).
```

## Accessibility rules

- Meet **WCAG AA** contrast minimums for text and UI components in both light and dark themes using the tokens above.
- **Status is never colour-only** — every flagged/normal/cleared indicator pairs colour with a text label.
- All interactive elements (buttons, tabs, filters, table sort controls) must be keyboard-operable and have visible focus states.
- Charts (bone age vs. chronological age, predicted-vs-true, MAE breakdowns) must have text alternatives (e.g. a table view or descriptive summary) for screen reader users.
- Heatmap overlays must have an accessible description of what the highlighted region represents (not just a visual-only cue).
- Form fields (patient intake, settings) must have associated labels, not placeholder-only labelling.
- Exact heading structure / landmark regions / ARIA roles per screen: `[TBD]`.

## Light/dark theming approach

- All colour values are defined once as CSS variables (see token table above) and consumed by components — no component-level hard-coded hex values.
- A theme toggle (available from Settings and likely the sidebar/header — exact placement `[TBD]`) switches the active token set.
- The sidebar background (`#1C1917`) is intentionally constant across both themes, so it anchors navigation regardless of theme.
- The heatmap colour scale is constant across themes (it encodes model attention, not UI state).

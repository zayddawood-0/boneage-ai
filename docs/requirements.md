# Requirements

Part of the [BoneAge AI](../README.md) documentation set. See also: [design.md](design.md), [architecture.md](architecture.md), [safety-and-ethics.md](safety-and-ethics.md).

> Reminder: this is a decision-support tool. No requirement in this document should be read as enabling diagnosis — see [safety-and-ethics.md](safety-and-ethics.md).

## User roles

| Role | Description |
|---|---|
| **Doctor** (paediatrician / radiologist) | Reviews flagged and cleared cases, views case reports, records decisions, exports PDF reports, schedules follow-ups. Final decision authority. Full access except user management and settings management. |
| **Radiographer** | Enters patient details, uploads X-rays, runs new analyses, and views patients. Review queue access is read-only (no decision recording, PDF export, or follow-up scheduling). No Model Performance or Settings access. |
| **Admin** | Configures flagging rules, normal-range reference tables, and agent behaviour (Settings); views Model Performance; manages user accounts. Not part of the day-to-day clinical workflow (no new analysis, patient intake, or case decisions). |

**Role-to-screen permission matrix (confirmed):**

| Screen / action | Doctor | Radiographer | Admin |
|---|---|---|---|
| Dashboard | ✓ | — | — |
| New analysis | ✓ | ✓ | — |
| Review queue (view) | ✓ | ✓ (read-only) | — |
| Review queue (record decision / export PDF / schedule follow-up) | ✓ | — | — |
| Case report (view) | ✓ | ✓ (read-only) | — |
| Patients | ✓ | ✓ | — |
| Model performance | ✓ | — | ✓ |
| Settings (flagging rules, agent behaviour, data & privacy) | — | — | ✓ |
| User management | — | — | ✓ |

Theme toggle and age-unit display preference are personal, not administrative, and remain available to all signed-in roles regardless of Settings access.

## Functional requirements

### Authentication & accounts
- **FR-1.** The system shall allow a clinician to sign in before accessing any patient data or screens.
- **FR-2.** The system shall support the three roles above (doctor, radiographer, admin), enforcing the permission matrix in [User roles](#user-roles) server-side, not just by hiding UI elements.

### Patient intake
- **FR-3.** The system shall allow entry of patient name/ID, sex, date of birth, and X-ray date.
- **FR-4.** The system shall compute chronological age automatically from date of birth and X-ray date — it shall never require the user to enter chronological age manually.
- **FR-5.** The system shall allow optional entry of height, weight, and referral reason.

### Image upload & quality
- **FR-6.** The system shall accept a left-hand X-ray in PNG, JPG, or DICOM format.
- **FR-7.** The system shall run image quality checks before inference: hand detected, orientation correct, resolution sufficient, and burned-in patient details removed/flagged.
- **FR-8.** The system shall block or warn before running inference on an image that fails quality checks, rather than silently proceeding.

### Prediction
- **FR-9.** The system shall predict bone age using the uploaded image and the patient's sex as model inputs.
- **FR-10.** The system shall return an uncertainty estimate alongside the bone age prediction.
- **FR-11.** The system shall generate and display an attention heatmap (e.g. Grad-CAM) for the prediction.

### Growth review agent
- **FR-12.** The system shall compare predicted bone age to chronological age using a configurable, sex- and age-specific normal range (see [AGENTS.md](../AGENTS.md#the-growth-review-agent)).
- **FR-13.** The normal-range threshold and reference table shall be configurable settings, not hard-coded values. Reference basis: Greulich & Pyle–derived SD reference data (exact tables `[TBD, to verify]`); demo default displayed in the UI: ±2 SD, configurable in Settings.
- **FR-14.** Cases within the normal range shall be auto-cleared when auto-clear is enabled in settings; otherwise they shall still appear in the queue marked as within range.
- **FR-15.** Cases outside the normal range, or where the model's uncertainty exceeds a configured threshold, shall be flagged and routed to the review queue.
- **FR-16.** For flagged cases, the agent shall write a short note explaining the flag and listing possible causes the doctor may consider (e.g. growth hormone deficiency, hypothyroidism, constitutional delay, early puberty) — phrased as possibilities, never a diagnosis.
- **FR-17.** The agent's flag decision shall be produced by deterministic, auditable logic; only the explanatory note shall be LLM-generated.
- **FR-18.** The agent shall never modify the model's predicted bone age value.

### Review queue & case report
- **FR-19.** The system shall provide a review queue with status tabs, search, sex filter, sorting, and pagination.
- **FR-20.** The system shall provide a case report showing the X-ray, heatmap, measurements, agent reasoning, and the patient's previous scans (if any).
- **FR-21.** The system shall allow the doctor to record a decision on a case: confirm flag, mark within expected range, or flag the model's read as wrong (manual re-read).
- **FR-22.** The system shall allow the doctor to enter an optional manual bone age reading and free-text notes.
- **FR-23.** The system shall allow the doctor to export a case report as a PDF.
- **FR-24.** The system shall allow the doctor to schedule a follow-up scan from the case report.

### Patients & model performance
- **FR-25.** The system shall provide a patients list/view across cases.
- **FR-26.** The system shall provide a model performance view showing MAE overall, by sex, and by age band; a predicted-vs-true chart; a model card; and stated limitations. All figures `[TBD]` until real evaluation results exist — see [model.md](model.md).

### Settings
- **FR-27.** The system shall allow configuration of flagging rules (normal-range threshold/reference table, auto-clear on/off) and agent behaviour. Admin role only.
- **FR-28.** The system shall allow switching between light and dark themes, and selection of age display units, available to all signed-in roles.
- **FR-29.** The system shall provide data & privacy settings (retention — default 30 days, de-identification — see [safety-and-ethics.md](safety-and-ethics.md)) and account/user management. Admin role only.

## Non-functional requirements

- **NFR-1 (Performance):** Inference (quality checks + prediction + heatmap) should return within a demo-acceptable time. Target latency: `[TBD]`.
- **NFR-2 (Privacy):** Patient data and images must be handled per [safety-and-ethics.md](safety-and-ethics.md) — de-identification where possible, default retention period of 30 days, and no third-party sharing beyond what's documented (the agent's LLM call receives only structured numbers/labels, never images or patient names).
- **NFR-3 (Accessibility):** UI must meet WCAG AA at minimum — sufficient colour contrast in both themes, status never conveyed by colour alone (always paired with a text label), keyboard navigability, screen-reader-friendly labels on charts/heatmaps.
- **NFR-4 (Theming):** Every screen must support light and dark themes via the shared CSS variable token set (see [design.md](design.md#design-tokens)) with no screen-specific hard-coded colours.
- **NFR-5 (Auditability):** Every agent flag decision must be traceable to its deterministic inputs (gap calculation, normal-range lookup) — not just to an LLM-generated note. Doctor decisions must be recorded with a timestamp and author for audit purposes.
- **NFR-6 (Reliability):** The system should degrade safely — e.g. if image quality checks fail, or model uncertainty is very high, the case must be flagged for human review rather than silently cleared.

## User stories (with acceptance criteria)

**US-1 — As a radiographer, I want to enter patient details and upload an X-ray, so that I can start an analysis.**
- AC: chronological age is computed automatically from date of birth + X-ray date and displayed before submission.
- AC: upload accepts PNG/JPG/DICOM; unsupported formats are rejected with a clear message.
- AC: image quality issues (no hand detected, wrong orientation, low resolution, burned-in identifiers) are surfaced before the case proceeds to prediction.

**US-2 — As a doctor, I want to see the predicted bone age with an uncertainty estimate and a heatmap, so that I can judge how much to trust the prediction.**
- AC: the case report shows bone age, uncertainty, and the Grad-CAM heatmap overlaid on the X-ray.
- AC: the heatmap uses the inferno-style colour scale from [design.md](design.md#design-tokens).

**US-3 — As a doctor, I want cases where bone age and chronological age diverge to be flagged automatically, so that I don't miss them in a busy queue.**
- AC: a case outside the configured normal range appears in the review queue with status "Flagged" (text label, not colour alone).
- AC: the flagged case includes a short agent note naming the direction (delayed/advanced), magnitude, and possible causes to check.
- AC: a case within range is either auto-cleared or shown as "Within expected range," depending on the auto-clear setting.

**US-4 — As a doctor, I want to record my own decision on a flagged case, so that the system reflects my clinical judgement, not just the model's.**
- AC: I can select confirm flag / within expected range / model looks wrong (manual re-read).
- AC: I can enter a manual bone age reading and free-text notes.
- AC: my decision and notes are saved and visible in the case's history.

**US-5 — As a doctor, I want to export a case report as a PDF and schedule a follow-up, so that I can share it or close the loop with the patient.**
- AC: PDF export includes the X-ray, heatmap, measurements, agent note, and my recorded decision.
- AC: I can schedule a follow-up scan date from the case report.

**US-6 — As an admin, I want to configure the normal-range threshold and reference table, so that the flagging logic reflects our clinic's chosen standard, not a hard-coded assumption.**
- AC: the Settings screen exposes the threshold (default ±2 SD) and reference table selection as editable fields.
- AC: changing these settings affects future flag decisions without requiring a code change.

**US-7 — As any user, I want the UI to work in both light and dark themes with accessible contrast, so that I can use it comfortably in different clinical settings.**
- AC: every screen renders correctly in both themes using the shared token set.
- AC: status indicators always include a text label alongside colour.

## Out of scope (for the hackathon build)

- Any feature that issues a diagnosis or treatment recommendation.
- Integration with a real hospital EHR/PACS system.
- Multi-hospital / multi-tenant support.
- Mobile native apps (web only).
- Real-time collaborative review (multiple doctors editing the same case simultaneously).
- Clinical validation / regulatory submission (this is a hackathon prototype, not a cleared medical device).
- Support for X-ray views other than left hand.
- Non-English localisation.

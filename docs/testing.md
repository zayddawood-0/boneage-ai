# Testing

Part of the [BoneAge AI](../README.md) documentation set. See also: [requirements.md](requirements.md), [AGENTS.md](../AGENTS.md#the-growth-review-agent), [tasks.md](tasks.md).

## Model evaluation

- Evaluate on the RSNA test split: MAE overall, by sex, by age band, % within ±12 months (see [model.md](model.md#evaluation-metrics)). All figures `[TBD]` until training completes.
- Evaluate generalisation and gap-flagging behaviour on DHA and/or RHPE, since RSNA lacks chronological age (see [data.md](data.md#handling-chronological-age-rsna-gap)).
- Sanity-check Grad-CAM heatmaps visually on a sample of cases — attention should plausibly fall on hand/wrist growth-plate regions, not background artefacts.
- Check uncertainty calibration qualitatively (do high-uncertainty cases correspond to genuinely harder images, e.g. poor quality or borderline age ranges) — exact calibration method `[TBD]`.

## Agent rule unit tests

The growth review agent's **flag decision** must be deterministic — this is the most important thing to unit-test, since it's the auditable core described in [AGENTS.md](../AGENTS.md#the-growth-review-agent). Suggested test cases:

- **Boundary cases at the threshold:** a gap exactly at the configured normal-range boundary (e.g. exactly ±2 SD) — verify the decision is consistent and documented (inclusive vs. exclusive boundary — decide and test this explicitly, since it's a common off-by-one source).
- **Just inside vs. just outside the boundary:** two cases differing by a small margin that straddle the threshold, to confirm the flag flips correctly.
- **Both sexes:** run the same chronological age and gap through both `male` and `female` normal-range lookups, confirming `get_normal_range` returns sex-specific values and `compare_gap` respects them.
- **Delayed case:** bone age meaningfully below chronological age → expect `gap_direction: delayed`, flagged.
- **Advanced case:** bone age meaningfully above chronological age → expect `gap_direction: advanced`, flagged.
- **Within range:** gap inside the configured threshold → expect `within_range`; auto-clear behaviour tested both with `auto_clear_enabled: true` and `false`.
- **High uncertainty override:** a case with an in-range gap but uncertainty above the configured threshold → expect `flagged` (uncertainty reason), confirming uncertainty can force a flag even when the point estimate looks fine.
- **Chronological age computation:** `compute_chronological_age` tested against known date-of-birth/X-ray-date pairs, including edge cases (leap years, same-month birthdays).
- **Agent never changes the model's number:** regression test asserting `bone_age_months` passed in equals `bone_age_months` referenced in the agent's output/note.
- **Note content guardrail:** `write_doctor_note` output should never contain diagnostic-sounding language (e.g. assert it doesn't claim a definitive condition) — a simple keyword/phrasing check, or manual review of generated notes during QA.
- **Data minimisation guardrail:** assert the payload sent to `write_doctor_note` (OpenAI Agents SDK call) contains only structured numbers/labels (sex, ages, gap, threshold, flag) and never an image reference or patient name/ID.

## API tests

- Auth: login success/failure.
- Patients/cases CRUD: create, read, list with filters (status, sex), sort, pagination.
- Upload: valid PNG/JPG/DICOM accepted; invalid format rejected; quality-check failure path returns the specific issue(s).
- Predict: returns bone age, uncertainty, heatmap reference for a valid case.
- Agent review: returns flag status, gap direction/magnitude, doctor note for a case with a prediction.
- Decision: recording a decision persists correctly and is retrievable on the case.
- PDF export: returns a valid file for a decided case.
- Follow-up: scheduling persists and is retrievable.
- Settings: get/put round-trip, including normal-range config and auto-clear toggle.
- Role-based access: doctor, radiographer, and admin tokens each get the access (and only the access) defined in the permission matrix in [requirements.md](requirements.md#user-roles) — e.g. a radiographer token is rejected on `POST /cases/{id}/decision`, and a doctor token is rejected on `PUT /settings`.

## UI tests

- Each screen in [design.md](design.md#screens) renders its documented states (empty, loading, error, flagged, normal) correctly.
- Status is always rendered with both colour and a text label — test this explicitly (e.g. a snapshot/assertion that a status pill always has accessible text, not just a coloured background).
- Light/dark theme toggle correctly swaps all token-driven colours across every screen.
- Review queue filters (status tabs, sex filter, search, sort) correctly narrow the table; pagination works at boundary page counts (0 results, exactly one page, multiple pages).
- New analysis 3-step flow: chronological age updates live as date of birth/X-ray date change; upload step blocks progression on a failed quality check; result step correctly shows flagged vs. normal styling.
- Case report: doctor decision controls save and reflect the saved state on reload; PDF export and follow-up scheduling trigger their respective actions.
- Accessibility: keyboard navigation reaches every interactive control; contrast spot-checks against the token table in both themes.

## Demo script

See [demo-script.md](demo-script.md) for the full 3–4 minute judge walkthrough, using the seeded demo cases (`backend/scripts/seed_demo_data.py`) and the deployed (or local-fallback) app.

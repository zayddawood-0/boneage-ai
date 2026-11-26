# Safety & Ethics

Part of the [BoneAge AI](../README.md) documentation set. See also: [requirements.md](requirements.md), [AGENTS.md](../AGENTS.md#the-growth-review-agent), [data.md](data.md).

## Decision-support disclaimer

**BoneAge AI is decision support only. It is not a diagnostic device and does not diagnose any medical condition.**

- The CNN produces a bone age *estimate* with an uncertainty value — it is a measurement aid, not a clinical conclusion.
- The growth review agent's flag is an *alert that a case may warrant attention* — it never states or implies a diagnosis. Its note is phrased as "possible causes the doctor may consider," never as a finding of fact.
- The doctor's recorded decision (confirm flag / within expected range / model looks wrong — manual re-read) is the final word on every case. The system does not act on its own output.
- This disclaimer must be visible in the product (e.g. on the case report and/or persistently in the UI — exact placement `[TBD]`, but it must not be buried) and repeated in any demo or presentation of the project.
- This is a hackathon prototype: it has not undergone clinical validation or regulatory review, and must not be presented as cleared for real patient care.

## Bias & dataset population limits

- Training data (RSNA) and evaluation data (Digital Hand Atlas, RHPE) each cover specific, limited populations — see [data.md](data.md) for exact composition (DHA: Asian, African American, Caucasian, Hispanic children; RHPE: Colombian patients; RSNA: population demographics as provided by the challenge, not separately itemised here).
- The model's accuracy on populations, age ranges, or imaging equipment outside what these datasets represent is **unverified**. This must be stated plainly in the model card ([model.md](model.md#model-card-template)) and in the Model performance screen's limitations section ([design.md](design.md#7-model-performance)) — not glossed over.
- Sex is used as a direct model input (consistent with established bone-age practice) — the UI and docs should be clear this reflects a biological covariate used in the clinical bone-age literature, not an assumption that other factors don't matter.
- MAE-by-sex and MAE-by-age-band breakdowns (see [model.md](model.md#evaluation-metrics)) exist specifically so that uneven performance across subgroups is visible rather than hidden behind an overall average — review these before any claim of "the model works well."

## Privacy

- **De-identification:** the image-quality check step must detect and block/flag burned-in patient details (name, ID, date of birth printed on the X-ray) before the image is stored or used for inference (see [requirements.md](requirements.md#image-upload--quality)).
- **Data entered:** patient name/ID, sex, date of birth, X-ray date, optional height/weight/referral reason, and the image itself are all personal/health data. Minimise what's stored to what the product actually needs.
- **Retention:** default retention period for images and case data is **30 days**, configurable in the Data & privacy section of Settings ([design.md](design.md#8-settings)) — not left indefinite by default.
- **Access control:** role-based access (doctor/radiographer/admin, see [requirements.md](requirements.md#user-roles)) limits who can view patient-identifying data versus de-identified/aggregate data — e.g. Model performance and user/account management are restricted to doctor and admin respectively, per the permission matrix in [requirements.md](requirements.md#user-roles).
- **Third parties (LLM calls):** the growth review agent's note-writing step (built on the OpenAI Agents SDK) receives **only structured numbers and labels — sex, ages, gap, threshold, flag status** — and never the raw X-ray image or the patient's name/ID. This is a hard rule on the `write_doctor_note` tool call, not a configurable option (see [AGENTS.md](../AGENTS.md#guardrails)).
- **Demo data:** the hackathon demo uses dataset images only (RSNA/DHA/RHPE samples) with synthetic or clearly fake patient names/IDs — never real patient data, even anonymised.

## Human-in-the-loop

- Every case that is flagged — and, depending on settings, every case at all — is reviewable by a doctor before any downstream action (PDF export, follow-up scheduling) is taken.
- Auto-clear (when enabled) only changes queue visibility/triage priority; it does not prevent a doctor from finding and reviewing a cleared case later (e.g. via Patients or search).
- The agent's deterministic tools ensure the flag decision is auditable and reproducible — a doctor or admin can trace *why* a case was flagged back to the computed gap and the configured normal range, not just an opaque model/LLM judgement (see [AGENTS.md](../AGENTS.md#decision-rules)).
- The doctor can always override the agent (mark a flagged case as within expected range) or override the model (flag the model's read as wrong and enter a manual reading) — the system is designed so neither the model nor the agent has the last word.

## Failure modes and how the UI surfaces them

| Failure mode | How it's surfaced |
|---|---|
| Image quality too poor for a reliable prediction (no hand detected, bad orientation, low resolution) | Blocked before inference runs, with the specific issue named, at the upload step (see [design.md](design.md#3-new-analysis-3-step-flow)). |
| Burned-in patient details detected on the image | Blocked/flagged before storage, per the de-identification check above. |
| Model uncertainty above the configured threshold | Case is flagged regardless of the point-estimate gap, with the note explicitly citing uncertainty as the reason (see [AGENTS.md](../AGENTS.md#decision-rules)). |
| Model prediction looks implausible to the doctor | Doctor can select "model looks wrong — re-read manually" on the case report and enter a manual bone age reading (see [requirements.md](requirements.md#us-4--as-a-doctor-i-want-to-record-my-own-decision-on-a-flagged-case-so-that-the-system-reflects-my-clinical-judgement-not-just-the-models)). |
| Agent/LLM note generation fails or times out | Case should still be flagged/queued based on the deterministic `compare_gap` result even if the note is missing or shows an error state — the flag must never silently disappear because the LLM call failed. Exact fallback copy: `[TBD]`. |
| Backend/model service unavailable | Upload/analysis flow should show a clear error state rather than a silent failure or an incorrect "within range" result (see [design.md](design.md) error states per screen). |

## Summary principle

If a choice is ever between making the system seem more capable/automated and keeping a human clinician firmly in control of every clinical judgement, choose the latter. This applies to UI copy, agent prompt design, default settings (e.g. auto-clear defaults, uncertainty thresholds), and anything shown in a demo.

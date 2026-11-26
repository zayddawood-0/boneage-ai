# Model

Part of the [BoneAge AI](../README.md) documentation set. See also: [data.md](data.md), [architecture.md](architecture.md), [testing.md](testing.md).

No results in this document are real yet — every metric is marked `[TBD]` until training/evaluation actually happens. Do not fill these in with invented numbers.

## Architecture

- **Backbone:** a pretrained CNN (e.g. EfficientNet or ResNet — exact choice `[TBD]`), fine-tuned on RSNA.
- **Inputs:** the left-hand X-ray image, plus the patient's **sex** concatenated into the regression head (sex is a known strong covariate for bone age).
- **Output head:** regression output for bone age in months, plus an uncertainty estimate produced via **MC dropout** (multiple stochastic forward passes at inference time, with the resulting prediction spread reported as the uncertainty estimate) — chosen over a variance head or ensemble because it requires no change to the training loss and can be retrofitted onto the pretrained backbone.
- **Explainability:** Grad-CAM (or a similar CAM-based method) over the backbone's final convolutional layers to produce the attention heatmap shown in the case report, rendered with the inferno-style scale defined in [design.md](design.md#design-tokens).

## Inputs / outputs (summary)

| | |
|---|---|
| **Inputs** | Left-hand X-ray image (PNG/JPG/DICOM, preprocessed per [data.md](data.md#preprocessing)); patient sex |
| **Outputs** | Predicted bone age (months); uncertainty estimate; Grad-CAM heatmap |

Chronological age is **not** a model input or output — it's computed separately from date of birth and X-ray date and compared against the predicted bone age by the growth review agent (see [AGENTS.md](../AGENTS.md#the-growth-review-agent)).

## Loss

- Primary loss: MAE / L1 on bone age in months (standard for this task, consistent with how RSNA challenge submissions were scored). Secondary/auxiliary loss (e.g. for the uncertainty head, if applicable): `[TBD]`.

## Training plan

1. Preprocess RSNA images per [data.md](data.md#preprocessing).
2. Fine-tune the chosen backbone on the RSNA train split; validate on the RSNA validation split; hold out the RSNA test split for final internal evaluation.
3. Evaluate generalisation and the gap-flagging logic on DHA and/or RHPE (see [data.md](data.md#handling-chronological-age-rsna-gap)).
4. Hyperparameters (learning rate, batch size, epochs, optimizer, augmentation set): `[TBD]`.
5. Checkpointing/versioning approach for the hackathon: `[TBD]`.

## Evaluation metrics

- **MAE overall** (months): `[TBD]`.
- **MAE by sex:** `[TBD]`.
- **MAE by age band:** `[TBD]` (age band boundaries also `[TBD]`).
- **% of predictions within ±12 months of ground truth:** `[TBD]`.
- These are the metrics surfaced on the Model performance screen (see [design.md](design.md#7-model-performance)) — the screen should render `[TBD]`/"pending evaluation" rather than a placeholder number that could be mistaken for a real result.

## Explainability

- Grad-CAM heatmaps are generated per prediction and shown overlaid on the X-ray in the case report, using the inferno-style scale (`#3B0F70 → #B73779 → #FC8961 → #FCFDBF`).
- Heatmaps are intended to show *where* the model focused, as a sanity-check aid for the doctor — not as proof of correctness. This limitation should be stated in the model card and in the Model performance screen's limitations section.

## Uncertainty approach

- **Confirmed: MC dropout.** Multiple stochastic forward passes at inference time (dropout left active), with the spread of predictions reported as the uncertainty estimate. This must run fast enough to stay inline with inference for the demo (see [architecture.md](architecture.md#deployment-notes-hackathon-demo)); number of passes `[TBD]`.
- The uncertainty estimate feeds directly into the growth review agent's decision: predictions with uncertainty above a configured threshold are flagged for review regardless of the point-estimate gap (see [AGENTS.md](../AGENTS.md#decision-rules)).

## Model card template

| Field | Value |
|---|---|
| Model name | BoneAge AI CNN (working name) |
| Version | `[TBD]` |
| Intended use | Decision support for estimating bone age from a left-hand X-ray, for review by a qualified clinician. **Not a standalone diagnostic tool.** |
| Out-of-scope use | Any use as a sole basis for diagnosis or treatment; use on X-ray views other than left hand; use without clinician review. |
| Training data | RSNA Pediatric Bone Age Challenge 2017 (train/validation splits) — see [data.md](data.md). |
| Evaluation data | RSNA test split; Digital Hand Atlas and/or RHPE for external evaluation — see [data.md](data.md). |
| Metrics | MAE overall / by sex / by age band; % within ±12 months — all `[TBD]` pending training. |
| Known limitations | Population coverage of training/evaluation data is limited to the datasets listed in [data.md](data.md); performance on populations/age ranges outside those datasets is unverified. Heatmaps indicate attention, not correctness. Uncertainty estimates are model-internal and not a substitute for clinical judgement. |
| Ethical considerations | See [safety-and-ethics.md](safety-and-ethics.md) — decision support only, bias/population limits, privacy, human-in-the-loop. |
| Licence/attribution | RSNA: non-commercial research/education use with attribution. DHA/RHPE: per their stated terms — see [data.md](data.md#licence--attribution-requirements). |

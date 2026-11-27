# Model

Part of the [BoneAge AI](../README.md) documentation set. See also: [data.md](data.md), [architecture.md](architecture.md), [testing.md](testing.md).

No results in this document are real yet — every metric is marked `[TBD]` until training/evaluation actually happens. Do not fill these in with invented numbers.

## Architecture

- **Backbone:** a pretrained CNN (e.g. EfficientNet or ResNet — exact choice `[TBD]`), fine-tuned on RSNA.
- **Inputs:** the left-hand X-ray image, plus the patient's **sex** concatenated into the regression head (sex is a known strong covariate for bone age).
- **Output head:** regression output for bone age in months, plus an uncertainty estimate produced via **MC dropout** (multiple stochastic forward passes at inference time, with the resulting prediction spread reported as the uncertainty estimate) — chosen over a variance head or ensemble because it requires no change to the training loss and can be retrofitted onto the pretrained backbone.
- **Explainability:** Grad-CAM over the backbone's final convolutional layer when running on PyTorch (training/evaluation, `ml/boneage/gradcam.py`); Score-CAM — a gradient-free stand-in, see below — when running via ONNX Runtime in the deployed backend (`ml/boneage/score_cam.py`, `ml/boneage/onnx_inference.py`). Either way the heatmap is rendered with the same inferno-style scale defined in [design.md](design.md#design-tokens).

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
4. **Optimizer: confirmed AdamW**, with early stopping on validation MAE and a learning-rate schedule. Numeric hyperparameters (learning rate, batch size, epoch count, schedule type, augmentation strength): `[TBD]` — the values in `ml/config/config.example.yaml` are reasonable starting points for the implementation, not tuned/final settings.
5. Checkpointing: the best validation-MAE checkpoint is saved during training (see `ml/boneage/training.py`). Versioning approach beyond that for the hackathon: `[TBD]`.

## Evaluation metrics

- **MAE overall** (months): `[TBD]`.
- **MAE by sex:** `[TBD]`.
- **MAE by age band:** `[TBD]` (age band boundaries also `[TBD]`).
- **% of predictions within ±12 months of ground truth:** `[TBD]`.
- These are the metrics surfaced on the Model performance screen (see [design.md](design.md#7-model-performance)) — the screen should render `[TBD]`/"pending evaluation" rather than a placeholder number that could be mistaken for a real result.

## Explainability

Heatmaps are generated per prediction and shown overlaid on the X-ray in the case report, using the inferno-style scale (`#3B0F70 → #B73779 → #FC8961 → #FCFDBF`). They're intended to show *where* the model focused, as a sanity-check aid for the doctor — not as proof of correctness. This limitation is stated in the model card and in the Model performance screen's limitations section, regardless of which method produced the heatmap below.

**Two methods, same contract.** The backend deploys on ONNX Runtime, not PyTorch, to stay under Vercel's Python function size limit (see [architecture.md](architecture.md#deployment-notes) — torch/torchvision alone are ~750 MB uncompressed, well past the 500 MB cap). ONNX Runtime gives forward passes only, no backpropagation, so Grad-CAM (which needs the gradient of the prediction with respect to the backbone's last conv layer) isn't available there. The two paths:

- **Grad-CAM** (`ml/boneage/gradcam.py`) — used when running the real PyTorch model directly (training, evaluation, and `ml/compare_heatmaps.py`'s sanity check below). Weights each channel of the target conv layer by the mean gradient of the prediction with respect to that channel, combines, ReLUs, and normalises.
- **Score-CAM** (`ml/boneage/score_cam.py`) — used by the deployed, ONNX-based backend (`ml/boneage/onnx_inference.py`). Gradient-free: it reads the same target layer's *activations* (exposed as a second output of the exported backbone graph, see `ml/boneage/onnx_export.py`) instead of their gradient, and estimates each channel's importance by actually masking the input with it and re-running the (deterministic, dropout-off) model.

  Classic Score-CAM weights each channel by how much masking with it *increases* a classification logit — that has no equivalent for a regression output like bone age (there's no single "more positive is better" direction). Instead, each of the top-`k` most active channels is weighted by how closely masking the image down to just that channel's region reproduces the **full image's** prediction:

  ```
  weight_i = softmax_i( -| f(masked_i) - f(full) | )
  ```

  where `f(full)` is the model's prediction on the whole image and `f(masked_i)` is its prediction after multiplying the image by channel `i`'s (upsampled, normalised) activation map. A channel whose region alone reproduces the full prediction gets the largest weight; a channel that barely matters gets driven toward zero by the softmax. The weighted channels are summed, ReLU'd, and renormalised — mirroring Grad-CAM's own combination step. Only the `top_k` most active channels are evaluated (`InferenceConfig.score_cam_top_k`, default 32, configurable in `ml/config/config.yaml`) rather than every channel of the target layer (512 for `resnet18`'s `layer4`), since each one costs a full extra forward pass.
- **Checking the two agree:** `ml/compare_heatmaps.py` runs both methods on the same sample images and saves them side by side, specifically so a real trained checkpoint's Grad-CAM and Score-CAM outputs can be eyeballed against each other before relying on Score-CAM in a demo — see [ml/README.md](../ml/README.md).
- **Uncertainty (MC dropout) on the ONNX path** doesn't rely on ONNX Runtime's own Dropout-in-training-mode behaviour (which can't cleanly reproduce `set_mc_dropout_mode`'s "dropout stochastic, BatchNorm frozen" split via PyTorch's exporter — see `ml/boneage/onnx_export.py`'s module docstring for the empirical reason). Instead the exported model is split into three graphs (backbone+activations, and the two head layers either side of each Dropout), and the actual Bernoulli dropout masks are applied in numpy between calling them — the same "inverted dropout" scaling `torch.nn.Dropout` uses, so it's numerically equivalent to the real model, not an approximation.

## Uncertainty approach

- **Confirmed: MC dropout.** Multiple stochastic forward passes at inference time (dropout left active), with the spread of predictions reported as the uncertainty estimate. This must run fast enough to stay inline with inference for the demo (see [architecture.md](architecture.md#deployment-notes)); number of passes `[TBD]`. On the deployed (ONNX) backend, the backbone itself (no dropout) runs once and only the two tiny head layers are rerun per stochastic pass, with the dropout masks applied in numpy — see [Explainability](#explainability) above and `ml/boneage/onnx_export.py`.
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

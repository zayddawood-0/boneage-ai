# Data

Part of the [BoneAge AI](../README.md) documentation set. See also: [model.md](model.md).

## Datasets

### 1. RSNA Pediatric Bone Age Challenge 2017 (main training set)

- **Size:** 14,236 left-hand radiographs — 12,611 train / 1,425 validation / 200 test.
- **Fields/labels:** bone age (months), sex. **Does not include chronological age.**
- **Licence:** non-commercial research/education use with attribution.
- **Links:** [Official (RSNA)](https://www.rsna.org/artificial-intelligence/ai-image-challenge/RSNA-Pediatric-Bone-Age-Challenge-2017) · [Kaggle mirror](https://www.kaggle.com/datasets/kmader/rsna-bone-age) — `kaggle datasets download -d kmader/rsna-bone-age`.
- **Role in this project:** primary training set for the CNN.

### 2. Digital Hand Atlas (USC)

- **Size:** ~1,400 hand X-rays of healthy children (Asian, African American, Caucasian, Hispanic).
- **Fields/labels:** chronological age, sex, Tanner stage, height, weight, two bone age readings.
- **Link:** [USC IPILab](https://ipilab.usc.edu/BAAweb).
- **Role in this project:** because it includes chronological age (unlike RSNA), used to evaluate the bone-age-vs-chronological-age gap logic and as an external generalisation check across its represented populations.

### 3. RHPE (Radiological Hand Pose Estimation), Universidad de los Andes

- **Size:** 6,288 hand X-rays, Colombian patients.
- **Fields/labels:** chronological age; hand bounding boxes/keypoints (also provided for RSNA images).
- **Link:** [BCV Uniandes](https://bcv-uniandes.github.io/baar-wp/).
- **Role in this project:** secondary evaluation set for the gap-flagging agent and generalisation; bounding boxes/keypoints may assist the image-quality "hand detected" check.

**Plan:** train on RSNA; evaluate the gap-flagging agent and generalisation on DHA and/or RHPE.

No other dataset figures should be used anywhere in this project beyond the three listed above — do not add or infer additional statistics.

## Splits

| Dataset | Split |
|---|---|
| RSNA | 12,611 train / 1,425 validation / 200 test (as provided by the challenge) |
| DHA | Not pre-split — used entirely as an external evaluation set. Internal train/val split, if any is needed for threshold tuning: `[TBD]`. |
| RHPE | Not pre-split for this project — used as an external evaluation set. Internal split, if needed: `[TBD]`. |

## Preprocessing

- **Resize:** target input resolution for the CNN backbone: `[TBD]` (depends on chosen architecture, e.g. EfficientNet/ResNet default input size).
- **Normalise:** pixel intensity normalisation strategy (e.g. per-image min-max vs. dataset-level mean/std): `[TBD]`.
- **Orientation:** left-hand X-rays should be in a consistent orientation (e.g. fingers up) before the model sees them; orientation correction is also surfaced to the user as an image-quality check (see [requirements.md](requirements.md#image-upload--quality)). Exact correction method (manual flag vs. automatic detection/rotation): `[TBD]`.
- **Augmentation:** candidates for training-time augmentation (e.g. small rotations, brightness/contrast jitter, slight crops) to improve robustness: `[TBD]` — to be finalised alongside the training plan in [model.md](model.md).
- **De-identification:** burned-in patient details (name, ID, DOB printed on the image) must be detected and removed/blocked before storage or model use — see [safety-and-ethics.md](safety-and-ethics.md#privacy).

## Handling chronological age (RSNA gap)

RSNA provides bone age and sex but **not** chronological age, so it cannot by itself be used to evaluate the bone-age-vs-chronological-age gap that the growth review agent flags on. Approach:

1. **Training:** RSNA is used only to train the CNN to predict bone age (image + sex → bone age), which does not require chronological age as a label.
2. **Gap evaluation:** DHA and/or RHPE — which do include chronological age — are used to evaluate how well the predicted bone age vs. actual chronological age gap behaves (e.g. does it correctly surface known delayed/advanced cases), and to sanity-check the normal-range/flagging logic described in [AGENTS.md](../AGENTS.md#the-growth-review-agent).
3. **In production use (post-hackathon placeholder):** chronological age is always computed from the real patient's date of birth and X-ray date, entered at intake (see [requirements.md](requirements.md#patient-intake)) — it is never inferred or estimated.

## Licence & attribution requirements

- **RSNA:** non-commercial research/education use, with attribution to RSNA. Do not use for any commercial purpose; include attribution in any publication, demo materials, or model card (see [model.md](model.md#model-card-template)).
- **Digital Hand Atlas (USC):** review and follow USC IPILab's stated terms of use before downloading/using; attribute per their requirements. Exact terms: `[TBD]` — confirm on the [USC IPILab site](https://ipilab.usc.edu/BAAweb) before use.
- **RHPE (Universidad de los Andes):** review and follow the terms stated on the [BCV Uniandes project page](https://bcv-uniandes.github.io/baar-wp/) before downloading/using; attribute per their requirements. Exact terms: `[TBD]`.
- General rule: no dataset here may be redistributed or used commercially without separately confirming terms; this project's use is framed as hackathon/research/education only.

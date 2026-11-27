# ml/ — BoneAge AI data pipeline + model

Phase 1 (data pipeline) and Phase 2A (model, training, evaluation, inference) — see [../docs/model.md](../docs/model.md), [../docs/data.md](../docs/data.md), [../docs/tasks.md](../docs/tasks.md). No model has actually been trained on real data yet; every metric in `docs/model.md` stays `[TBD]` until that happens for real (see "Training on Kaggle" below).

## What's here

```
ml/
├── boneage/
│   ├── config.py        # loads ml/config/config.yaml into a PipelineConfig
│   ├── seed.py           # set_seed() — reproducible splits/augmentation/training
│   ├── splits.py          # CSV loading + column-alias normalisation; generic seeded split utility
│   ├── transforms.py      # preprocessing (resize+pad, orientation, grayscale) + train-only augmentation
│   ├── datasets.py        # RSNABoneAgeDataset (PyTorch Dataset)
│   ├── dataloaders.py     # DataLoader construction
│   ├── model.py            # BoneAgeModel: CNN backbone + sex -> regression head (dropout for MC dropout)
│   ├── metrics.py          # MAE overall/by sex/by age band, % within threshold
│   ├── training.py         # train_model(): the actual training loop
│   ├── evaluation.py       # evaluate_model(): metrics + JSON/scatter-plot saving
│   ├── gradcam.py           # Grad-CAM heatmap (PyTorch path — training/evaluation)
│   ├── inference.py        # load a checkpoint, predict bone age + MC-dropout uncertainty + heatmap
│   ├── colormap.py          # shared inferno colour LUT (no matplotlib at runtime) — used by both paths below
│   ├── onnx_export.py       # exports a checkpoint to 3 ONNX graphs + metadata.json — see docstring for why 3
│   ├── onnx_inference.py    # torch-free inference via ONNX Runtime + numpy — what the deployed backend runs
│   ├── numpy_transforms.py  # torch-free preprocessing, used only by onnx_inference.py
│   ├── score_cam.py         # Score-CAM: gradient-free Grad-CAM stand-in for the ONNX path
│   └── prediction_result.py # the PredictionResult shape shared by inference.py and onnx_inference.py
├── config/
│   ├── config.example.yaml   # template — copy to config.yaml and fill in real paths
│   └── config.yaml            # (gitignored) your local dataset paths
├── notebooks/
│   └── train_kaggle.ipynb     # runs training + evaluation on Kaggle (GPU) — see below
├── tests/                 # unit tests against a small fake dataset generated on the fly
├── train.py                # CLI: python ml/train.py --config ml/config/config.yaml
├── evaluate.py              # CLI: python ml/evaluate.py --config ... --checkpoint ...
├── export_onnx.py            # CLI: python ml/export_onnx.py --config ... --checkpoint ... --out-dir ...
├── compare_heatmaps.py        # CLI: Grad-CAM vs Score-CAM side by side, for a visual sanity check
├── requirements.txt
└── pytest.ini
```

## Setup

This project does **not** download or include the RSNA dataset. Get it yourself per [../docs/data.md](../docs/data.md) (Kaggle mirror: `kaggle datasets download -d kmader/rsna-bone-age`), then:

```bash
pip install -r ml/requirements.txt
cp ml/config/config.example.yaml ml/config/config.yaml
# edit ml/config/config.yaml with your real dataset paths
```

## Running the tests

Tests never touch the real dataset or download pretrained weights — they generate a small fake set of images + CSV on the fly (see `tests/conftest.py`) and use `pretrained=False`, so they run without `config.yaml`, any downloaded data, or network access.

```bash
cd ml
pytest
```

(or `pytest ml` from the repo root)

## Training locally (CPU or GPU)

```bash
python ml/train.py --config ml/config/config.yaml
python ml/evaluate.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt
```

`train.py` reads every hyperparameter from the config (loss is fixed to L1/MAE per [docs/model.md#loss](../docs/model.md#loss); optimizer is AdamW). Mixed precision only activates when `torch.cuda.is_available()` — harmless on CPU. `evaluate.py` writes `val_results.json` / `test_results.json` and scatter plots to `config.evaluation.output_dir`.

## Training on Kaggle (GPU)

See `notebooks/train_kaggle.ipynb` — it installs the `boneage` package from an uploaded code dataset, points the config at the Kaggle-mounted `kmader/rsna-bone-age` dataset, trains on GPU, runs evaluation, and leaves the checkpoint + results under `/kaggle/working` for download. Full step-by-step instructions are in the conversation this notebook was produced in (and as markdown cells inside the notebook itself).

## Exporting to ONNX (for the deployed backend)

The backend doesn't run PyTorch — Vercel's Python Functions cap out at 500 MB uncompressed, and `torch`+`torchvision` alone measure ~750 MB (see [../docs/architecture.md#deployment-notes](../docs/architecture.md#deployment-notes)). Instead it runs the trained model via **ONNX Runtime**:

```bash
python ml/export_onnx.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --out-dir ml/checkpoints/onnx
```

Writes three ONNX graphs plus `metadata.json` into `--out-dir` (gitignored, same as the checkpoint) — see `boneage/onnx_export.py`'s module docstring for exactly why it's three graphs rather than one (short version: PyTorch's ONNX exporter can't cleanly reproduce `set_mc_dropout_mode`'s "dropout stochastic, BatchNorm frozen" split, so dropout is applied as a numpy Bernoulli mask between two exported head graphs instead — numerically equivalent to the real model, verified in `ml/tests/test_onnx_inference.py`). Upload the resulting directory as a zip somewhere reachable and point the backend's `ONNX_DOWNLOAD_URL` at it (see [backend/README.md](../backend/README.md#model-delivery-deployment)).

Before trusting it in a demo, sanity-check that Score-CAM (the gradient-free Grad-CAM stand-in this ONNX path uses, see [../docs/model.md#explainability](../docs/model.md#explainability)) actually highlights similar regions to real Grad-CAM:

```bash
python ml/compare_heatmaps.py --config ml/config/config.yaml --checkpoint ml/checkpoints/best_model.pt --onnx-dir ml/checkpoints/onnx --out-dir ml/results/heatmap_comparison --images path/to/sample1.png path/to/sample2.png
```

Omit `--images` to compare against a couple of auto-generated synthetic images instead (a quick wiring check, not a real sanity check — they're noise, not hand X-rays).

## Design notes

- Dataset location always comes from `config.yaml`, never hard-coded (see `boneage/config.py`).
- RSNA's train/validation/test pools are loaded as the three separate, officially pre-split image-dir + CSV pairs (12,611 / 1,425 / 200 — see [../docs/data.md#splits](../docs/data.md#splits)); `boneage.splits.random_split_dataframe` is a generic, seeded splitter kept for datasets that only come as a single pool (DHA/RHPE, or ad-hoc internal splits, or a Kaggle mirror that doesn't ship a separately labelled validation set).
- Grayscale handling, resize+pad, and EXIF-orientation correction happen in `boneage/transforms.py`; full automatic hand-orientation correction is out of scope here (`[TBD]`, see [../docs/data.md#preprocessing](../docs/data.md#preprocessing)).
- Training-time augmentation (small rotation/translate/zoom/brightness/contrast) is only ever added when `train=True`; **no horizontal flip is used anywhere** — every RSNA image is a left hand.
- Sex is encoded as a `(1,)` float tensor (`1.0` = male, `0.0` = female) — the extra model input per [../docs/model.md](../docs/model.md), concatenated into the regression head in `boneage/model.py`.
- **MC dropout** (`boneage.model.set_mc_dropout_mode`) puts the model in eval mode (frozen BatchNorm) but forces `Dropout` layers back into train mode, so repeated forward passes are stochastic only in the dropout — `boneage.inference.predict_single_image` runs N such passes for the point estimate + uncertainty (mean/std), per [../docs/model.md#uncertainty-approach](../docs/model.md#uncertainty-approach).
- **Grad-CAM** (`boneage/gradcam.py`) runs as a separate, single deterministic (dropout-off) pass — mixing stochastic dropout into the explainability heatmap would make it noisy and less meaningful. The deployed (ONNX) backend uses **Score-CAM** (`boneage/score_cam.py`) instead, since ONNX Runtime gives forward passes only, no gradients — see [Exporting to ONNX](#exporting-to-onnx-for-the-deployed-backend) above and [../docs/model.md#explainability](../docs/model.md#explainability) for the regression-appropriate channel-weighting formula it uses.
- Backbone choice, hyperparameters, age-band boundaries, and MC-dropout pass count are all still `[TBD]` per [../docs/model.md](../docs/model.md) — the defaults in `config.example.yaml` are reasonable starting points, not tuned values.
- No metric in [../docs/model.md](../docs/model.md) should be filled in from a toy/CPU-smoke run — only from a real trained checkpoint evaluated with `evaluate.py` (locally or via the Kaggle notebook).

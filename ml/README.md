# ml/ — BoneAge AI data pipeline

Phase 1 scope only: **data loading and preprocessing** for the RSNA Pediatric Bone Age dataset (see [../docs/data.md](../docs/data.md)). No model training or inference code lives here yet — see [../docs/tasks.md](../docs/tasks.md).

## What's here

```
ml/
├── boneage/
│   ├── config.py        # loads ml/config/config.yaml into a PipelineConfig
│   ├── seed.py           # set_seed() — reproducible splits/augmentation
│   ├── splits.py          # CSV loading + column-alias normalisation; generic seeded split utility
│   ├── transforms.py      # preprocessing (resize+pad, orientation, grayscale) + train-only augmentation
│   ├── datasets.py        # RSNABoneAgeDataset (PyTorch Dataset)
│   └── dataloaders.py     # DataLoader construction
├── config/
│   ├── config.example.yaml   # template — copy to config.yaml and fill in real paths
│   └── config.yaml            # (gitignored) your local dataset paths
├── tests/                 # unit tests against a small fake dataset generated on the fly
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

Tests never touch the real dataset — they generate a small fake set of images + CSV on the fly (see `tests/conftest.py`), so they run without `config.yaml` or any downloaded data.

```bash
cd ml
pytest
```

(or `pytest ml` from the repo root)

## Design notes

- Dataset location always comes from `config.yaml`, never hard-coded (see `boneage/config.py`).
- RSNA's train/validation/test pools are loaded as the three separate, officially pre-split image-dir + CSV pairs (12,611 / 1,425 / 200 — see [../docs/data.md#splits](../docs/data.md#splits)); `boneage.splits.random_split_dataframe` is a generic, seeded splitter kept for datasets that only come as a single pool (DHA/RHPE, or ad-hoc internal splits).
- Grayscale handling, resize+pad, and EXIF-orientation correction happen in `boneage/transforms.py`; full automatic hand-orientation correction is out of scope here (`[TBD]`, see [../docs/data.md#preprocessing](../docs/data.md#preprocessing)).
- Training-time augmentation (small rotation/translate/zoom/brightness/contrast) is only ever added when `train=True`; **no horizontal flip is used anywhere** — every RSNA image is a left hand.
- Sex is encoded as a `(1,)` float tensor (`1.0` = male, `0.0` = female) — the extra model input per [../docs/model.md](../docs/model.md).

from __future__ import annotations

import pytest

from boneage.config import load_config

CONFIG_YAML = """
seed: 7

data:
  rsna:
    train:
      images_dir: '{train_images}'
      labels_csv: '{train_csv}'
    val:
      images_dir: '{val_images}'
      labels_csv: '{val_csv}'
    test:
      images_dir: '{test_images}'
      labels_csv: '{test_csv}'
  column_aliases:
    id: ["id", "Case ID"]
    boneage: ["boneage", "Bone Age"]
    male: ["male", "Sex"]
  image_extension: ".png"

preprocessing:
  image_size: 64
  normalize_mean: [0.485, 0.456, 0.406]
  normalize_std: [0.229, 0.224, 0.225]

augmentation:
  rotation_degrees: 10
  translate_frac: 0.05
  zoom_range: [0.95, 1.05]
  brightness: 0.2
  contrast: 0.2

dataloader:
  batch_size: 4
  num_workers: 0
"""


def test_load_config_parses_all_sections(tmp_path, make_fake_split):
    train_images, train_csv, _ = make_fake_split("train", n=2)
    val_images, val_csv, _ = make_fake_split("val", n=2)
    test_images, test_csv, _ = make_fake_split("test", n=2)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        CONFIG_YAML.format(
            train_images=train_images,
            train_csv=train_csv,
            val_images=val_images,
            val_csv=val_csv,
            test_images=test_images,
            test_csv=test_csv,
        ),
        encoding="utf-8",
    )

    cfg = load_config(config_path)

    assert cfg.seed == 7
    assert cfg.data.train.images_dir == train_images
    assert cfg.data.val.labels_csv == val_csv
    assert cfg.data.image_extension == ".png"
    assert cfg.preprocessing.image_size == 64
    assert cfg.preprocessing.normalize_mean == [0.485, 0.456, 0.406]
    assert cfg.augmentation.zoom_range == (0.95, 1.05)
    assert cfg.dataloader.batch_size == 4


def test_load_config_missing_file_raises(tmp_path):
    missing_path = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_config(missing_path)

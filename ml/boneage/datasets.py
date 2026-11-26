"""PyTorch Dataset for the RSNA Pediatric Bone Age dataset."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import torch
from torch.utils.data import Dataset

from .splits import load_labels_csv


class RSNABoneAgeDataset(Dataset):
    """Returns `(image, sex, bone_age_months)` triples.

    - `image`: output of `transform` (normally a 3xHxW tensor — see
      `boneage.transforms.build_transforms`). No transform means a PIL image.
    - `sex`: shape `(1,)` float tensor — `1.0` = male, `0.0` = female. This is
      the extra model input described in docs/model.md.
    - `bone_age_months`: scalar float tensor — the regression target.
    """

    def __init__(
        self,
        labels_csv: str | Path,
        images_dir: str | Path,
        column_aliases: dict[str, list[str]],
        transform: Callable | None = None,
        image_extension: str = ".png",
    ) -> None:
        self.df = load_labels_csv(str(labels_csv), column_aliases)
        self.images_dir = Path(images_dir)
        self.transform = transform
        self.image_extension = image_extension

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> tuple[object, torch.Tensor, torch.Tensor]:
        from .transforms import load_and_orient

        row = self.df.iloc[idx]
        image_path = self.images_dir / f"{row['id']}{self.image_extension}"
        image = load_and_orient(image_path)

        if self.transform is not None:
            image = self.transform(image)

        sex = torch.tensor([float(row["male"])], dtype=torch.float32)
        bone_age_months = torch.tensor(float(row["boneage"]), dtype=torch.float32)
        return image, sex, bone_age_months

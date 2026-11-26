"""Image quality checks before inference: hand detected, orientation,
resolution, burned-in patient details — see docs/requirements.md FR-7/FR-8
and docs/data.md#preprocessing.

These are deliberately simple heuristics, not a trained detector — full
automatic hand/orientation detection is explicitly out of scope per
docs/data.md#preprocessing (`[TBD]`). They exist so the API has a real,
testable gate before spending a prediction on an unusable image, not to
claim clinical-grade image QA.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageOps

MIN_RESOLUTION_PX = 256
MAX_ASPECT_RATIO = 3.0  # width:height or height:width beyond this looks wrong for a hand X-ray
MIN_PIXEL_STD = 8.0  # near-blank/corrupted images have ~uniform pixel values
BURNED_IN_BRIGHT_THRESHOLD = 235  # near-white, where printed labels are usually burned in
BURNED_IN_CORNER_FRACTION = 0.12  # fraction of a corner region that must be "label-bright"


@dataclass
class QualityResult:
    ok: bool
    issues: list[str] = field(default_factory=list)


def run_quality_checks(image: Image.Image) -> QualityResult:
    issues: list[str] = []

    image = ImageOps.exif_transpose(image)
    grayscale = image.convert("L")
    arr = np.asarray(grayscale, dtype=np.float32)
    height, width = arr.shape

    if not _resolution_ok(width, height):
        issues.append("low_resolution")

    if not _orientation_ok(width, height):
        issues.append("unexpected_orientation")

    if not _hand_detected(arr):
        issues.append("no_hand_detected")

    if _burned_in_details_detected(arr):
        issues.append("burned_in_details_detected")

    return QualityResult(ok=not issues, issues=issues)


def _resolution_ok(width: int, height: int) -> bool:
    return width >= MIN_RESOLUTION_PX and height >= MIN_RESOLUTION_PX


def _orientation_ok(width: int, height: int) -> bool:
    longer, shorter = max(width, height), min(width, height)
    if shorter == 0:
        return False
    return (longer / shorter) <= MAX_ASPECT_RATIO


def _hand_detected(arr: np.ndarray) -> bool:
    """Heuristic stand-in for a real hand-detection model: a genuine X-ray has
    real tissue/bone contrast, so pixel values vary; a blank, corrupted, or
    solid-fill image doesn't. This cannot confirm a hand is present — it can
    only reject images with no plausible anatomy at all.
    """
    return float(np.std(arr)) >= MIN_PIXEL_STD


def _burned_in_details_detected(arr: np.ndarray) -> bool:
    """Heuristic stand-in for OCR/label detection: burned-in patient details
    are typically printed as bright text blocks in a corner of the film.
    Flags a corner if an unusually large fraction of it is near-white
    against the (normally dark) X-ray background — a real text/label
    detector is `[TBD]`, see docs/data.md#preprocessing.
    """
    height, width = arr.shape
    corner_h = max(1, height // 6)
    corner_w = max(1, width // 6)

    corners = [
        arr[:corner_h, :corner_w],
        arr[:corner_h, width - corner_w :],
        arr[height - corner_h :, :corner_w],
        arr[height - corner_h :, width - corner_w :],
    ]
    for corner in corners:
        bright_fraction = float(np.mean(corner >= BURNED_IN_BRIGHT_THRESHOLD))
        if bright_fraction >= BURNED_IN_CORNER_FRACTION:
            return True
    return False

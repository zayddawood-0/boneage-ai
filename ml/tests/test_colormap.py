"""Checks the hardcoded inferno LUT in boneage/colormap.py still matches
matplotlib's real "inferno" colormap — matplotlib is a ml/-only, training-time
dependency (see colormap.py's docstring), so this is the one place that
cross-checks the baked-in copy is faithful.
"""
from __future__ import annotations

import numpy as np

from boneage.colormap import INFERNO_LUT


def test_lut_matches_matplotlib_inferno():
    matplotlib = __import__("matplotlib")
    cmap = matplotlib.colormaps["inferno"]
    xs = np.linspace(0, 1, 256)
    expected = (np.array([cmap(x)[:3] for x in xs]) * 255).round().astype(np.uint8)

    assert INFERNO_LUT.shape == (256, 3)
    assert np.array_equal(INFERNO_LUT, expected)


def test_lut_endpoints_match_design_tokens():
    # docs/design.md#design-tokens: #3B0F70 -> ... -> #FCFDBF is the scale
    # description; the LUT's actual 0/255 endpoints are inferno's true ends.
    assert tuple(INFERNO_LUT[0]) == (0, 0, 4)
    assert tuple(INFERNO_LUT[-1]) == (252, 255, 164)

"""The two image-layer endpoints added for the frontend's independent-layer
heatmap viewer: GET /cases/{id}/image (plain X-ray) and
GET /cases/{id}/heatmap-layer (heatmap alone, transparent PNG) — see
docs/api.md and backend/app/inference_adapter.py.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def _good_quality_xray_bytes() -> bytes:
    rng = np.random.default_rng(0)
    arr = rng.integers(20, 200, size=(400, 320), dtype=np.uint8)
    image = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _create_predicted_case(client, headers) -> int:
    patient_resp = client.post(
        "/patients",
        json={"name_or_id": "Image Endpoint Patient", "sex": "male", "date_of_birth": "2016-01-01"},
        headers=headers,
    )
    patient_id = patient_resp.json()["id"]

    case_resp = client.post(
        "/cases", json={"patient_id": patient_id, "xray_date": "2026-11-26"}, headers=headers
    )
    case_id = case_resp.json()["id"]

    client.post(
        f"/cases/{case_id}/upload",
        files={"file": ("xray.png", _good_quality_xray_bytes(), "image/png")},
        headers=headers,
    )
    return case_id


def test_predict_response_includes_image_and_heatmap_layer_urls(client, auth_headers):
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)

    predict_resp = client.post(f"/cases/{case_id}/predict", headers=headers)
    body = predict_resp.json()

    assert body["image_url"] == f"/cases/{case_id}/image"
    assert body["heatmap_layer_url"] == f"/cases/{case_id}/heatmap-layer"
    assert body["prediction_source"] == "mock"  # no checkpoint in the test environment


def test_image_and_heatmap_layer_endpoints_return_same_sized_pngs(client, auth_headers):
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)
    client.post(f"/cases/{case_id}/predict", headers=headers)

    image_resp = client.get(f"/cases/{case_id}/image", headers=headers)
    layer_resp = client.get(f"/cases/{case_id}/heatmap-layer", headers=headers)

    assert image_resp.status_code == 200
    assert image_resp.headers["content-type"] == "image/png"
    assert layer_resp.status_code == 200
    assert layer_resp.headers["content-type"] == "image/png"

    image = Image.open(io.BytesIO(image_resp.content))
    layer = Image.open(io.BytesIO(layer_resp.content))

    # The two layers must line up for the frontend to composite them.
    assert image.size == layer.size
    assert image.mode == "RGB"
    assert layer.mode == "RGBA"


def test_mock_heatmap_layer_is_not_fully_transparent_or_opaque(client, auth_headers):
    # Sanity check that the mock layer actually carries visible content
    # (the amber tint + "MOCK HEATMAP" text/border), not an edge-case blank
    # PNG — most of the layer (the flat tint) should stay translucent so the
    # X-ray underneath still shows through, even though the border/text are
    # drawn at full opacity for legibility.
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)
    client.post(f"/cases/{case_id}/predict", headers=headers)

    layer_resp = client.get(f"/cases/{case_id}/heatmap-layer", headers=headers)
    layer = Image.open(io.BytesIO(layer_resp.content))
    alpha = np.asarray(layer)[:, :, 3]

    assert alpha.min() > 0  # even the flat tint is visible
    assert np.median(alpha) < 255  # most of the layer is translucent, not opaque


def test_image_and_heatmap_layer_404_before_predict(client, auth_headers):
    headers = auth_headers("radiographer")
    patient_resp = client.post(
        "/patients",
        json={"name_or_id": "No Prediction Yet", "sex": "female", "date_of_birth": "2017-01-01"},
        headers=headers,
    )
    case_id = client.post(
        "/cases",
        json={"patient_id": patient_resp.json()["id"], "xray_date": "2026-11-26"},
        headers=headers,
    ).json()["id"]

    assert client.get(f"/cases/{case_id}/image", headers=headers).status_code == 404
    assert client.get(f"/cases/{case_id}/heatmap-layer", headers=headers).status_code == 404


def test_image_and_heatmap_layer_role_access_matches_heatmap_endpoint(client, auth_headers):
    radiographer_headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, radiographer_headers)
    client.post(f"/cases/{case_id}/predict", headers=radiographer_headers)

    for headers in (radiographer_headers, auth_headers("doctor")):
        assert client.get(f"/cases/{case_id}/image", headers=headers).status_code == 200
        assert client.get(f"/cases/{case_id}/heatmap-layer", headers=headers).status_code == 200

    admin_headers = auth_headers("admin")
    assert client.get(f"/cases/{case_id}/image", headers=admin_headers).status_code == 403
    assert client.get(f"/cases/{case_id}/heatmap-layer", headers=admin_headers).status_code == 403

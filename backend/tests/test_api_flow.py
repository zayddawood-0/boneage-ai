"""End-to-end API flow: patient -> case -> upload -> predict -> agent-review
-> doctor decision -> PDF export. See docs/architecture.md#data-flow and
docs/api.md.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image


def _good_quality_xray_bytes() -> bytes:
    rng = np.random.default_rng(0)
    arr = rng.integers(20, 200, size=(400, 320), dtype=np.uint8)  # plenty of variance, no bright corners
    image = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _blank_tiny_image_bytes() -> bytes:
    image = Image.new("L", (32, 32), color=128)  # too small + no variance
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _create_patient(client, headers) -> int:
    resp = client.post(
        "/patients",
        json={"name_or_id": "Flow Test Patient", "sex": "female", "date_of_birth": "2015-05-26"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_full_flow_upload_to_decision(client, auth_headers):
    radiographer_headers = auth_headers("radiographer")
    doctor_headers = auth_headers("doctor")

    patient_id = _create_patient(client, radiographer_headers)

    create_resp = client.post(
        "/cases",
        json={"patient_id": patient_id, "xray_date": "2026-11-26"},
        headers=radiographer_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    case_body = create_resp.json()
    case_id = case_body["id"]
    assert case_body["chronological_age_months"] == 138  # 2015-05-26 -> 2026-11-26

    upload_resp = client.post(
        f"/cases/{case_id}/upload",
        files={"file": ("xray.png", _good_quality_xray_bytes(), "image/png")},
        headers=radiographer_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    assert upload_resp.json()["quality_ok"] is True
    assert upload_resp.json()["issues"] == []

    predict_resp = client.post(f"/cases/{case_id}/predict", headers=radiographer_headers)
    assert predict_resp.status_code == 200, predict_resp.text
    predict_body = predict_resp.json()
    # No trained checkpoint exists in the test environment -> must be clearly mock.
    assert predict_body["prediction_source"] == "mock"
    assert isinstance(predict_body["bone_age_months"], float)
    assert predict_body["uncertainty_months"] > 0

    heatmap_resp = client.get(f"/cases/{case_id}/heatmap", headers=radiographer_headers)
    assert heatmap_resp.status_code == 200
    assert heatmap_resp.headers["content-type"] == "image/png"

    review_resp = client.post(f"/cases/{case_id}/agent-review", headers=radiographer_headers)
    assert review_resp.status_code == 200, review_resp.text
    review_body = review_resp.json()
    assert review_body["chronological_age_months"] == 138
    assert review_body["gap_direction"] in ("within_range", "delayed", "advanced", "uncertain")
    assert review_body["flag_status"] in ("cleared", "flagged", "needs_review")
    assert review_body["doctor_note"]
    assert review_body["doctor_note_source"] == "template"  # no OPENAI_API_KEY in tests

    # Radiographer cannot record a decision (read-only review queue access).
    forbidden = client.post(
        f"/cases/{case_id}/decision",
        json={"decision": "within_expected_range", "manual_bone_age_months": None, "notes": None},
        headers=radiographer_headers,
    )
    assert forbidden.status_code == 403

    decision_resp = client.post(
        f"/cases/{case_id}/decision",
        json={
            "decision": "confirm_flag",
            "manual_bone_age_months": None,
            "notes": "Agrees with the agent's flag.",
        },
        headers=doctor_headers,
    )
    assert decision_resp.status_code == 200, decision_resp.text
    assert decision_resp.json()["ok"] is True

    detail_resp = client.get(f"/cases/{case_id}", headers=doctor_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["decision"] == "confirm_flag"
    assert detail["decision_notes"] == "Agrees with the agent's flag."
    assert detail["prediction_source"] == "mock"
    assert detail["heatmap_url"] == f"/cases/{case_id}/heatmap"

    pdf_resp = client.get(f"/cases/{case_id}/report.pdf", headers=doctor_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content[:4] == b"%PDF"


def test_bad_quality_upload_is_rejected_and_blocks_prediction(client, auth_headers):
    headers = auth_headers("radiographer")
    patient_id = _create_patient(client, headers)
    case_id = client.post(
        "/cases", json={"patient_id": patient_id, "xray_date": "2026-11-26"}, headers=headers
    ).json()["id"]

    upload_resp = client.post(
        f"/cases/{case_id}/upload",
        files={"file": ("bad.png", _blank_tiny_image_bytes(), "image/png")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["quality_ok"] is False
    assert "low_resolution" in body["issues"]
    assert "no_hand_detected" in body["issues"]
    assert body["image_id"] is None

    predict_resp = client.post(f"/cases/{case_id}/predict", headers=headers)
    assert predict_resp.status_code == 400


def test_unsupported_file_extension_rejected(client, auth_headers):
    headers = auth_headers("radiographer")
    patient_id = _create_patient(client, headers)
    case_id = client.post(
        "/cases", json={"patient_id": patient_id, "xray_date": "2026-11-26"}, headers=headers
    ).json()["id"]

    resp = client.post(
        f"/cases/{case_id}/upload",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_queue_filters_by_status_and_sex(client, auth_headers):
    headers = auth_headers("radiographer")

    # Patient/case 1: female.
    p1 = _create_patient(client, headers)
    c1 = client.post(
        "/cases", json={"patient_id": p1, "xray_date": "2026-11-26"}, headers=headers
    ).json()["id"]
    client.post(
        f"/cases/{c1}/upload",
        files={"file": ("xray.png", _good_quality_xray_bytes(), "image/png")},
        headers=headers,
    )
    client.post(f"/cases/{c1}/predict", headers=headers)
    client.post(f"/cases/{c1}/agent-review", headers=headers)

    resp = client.get("/cases?sex=female", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(c["sex"] == "female" for c in body["cases"])
    assert body["page"] == 1
    assert body["total_pages"] >= 1

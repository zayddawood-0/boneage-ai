"""Retention cleanup (app/retention.py) deletes image/heatmap files and
clears their path columns for cases past the configured retention period,
but leaves the case record and everything else about it intact. See
docs/safety-and-ethics.md#privacy and docs/tasks.md Phase 5.
"""
from __future__ import annotations

import datetime as dt
import io
from pathlib import Path

import numpy as np
from PIL import Image

from app import models
from app.retention import cleanup_expired_images
from app.settings_store import get_or_create_settings


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
        json={"name_or_id": "Retention Test Patient", "sex": "male", "date_of_birth": "2016-01-01"},
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
    client.post(f"/cases/{case_id}/predict", headers=headers)
    return case_id


def test_cleanup_removes_images_for_expired_cases_but_keeps_the_case(client, auth_headers, db_session):
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)

    case = db_session.get(models.Case, case_id)
    assert case.image_path and case.display_image_path and case.heatmap_path and case.heatmap_layer_path
    image_path = case.image_path

    settings_row = get_or_create_settings(db_session)
    now = dt.datetime.now(dt.UTC)
    case.created_at = now - dt.timedelta(days=settings_row.retention_days + 1)
    db_session.commit()

    cleaned = cleanup_expired_images(db_session, now=now)
    assert cleaned == 1

    db_session.refresh(case)
    assert case.image_path is None
    assert case.display_image_path is None
    assert case.heatmap_path is None
    assert case.heatmap_layer_path is None
    # The case record itself (prediction, flag, code) is untouched.
    assert case.bone_age_months is not None
    assert case.case_code is not None

    assert not Path(image_path).exists()


def test_cleanup_leaves_recent_cases_alone(client, auth_headers, db_session):
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)

    cleaned = cleanup_expired_images(db_session)
    assert cleaned == 0

    case = db_session.get(models.Case, case_id)
    assert case.image_path is not None


def test_cleanup_is_idempotent(client, auth_headers, db_session):
    headers = auth_headers("radiographer")
    case_id = _create_predicted_case(client, headers)

    case = db_session.get(models.Case, case_id)
    settings_row = get_or_create_settings(db_session)
    now = dt.datetime.now(dt.UTC)
    case.created_at = now - dt.timedelta(days=settings_row.retention_days + 1)
    db_session.commit()

    first = cleanup_expired_images(db_session, now=now)
    second = cleanup_expired_images(db_session, now=now)
    assert first == 1
    assert second == 0

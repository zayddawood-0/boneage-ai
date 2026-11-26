"""Role-based access control for every endpoint, per the permission matrix
in docs/requirements.md#user-roles (enforced server-side — FR-2).
"""
from __future__ import annotations

import datetime as dt

from app import models


def _seed_patient_and_case(db_session) -> tuple[models.Patient, models.Case]:
    patient = models.Patient(
        patient_code="P-9001",
        name_or_id="RBAC Test Patient",
        sex="female",
        date_of_birth=dt.date(2015, 1, 1),
        is_demo=True,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    case = models.Case(
        case_code="BA-9001",
        patient_id=patient.id,
        xray_date=dt.date(2026, 1, 1),
        is_demo=True,
        chronological_age_months=132,
        bone_age_months=120.0,
        uncertainty_months=4.0,
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return patient, case


def test_login_wrong_password_rejected(client, make_user):
    make_user("someone@test.local", "doctor", password="correct-password")
    resp = client.post(
        "/auth/login", json={"email": "someone@test.local", "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_protected_endpoint_without_token_is_401(client):
    resp = client.get("/patients")
    assert resp.status_code == 401


# ---- Patients: doctor + radiographer only ----


def test_list_patients_allowed_for_doctor_and_radiographer(client, auth_headers):
    for role in ("doctor", "radiographer"):
        resp = client.get("/patients", headers=auth_headers(role))
        assert resp.status_code == 200, (role, resp.text)


def test_list_patients_forbidden_for_admin(client, auth_headers):
    resp = client.get("/patients", headers=auth_headers("admin"))
    assert resp.status_code == 403


def test_create_patient_allowed_for_radiographer_forbidden_for_admin(client, auth_headers):
    payload = {"name_or_id": "New Patient", "sex": "male", "date_of_birth": "2018-01-01"}
    ok = client.post("/patients", json=payload, headers=auth_headers("radiographer"))
    assert ok.status_code == 201

    forbidden = client.post("/patients", json=payload, headers=auth_headers("admin"))
    assert forbidden.status_code == 403


# ---- Review queue: doctor full, radiographer read-only, admin none ----


def test_view_queue_allowed_for_doctor_and_radiographer_not_admin(client, auth_headers, db_session):
    _seed_patient_and_case(db_session)

    for role in ("doctor", "radiographer"):
        resp = client.get("/cases", headers=auth_headers(role))
        assert resp.status_code == 200, role

    resp = client.get("/cases", headers=auth_headers("admin"))
    assert resp.status_code == 403


def test_view_case_detail_allowed_for_doctor_and_radiographer_not_admin(
    client, auth_headers, db_session
):
    _, case = _seed_patient_and_case(db_session)

    for role in ("doctor", "radiographer"):
        resp = client.get(f"/cases/{case.id}", headers=auth_headers(role))
        assert resp.status_code == 200, role

    resp = client.get(f"/cases/{case.id}", headers=auth_headers("admin"))
    assert resp.status_code == 403


def test_record_decision_allowed_for_doctor_only(client, auth_headers, db_session):
    _, case = _seed_patient_and_case(db_session)
    payload = {"decision": "within_expected_range", "manual_bone_age_months": None, "notes": None}

    for role in ("radiographer", "admin"):
        resp = client.post(f"/cases/{case.id}/decision", json=payload, headers=auth_headers(role))
        assert resp.status_code == 403, role

    resp = client.post(f"/cases/{case.id}/decision", json=payload, headers=auth_headers("doctor"))
    assert resp.status_code == 200


def test_export_pdf_allowed_for_doctor_only(client, auth_headers, db_session):
    _, case = _seed_patient_and_case(db_session)

    for role in ("radiographer", "admin"):
        resp = client.get(f"/cases/{case.id}/report.pdf", headers=auth_headers(role))
        assert resp.status_code == 403, role

    resp = client.get(f"/cases/{case.id}/report.pdf", headers=auth_headers("doctor"))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_schedule_follow_up_allowed_for_doctor_only(client, auth_headers, db_session):
    _, case = _seed_patient_and_case(db_session)
    payload = {"follow_up_date": "2027-01-01"}

    resp = client.post(f"/cases/{case.id}/follow-up", json=payload, headers=auth_headers("radiographer"))
    assert resp.status_code == 403

    resp = client.post(f"/cases/{case.id}/follow-up", json=payload, headers=auth_headers("doctor"))
    assert resp.status_code == 200


# ---- New analysis: doctor + radiographer ----


def test_create_case_allowed_for_doctor_and_radiographer_not_admin(client, auth_headers, db_session):
    patient = models.Patient(
        patient_code="P-9002",
        name_or_id="Another Patient",
        sex="male",
        date_of_birth=dt.date(2016, 6, 6),
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    payload = {"patient_id": patient.id, "xray_date": "2026-11-26"}

    for role in ("doctor", "radiographer"):
        resp = client.post("/cases", json=payload, headers=auth_headers(role))
        assert resp.status_code == 201, role

    resp = client.post("/cases", json=payload, headers=auth_headers("admin"))
    assert resp.status_code == 403


# ---- Settings: admin only ----


def test_get_settings_allowed_for_admin_only(client, auth_headers):
    for role in ("doctor", "radiographer"):
        resp = client.get("/settings", headers=auth_headers(role))
        assert resp.status_code == 403, role

    resp = client.get("/settings", headers=auth_headers("admin"))
    assert resp.status_code == 200


def test_put_settings_allowed_for_admin_only(client, auth_headers):
    payload = {"threshold_months": 10.0}

    resp = client.put("/settings", json=payload, headers=auth_headers("doctor"))
    assert resp.status_code == 403

    resp = client.put("/settings", json=payload, headers=auth_headers("admin"))
    assert resp.status_code == 200


# ---- Model performance: doctor + admin only ----


def test_model_performance_allowed_for_doctor_and_admin_not_radiographer(client, auth_headers):
    for role in ("doctor", "admin"):
        resp = client.get("/model/performance", headers=auth_headers(role))
        assert resp.status_code == 200, role

    resp = client.get("/model/performance", headers=auth_headers("radiographer"))
    assert resp.status_code == 403

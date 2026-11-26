#!/usr/bin/env python
"""Seeds demo users (one per role) and 6 sample cases (BA-1037..BA-1042)
matching the mock data in design/Queue.html and design/Patients.html.

All data here is synthetic/clearly-fake demo data (docs/safety-and-ethics.md
#privacy: "use synthetic or clearly fake patient names/IDs ... never real
patient data"). Bone age values are hand-set to match the design mockups —
they are NOT model predictions (no real checkpoint exists yet), hence
`prediction_source="mock"` on every seeded case. The growth review agent's
decision (gap_direction/flag_status/doctor_note) IS computed for real, by
running the actual deterministic rules + note writer against these values.

Usage (from the repo root, after `alembic upgrade head` in backend/):
    python backend/scripts/seed_demo_data.py
Safe to re-run — existing users/patients/cases (matched by email/code) are
left alone rather than duplicated.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app import models  # noqa: E402
from app.agent.review import run_growth_review  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.settings_store import get_or_create_settings  # noqa: E402

DEMO_PASSWORD = "demo-password"

DEMO_USERS = [
    {"email": "doctor@boneage.ai", "role": "doctor", "name": "Dr. Demo"},
    {"email": "radiographer@boneage.ai", "role": "radiographer", "name": "Radiographer Demo"},
    {"email": "admin@boneage.ai", "role": "admin", "name": "Admin Demo"},
]

# Matches design/Queue.html + design/Patients.html exactly (same six cases,
# same chronological/bone ages, same flagged/normal classification — see
# AGENTS.md#example-input-output for the shape this is meant to exercise).
DEMO_CASES = [
    {
        "case_code": "BA-1042",
        "patient_code": "P-0213",
        "name": "Demo Patient A",
        "sex": "female",
        "date_of_birth": dt.date(2015, 5, 26),
        "xray_date": dt.date(2026, 11, 26),
        "bone_age_months": 110.0,  # 9y 2m
        "uncertainty_months": 4.0,
        "decision": None,  # awaiting review (flagged, delayed)
    },
    {
        "case_code": "BA-1041",
        "patient_code": "P-0212",
        "name": "Demo Patient B",
        "sex": "male",
        "date_of_birth": dt.date(2020, 11, 26),
        "xray_date": dt.date(2026, 11, 26),
        "bone_age_months": 101.0,  # 8y 5m
        "uncertainty_months": 5.0,
        "decision": None,  # awaiting review (flagged, advanced)
    },
    {
        "case_code": "BA-1040",
        "patient_code": "P-0209",
        "name": "Demo Patient C",
        "sex": "male",
        "date_of_birth": dt.date(2017, 10, 25),
        "xray_date": dt.date(2026, 11, 25),
        "bone_age_months": 118.0,  # 9y 10m
        "uncertainty_months": 3.0,
        "decision": None,  # within range -> auto-cleared
    },
    {
        "case_code": "BA-1039",
        "patient_code": "P-0207",
        "name": "Demo Patient D",
        "sex": "female",
        "date_of_birth": dt.date(2013, 11, 24),
        "xray_date": dt.date(2026, 11, 24),
        "bone_age_months": 161.0,  # 13y 5m
        "uncertainty_months": 3.0,
        "decision": "within_expected_range",  # reviewed, within range
    },
    {
        "case_code": "BA-1038",
        "patient_code": "P-0204",
        "name": "Demo Patient E",
        "sex": "female",
        "date_of_birth": dt.date(2019, 9, 24),
        "xray_date": dt.date(2026, 11, 24),
        "bone_age_months": 79.0,  # 6y 7m
        "uncertainty_months": 3.0,
        "decision": "within_expected_range",  # reviewed, within range
    },
    {
        "case_code": "BA-1037",
        "patient_code": "P-0198",
        "name": "Demo Patient F",
        "sex": "male",
        "date_of_birth": dt.date(2014, 8, 23),
        "xray_date": dt.date(2026, 11, 23),
        "bone_age_months": 116.0,  # 9y 8m
        "uncertainty_months": 4.0,
        "decision": "confirm_flag",  # reviewed and confirmed (flagged, delayed)
    },
]


def seed_users(db) -> dict[str, models.User]:
    users_by_role = {}
    for spec in DEMO_USERS:
        user = db.query(models.User).filter_by(email=spec["email"]).one_or_none()
        if user is None:
            user = models.User(
                email=spec["email"],
                hashed_password=hash_password(DEMO_PASSWORD),
                role=spec["role"],
                name=spec["name"],
            )
            db.add(user)
            db.flush()
            print(f"Created user {spec['email']} ({spec['role']})")
        else:
            print(f"User {spec['email']} already exists, leaving as-is")
        users_by_role[spec["role"]] = user
    db.commit()
    return users_by_role


def seed_cases(db, doctor_user: models.User) -> None:
    settings_row = get_or_create_settings(db)

    for spec in DEMO_CASES:
        patient = db.query(models.Patient).filter_by(patient_code=spec["patient_code"]).one_or_none()
        if patient is None:
            patient = models.Patient(
                patient_code=spec["patient_code"],
                name_or_id=spec["name"],
                sex=spec["sex"],
                date_of_birth=spec["date_of_birth"],
                is_demo=True,
            )
            db.add(patient)
            db.flush()
            print(f"Created patient {spec['patient_code']} ({spec['name']})")

        existing_case = db.query(models.Case).filter_by(case_code=spec["case_code"]).one_or_none()
        if existing_case is not None:
            print(f"Case {spec['case_code']} already exists, leaving as-is")
            continue

        review = run_growth_review(
            sex=spec["sex"],
            date_of_birth=spec["date_of_birth"],
            xray_date=spec["xray_date"],
            bone_age_months=spec["bone_age_months"],
            uncertainty_months=spec["uncertainty_months"],
            settings_row=settings_row,
        )

        case = models.Case(
            case_code=spec["case_code"],
            patient_id=patient.id,
            xray_date=spec["xray_date"],
            is_demo=True,
            quality_ok=True,
            quality_issues=[],
            bone_age_months=spec["bone_age_months"],
            uncertainty_months=spec["uncertainty_months"],
            prediction_source="mock",  # hand-set demo values, not a real model run
            chronological_age_months=review.chronological_age_months,
            gap_months=review.gap_magnitude_months,
            gap_direction=review.gap_direction,
            flag_status=review.flag_status,
            flag_reason=review.flag_reason,
            doctor_note=review.doctor_note,
            doctor_note_source=review.doctor_note_source,
        )

        if spec["decision"] is not None:
            case.decision = spec["decision"]
            case.decided_by_user_id = doctor_user.id
            case.decided_at = dt.datetime.combine(spec["xray_date"], dt.time(14, 30))

        db.add(case)
        print(
            f"Created case {spec['case_code']}: {review.gap_direction} / {review.flag_status} "
            f"(decision={spec['decision']})"
        )

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        users_by_role = seed_users(db)
        seed_cases(db, users_by_role["doctor"])
    finally:
        db.close()
    print("\nDemo login credentials (all roles share the same password):")
    for spec in DEMO_USERS:
        print(f"  {spec['email']}  /  {DEMO_PASSWORD}   ({spec['role']})")


if __name__ == "__main__":
    main()

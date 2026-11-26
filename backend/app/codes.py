"""Human-readable code generation for patients (P-0213) and cases (BA-1042),
matching the format used throughout design/ (see design/Queue.html,
design/Patients.html).
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

_CASE_PATTERN = re.compile(r"^BA-(\d+)$")
_PATIENT_PATTERN = re.compile(r"^P-(\d+)$")


def next_case_code(db: Session) -> str:
    codes = db.execute(select(models.Case.case_code)).scalars().all()
    max_n = 1000
    for code in codes:
        match = _CASE_PATTERN.match(code)
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"BA-{max_n + 1}"


def next_patient_code(db: Session) -> str:
    codes = db.execute(select(models.Patient.patient_code)).scalars().all()
    max_n = 0
    for code in codes:
        match = _PATIENT_PATTERN.match(code)
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"P-{max_n + 1:04d}"

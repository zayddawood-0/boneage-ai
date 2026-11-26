from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..codes import next_patient_code
from ..database import get_db
from ..deps import require_roles
from ..serializers import case_to_list_item

router = APIRouter(prefix="/patients", tags=["patients"])

# Permission matrix (docs/requirements.md#user-roles): doctor + radiographer only.
_ALLOWED = ("doctor", "radiographer")


@router.get("", response_model=list[schemas.PatientOut])
def list_patients(
    db: Session = Depends(get_db), _user: models.User = Depends(require_roles(*_ALLOWED))
) -> list[models.Patient]:
    return list(db.execute(select(models.Patient)).scalars().all())


@router.post("", response_model=schemas.PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: schemas.PatientCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_ALLOWED)),
) -> models.Patient:
    patient = models.Patient(
        patient_code=next_patient_code(db),
        name_or_id=payload.name_or_id,
        sex=payload.sex,
        date_of_birth=payload.date_of_birth,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=schemas.PatientDetail)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_ALLOWED)),
) -> schemas.PatientDetail:
    patient = db.get(models.Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return schemas.PatientDetail(
        id=patient.id,
        patient_code=patient.patient_code,
        name_or_id=patient.name_or_id,
        sex=patient.sex,
        date_of_birth=patient.date_of_birth,
        cases=[case_to_list_item(c) for c in patient.cases],
    )

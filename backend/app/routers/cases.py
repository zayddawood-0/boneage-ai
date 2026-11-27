from __future__ import annotations

import datetime as dt
import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import models, schemas
from ..agent.review import run_growth_review
from ..agent.tools import compute_chronological_age_months
from ..codes import next_case_code
from ..database import get_db
from ..deps import require_roles
from ..inference_adapter import InferenceAdapter
from ..pdf import build_case_report_pdf
from ..quality import run_quality_checks
from ..serializers import case_to_detail, case_to_list_item
from ..settings_store import get_or_create_settings
from ..storage import (
    heatmap_layer_url_for_case,
    heatmap_url_for_case,
    image_url_for_case,
    read_case_image_bytes,
    save_display_image,
    save_heatmap_image,
    save_heatmap_layer_image,
    save_upload_bytes,
)

router = APIRouter(prefix="/cases", tags=["cases"])

_CLINICAL_WORKFLOW = ("doctor", "radiographer")  # new analysis, view queue/case
_DOCTOR_ONLY = ("doctor",)  # decisions, PDF export, follow-up — per permission matrix

_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dcm"}


def _get_case_or_404(db: Session, case_id: int) -> models.Case:
    case = db.get(models.Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.post("", response_model=schemas.CaseCreateResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: schemas.CaseCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.CaseCreateResponse:
    patient = db.get(models.Patient, payload.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    chronological_age_months = compute_chronological_age_months(
        patient.date_of_birth, payload.xray_date
    )
    case = models.Case(
        case_code=next_case_code(db),
        patient_id=patient.id,
        xray_date=payload.xray_date,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        referral_reason=payload.referral_reason,
        chronological_age_months=chronological_age_months,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return schemas.CaseCreateResponse(
        id=case.id, case_code=case.case_code, chronological_age_months=chronological_age_months
    )


@router.get("", response_model=schemas.CaseListResponse)
def list_cases(
    status_filter: str | None = Query(default=None, alias="status"),
    sex: str | None = None,
    sort: str = "date_desc",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.CaseListResponse:
    query = select(models.Case).join(models.Patient)
    if status_filter:
        query = query.where(models.Case.flag_status == status_filter)
    if sex:
        query = query.where(models.Patient.sex == sex)
    query = query.order_by(
        models.Case.xray_date.asc() if sort == "date_asc" else models.Case.xray_date.desc()
    )

    all_cases = list(db.execute(query).scalars().all())
    total_pages = max(1, (len(all_cases) + page_size - 1) // page_size)
    page = max(1, page)
    start = (page - 1) * page_size
    page_cases = all_cases[start : start + page_size]

    return schemas.CaseListResponse(
        cases=[case_to_list_item(c) for c in page_cases], page=page, total_pages=total_pages
    )


@router.get("/{case_id}", response_model=schemas.CaseDetail)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.CaseDetail:
    case = _get_case_or_404(db, case_id)
    prior_cases = [c for c in case.patient.cases if c.id != case.id]
    return case_to_detail(case, prior_cases)


@router.post("/{case_id}/upload", response_model=schemas.UploadResponse)
async def upload_xray(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.UploadResponse:
    case = _get_case_or_404(db, case_id)

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext or '(none)'}' — accepted: PNG, JPG, DICOM.",
        )

    data = await file.read()

    if ext == ".dcm":
        # Pixel-level quality checks need real DICOM pixel decoding, out of
        # scope for this pass — the file is still accepted and stored.
        quality_ok, issues = True, []
    else:
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read image file"
            ) from exc
        result = run_quality_checks(image)
        quality_ok, issues = result.ok, result.issues

    # Blob uploads go over the network (vercel-blob's sync API) — run it off
    # the event loop rather than blocking this async endpoint (see
    # storage.py; a no-op extra hop for the local-disk backend).
    saved_handle = await run_in_threadpool(save_upload_bytes, case.id, filename, data)
    case.image_path = saved_handle
    case.quality_ok = quality_ok
    case.quality_issues = issues
    db.commit()

    return schemas.UploadResponse(
        quality_ok=quality_ok, issues=issues, image_id=Path(saved_handle).name if quality_ok else None
    )


@router.post("/{case_id}/predict", response_model=schemas.PredictResponse)
def predict_case(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.PredictResponse:
    case = _get_case_or_404(db, case_id)
    if not case.image_path or not case.quality_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case has no quality-passing uploaded image yet.",
        )

    adapter = InferenceAdapter()
    sex_is_male = case.patient.sex == "male"

    # The ml/ inference functions take a real file path on disk (see
    # ml/boneage/onnx_inference.py / inference.py) — for the local storage
    # backend `case.image_path` already is one, but for Vercel Blob it's a
    # pathname, not a local file, so the stored bytes are fetched and
    # written to a throwaway temp file either way (a harmless extra hop for
    # the local-disk backend, see storage.py).
    image_bytes = read_case_image_bytes(case.image_path)
    if image_bytes is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image not found")

    suffix = Path(case.image_path).suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = Path(tmp.name)
    try:
        result = adapter.predict(tmp_path, sex_is_male)
    finally:
        tmp_path.unlink(missing_ok=True)

    heatmap_handle = save_heatmap_image(case.id, result.heatmap_image)
    display_handle = save_display_image(case.id, result.plain_image)
    heatmap_layer_handle = save_heatmap_layer_image(case.id, result.heatmap_layer)

    case.bone_age_months = result.bone_age_months
    case.uncertainty_months = result.uncertainty_months
    case.heatmap_path = heatmap_handle
    case.display_image_path = display_handle
    case.heatmap_layer_path = heatmap_layer_handle
    case.prediction_source = result.source
    db.commit()

    return schemas.PredictResponse(
        bone_age_months=result.bone_age_months,
        uncertainty_months=result.uncertainty_months,
        heatmap_url=heatmap_url_for_case(case.id),
        image_url=image_url_for_case(case.id),
        heatmap_layer_url=heatmap_layer_url_for_case(case.id),
        prediction_source=result.source,
    )


@router.get("/{case_id}/heatmap")
def get_heatmap(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> Response:
    """Pre-blended X-ray + heatmap, flattened into one image — used by the
    PDF report. The frontend's interactive viewer uses the two separate
    layers below instead, so it can control opacity and show the plain
    X-ray alone."""
    case = _get_case_or_404(db, case_id)
    data = read_case_image_bytes(case.heatmap_path)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No heatmap for this case")
    return Response(content=data, media_type="image/png")


@router.get("/{case_id}/image")
def get_display_image(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> Response:
    """The plain preprocessed X-ray alone (no heatmap) — always the real
    uploaded image, resized/oriented the same way the model saw it, even
    when the prediction itself is mocked (see inference_adapter.py)."""
    case = _get_case_or_404(db, case_id)
    data = read_case_image_bytes(case.display_image_path)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No image for this case")
    return Response(content=data, media_type="image/png")


@router.get("/{case_id}/heatmap-layer")
def get_heatmap_layer(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> Response:
    """The Grad-CAM heatmap alone, as a transparent PNG the same size as
    /image, for the frontend to composite independently (opacity slider,
    side-by-side view). Real attention when prediction_source is "real";
    a clearly-labelled fake layer when it's "mock" — see inference_adapter.py."""
    case = _get_case_or_404(db, case_id)
    data = read_case_image_bytes(case.heatmap_layer_path)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No heatmap layer for this case")
    return Response(content=data, media_type="image/png")


@router.post("/{case_id}/agent-review", response_model=schemas.AgentReviewResponse)
def agent_review_case(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_CLINICAL_WORKFLOW)),
) -> schemas.AgentReviewResponse:
    case = _get_case_or_404(db, case_id)
    if case.bone_age_months is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Case has no prediction yet."
        )

    settings_row = get_or_create_settings(db)
    result = run_growth_review(
        sex=case.patient.sex,
        date_of_birth=case.patient.date_of_birth,
        xray_date=case.xray_date,
        bone_age_months=case.bone_age_months,
        uncertainty_months=case.uncertainty_months,
        settings_row=settings_row,
    )

    case.chronological_age_months = result.chronological_age_months
    case.gap_months = result.gap_magnitude_months
    case.gap_direction = result.gap_direction
    case.flag_status = result.flag_status
    case.flag_reason = result.flag_reason
    case.doctor_note = result.doctor_note
    case.doctor_note_source = result.doctor_note_source
    db.commit()

    return schemas.AgentReviewResponse(
        chronological_age_months=result.chronological_age_months,
        gap_direction=result.gap_direction,
        gap_magnitude_months=result.gap_magnitude_months,
        flag_status=result.flag_status,
        flag_reason=result.flag_reason,
        doctor_note=result.doctor_note,
        doctor_note_source=result.doctor_note_source,
    )


@router.post("/{case_id}/decision", response_model=schemas.DecisionResponse)
def record_decision(
    case_id: int,
    payload: schemas.DecisionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(*_DOCTOR_ONLY)),
) -> schemas.DecisionResponse:
    case = _get_case_or_404(db, case_id)

    case.decision = payload.decision
    case.manual_bone_age_months = payload.manual_bone_age_months
    case.decision_notes = payload.notes
    case.decided_by_user_id = current_user.id
    case.decided_at = dt.datetime.now(dt.UTC)
    db.commit()

    return schemas.DecisionResponse(
        ok=True, decided_at=case.decided_at, decided_by=current_user.id
    )


@router.get("/{case_id}/report.pdf")
def export_report(
    case_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_DOCTOR_ONLY)),
) -> Response:
    case = _get_case_or_404(db, case_id)
    decided_by_name = None
    if case.decided_by_user_id:
        decider = db.get(models.User, case.decided_by_user_id)
        decided_by_name = decider.name if decider else None

    pdf_bytes = build_case_report_pdf(case, decided_by_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{case.case_code}_report.pdf"'},
    )


@router.post("/{case_id}/follow-up", response_model=schemas.OkResponse)
def schedule_follow_up(
    case_id: int,
    payload: schemas.FollowUpRequest,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_roles(*_DOCTOR_ONLY)),
) -> schemas.OkResponse:
    case = _get_case_or_404(db, case_id)
    case.follow_up_date = payload.follow_up_date
    db.commit()
    return schemas.OkResponse(ok=True)

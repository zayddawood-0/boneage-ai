"""ORM -> Pydantic response shaping, shared across routers."""
from __future__ import annotations

from . import models, schemas
from .storage import heatmap_layer_url_for_case, heatmap_url_for_case, image_url_for_case


def case_to_list_item(case: models.Case) -> schemas.CaseListItem:
    return schemas.CaseListItem(
        id=case.id,
        case_code=case.case_code,
        patient_name_or_id=case.patient.name_or_id,
        sex=case.patient.sex,
        chronological_age_months=case.chronological_age_months,
        bone_age_months=case.bone_age_months,
        gap_months=case.gap_months,
        flag_status=case.flag_status,
        gap_direction=case.gap_direction,
        decision=case.decision,
        xray_date=case.xray_date,
    )


def case_to_detail(case: models.Case, prior_cases: list[models.Case]) -> schemas.CaseDetail:
    heatmap_url = heatmap_url_for_case(case.id) if case.heatmap_path else None
    image_url = image_url_for_case(case.id) if case.display_image_path else None
    heatmap_layer_url = heatmap_layer_url_for_case(case.id) if case.heatmap_layer_path else None
    return schemas.CaseDetail(
        id=case.id,
        case_code=case.case_code,
        patient=schemas.PatientOut.model_validate(case.patient),
        xray_date=case.xray_date,
        height_cm=case.height_cm,
        weight_kg=case.weight_kg,
        referral_reason=case.referral_reason,
        is_demo=case.is_demo,
        quality_ok=case.quality_ok,
        quality_issues=case.quality_issues,
        bone_age_months=case.bone_age_months,
        uncertainty_months=case.uncertainty_months,
        heatmap_url=heatmap_url,
        image_url=image_url,
        heatmap_layer_url=heatmap_layer_url,
        prediction_source=case.prediction_source,
        chronological_age_months=case.chronological_age_months,
        gap_months=case.gap_months,
        gap_direction=case.gap_direction,
        flag_status=case.flag_status,
        flag_reason=case.flag_reason,
        doctor_note=case.doctor_note,
        doctor_note_source=case.doctor_note_source,
        decision=case.decision,
        manual_bone_age_months=case.manual_bone_age_months,
        decision_notes=case.decision_notes,
        decided_by_user_id=case.decided_by_user_id,
        decided_at=case.decided_at,
        follow_up_date=case.follow_up_date,
        prior_cases=[case_to_list_item(c) for c in prior_cases],
    )

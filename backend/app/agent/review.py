"""Orchestrates one growth review: deterministic decision + (optional) LLM note.

See AGENTS.md#decision-rules for the spec this implements.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .. import models
from ..config import get_settings
from .note_writer import write_doctor_note
from .reference_table import ReferenceTable
from .tools import GrowthReviewRuleSettings, compare_gap, compute_chronological_age_months, get_normal_range


@dataclass(frozen=True)
class GrowthReviewResult:
    chronological_age_months: int
    gap_direction: str
    gap_magnitude_months: float
    flag_status: str
    flag_reason: str | None
    doctor_note: str | None
    doctor_note_source: str | None


def _rule_settings_from_model(settings_row: models.GrowthReviewSettings) -> GrowthReviewRuleSettings:
    return GrowthReviewRuleSettings(
        rule_type=settings_row.rule_type,
        threshold_sd=settings_row.threshold_sd,
        threshold_months=settings_row.threshold_months,
        flag_advanced=settings_row.flag_advanced,
        flag_uncertain_enabled=settings_row.flag_uncertain_enabled,
        uncertainty_threshold_months=settings_row.uncertainty_threshold_months,
        auto_clear_enabled=settings_row.auto_clear_enabled,
    )


def _load_reference_table(settings_row: models.GrowthReviewSettings) -> ReferenceTable | None:
    if settings_row.rule_type != "sd":
        return None
    app_settings = get_settings()
    return ReferenceTable.load(app_settings.reference_table_path)


def run_growth_review(
    *,
    sex: str,
    date_of_birth: dt.date,
    xray_date: dt.date,
    bone_age_months: float,
    uncertainty_months: float | None,
    settings_row: models.GrowthReviewSettings,
) -> GrowthReviewResult:
    """Runs the full deterministic decision, then (if enabled) writes a note.

    Only this function's own locals end up in the LLM payload — never the
    Case/Patient ORM objects, so there's no way for an image path or name to
    leak into `write_doctor_note` by accident.
    """
    rule_settings = _rule_settings_from_model(settings_row)
    reference_table = _load_reference_table(settings_row)

    chronological_age_months = compute_chronological_age_months(date_of_birth, xray_date)
    normal_range = get_normal_range(sex, chronological_age_months, rule_settings, reference_table)
    gap_result = compare_gap(
        bone_age_months, chronological_age_months, uncertainty_months, normal_range, rule_settings
    )

    doctor_note: str | None = None
    doctor_note_source: str | None = None

    if settings_row.write_note_enabled:
        payload = {
            "sex": sex,
            "chronological_age_months": chronological_age_months,
            "bone_age_months": bone_age_months,
            "gap_months": gap_result.gap_magnitude_months,
            "gap_direction": gap_result.gap_direction,
            "normal_range_basis": normal_range.basis,
            "flag_status": gap_result.flag_status,
            "flag_reason": gap_result.flag_reason,
            "uncertainty_months": uncertainty_months,
        }
        doctor_note, doctor_note_source = write_doctor_note(payload)

    return GrowthReviewResult(
        chronological_age_months=chronological_age_months,
        gap_direction=gap_result.gap_direction,
        gap_magnitude_months=gap_result.gap_magnitude_months,
        flag_status=gap_result.flag_status,
        flag_reason=gap_result.flag_reason,
        doctor_note=doctor_note,
        doctor_note_source=doctor_note_source,
    )

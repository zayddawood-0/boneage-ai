"""Deterministic growth review agent tools — see AGENTS.md#the-growth-review-agent.

The flag decision lives entirely in this plain Python, never in the LLM
(AGENTS.md guardrail: "Never diagnose" / "Auditability"). The LLM is only
ever used downstream, in note_writer.py, to phrase an explanation of a
decision already made here.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .reference_table import ReferenceTable


def compute_chronological_age_months(date_of_birth: dt.date, xray_date: dt.date) -> int:
    """Whole months between two dates, per docs/requirements.md FR-4."""
    months = (xray_date.year - date_of_birth.year) * 12 + (xray_date.month - date_of_birth.month)
    if xray_date.day < date_of_birth.day:
        months -= 1
    return max(months, 0)


@dataclass(frozen=True)
class NormalRange:
    lower_bone_age_months: float
    upper_bone_age_months: float
    basis: str
    resolved: bool  # False => could not be determined (e.g. empty SD reference table)


@dataclass(frozen=True)
class GrowthReviewRuleSettings:
    """The subset of GrowthReviewSettings (models.py) the rules need."""

    rule_type: str  # "sd" | "fixed_months"
    threshold_sd: float
    threshold_months: float
    flag_advanced: bool
    flag_uncertain_enabled: bool
    uncertainty_threshold_months: float
    auto_clear_enabled: bool


def get_normal_range(
    sex: str,
    chronological_age_months: int,
    settings: GrowthReviewRuleSettings,
    reference_table: ReferenceTable | None,
) -> NormalRange:
    """Looks up the acceptable bone-age range for this sex/age, from settings
    — never a value hard-coded in code (AGENTS.md guardrail).
    """
    if settings.rule_type == "fixed_months":
        return NormalRange(
            lower_bone_age_months=chronological_age_months - settings.threshold_months,
            upper_bone_age_months=chronological_age_months + settings.threshold_months,
            basis=f"fixed ±{settings.threshold_months:g} months around chronological age",
            resolved=True,
        )

    if settings.rule_type == "sd":
        entry = reference_table.lookup(sex, chronological_age_months) if reference_table else None
        if entry is None:
            return NormalRange(
                lower_bone_age_months=0.0,
                upper_bone_age_months=0.0,
                basis=(
                    "SD-based reference table has no entry for this sex/age "
                    "(table is an empty [TBD] template — see "
                    "backend/data/reference_tables)"
                ),
                resolved=False,
            )
        lower = entry.mean_bone_age_months - settings.threshold_sd * entry.sd_months
        upper = entry.mean_bone_age_months + settings.threshold_sd * entry.sd_months
        return NormalRange(
            lower_bone_age_months=lower,
            upper_bone_age_months=upper,
            basis=f"±{settings.threshold_sd:g} SD around the reference mean for this sex/age",
            resolved=True,
        )

    raise ValueError(f"Unknown rule_type: {settings.rule_type!r}")


@dataclass(frozen=True)
class GapResult:
    gap_direction: str  # within_range | delayed | advanced | uncertain
    gap_magnitude_months: float
    flag_status: str  # cleared | flagged | needs_review
    flag_reason: str | None


def compare_gap(
    bone_age_months: float,
    chronological_age_months: int,
    uncertainty_months: float | None,
    normal_range: NormalRange,
    settings: GrowthReviewRuleSettings,
) -> GapResult:
    """Rule-based comparison — the one place the flag decision is actually made.

    Order of checks, each documented because it's a real design choice:
    1. An unresolved normal range (e.g. empty SD table) means the system
       cannot classify delayed/advanced/normal at all — flag for review
       rather than guess, regardless of the uncertainty toggle below.
    2. High MC-dropout uncertainty, if that check is enabled, also means
       "don't trust this gap enough to auto-decide" — flag for review.
    3. Otherwise, compare bone age against the resolved range. An "advanced"
       result is only actually flagged if `flag_advanced` is enabled;
       otherwise it's reported but treated as cleared.
    """
    gap_magnitude_months = bone_age_months - chronological_age_months

    if not normal_range.resolved:
        return GapResult(
            gap_direction="uncertain",
            gap_magnitude_months=gap_magnitude_months,
            flag_status="needs_review",
            flag_reason="normal_range_unresolved",
        )

    if (
        settings.flag_uncertain_enabled
        and uncertainty_months is not None
        and uncertainty_months > settings.uncertainty_threshold_months
    ):
        return GapResult(
            gap_direction="uncertain",
            gap_magnitude_months=gap_magnitude_months,
            flag_status="needs_review",
            flag_reason="high_model_uncertainty",
        )

    if normal_range.lower_bone_age_months <= bone_age_months <= normal_range.upper_bone_age_months:
        return GapResult(
            gap_direction="within_range",
            gap_magnitude_months=gap_magnitude_months,
            flag_status="cleared",
            flag_reason=None,
        )

    if bone_age_months < normal_range.lower_bone_age_months:
        return GapResult(
            gap_direction="delayed",
            gap_magnitude_months=gap_magnitude_months,
            flag_status="flagged",
            flag_reason="delayed_outside_range",
        )

    # Advanced.
    if settings.flag_advanced:
        return GapResult(
            gap_direction="advanced",
            gap_magnitude_months=gap_magnitude_months,
            flag_status="flagged",
            flag_reason="advanced_outside_range",
        )
    return GapResult(
        gap_direction="advanced",
        gap_magnitude_months=gap_magnitude_months,
        flag_status="cleared",
        flag_reason="advanced_but_flag_advanced_disabled",
    )

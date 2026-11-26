"""Unit tests for the deterministic growth review rules (backend/app/agent/tools.py).

See AGENTS.md#decision-rules. These test pure functions directly — no DB,
no API, no LLM — because the flag decision must be deterministic and
auditable on its own.
"""
from __future__ import annotations

from app.agent.reference_table import ReferenceEntry, ReferenceTable
from app.agent.tools import GrowthReviewRuleSettings, compare_gap, compute_chronological_age_months, get_normal_range
import datetime as dt


def _fixed_months_settings(**overrides) -> GrowthReviewRuleSettings:
    defaults = dict(
        rule_type="fixed_months",
        threshold_sd=2.0,
        threshold_months=12.0,
        flag_advanced=True,
        flag_uncertain_enabled=True,
        uncertainty_threshold_months=18.0,
        auto_clear_enabled=True,
    )
    defaults.update(overrides)
    return GrowthReviewRuleSettings(**defaults)


# ---- compute_chronological_age_months ----


def test_compute_chronological_age_exact_months():
    assert compute_chronological_age_months(dt.date(2015, 5, 26), dt.date(2026, 11, 26)) == 138


def test_compute_chronological_age_day_not_yet_reached():
    # Same month/year math, but xray day is before birth day -> one month less.
    assert compute_chronological_age_months(dt.date(2015, 5, 27), dt.date(2026, 11, 26)) == 137


def test_compute_chronological_age_leap_year_safe():
    assert compute_chronological_age_months(dt.date(2016, 2, 29), dt.date(2017, 2, 28)) == 11


# ---- get_normal_range: fixed_months ----


def test_fixed_months_range_is_symmetric_around_chronological_age():
    settings = _fixed_months_settings(threshold_months=12.0)
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    assert normal_range.resolved is True
    assert normal_range.lower_bone_age_months == 108.0
    assert normal_range.upper_bone_age_months == 132.0


def test_fixed_months_range_identical_for_both_sexes():
    settings = _fixed_months_settings(threshold_months=12.0)
    male_range = get_normal_range("male", 120, settings, reference_table=None)
    female_range = get_normal_range("female", 120, settings, reference_table=None)

    assert male_range.lower_bone_age_months == female_range.lower_bone_age_months
    assert male_range.upper_bone_age_months == female_range.upper_bone_age_months


# ---- compare_gap: boundary cases, fixed_months rule ----


def test_boundary_exactly_at_lower_edge_is_within_range():
    settings = _fixed_months_settings(threshold_months=12.0)
    normal_range = get_normal_range("female", 120, settings, reference_table=None)

    result = compare_gap(108.0, 120, 3.0, normal_range, settings)

    assert result.gap_direction == "within_range"
    assert result.flag_status == "cleared"


def test_boundary_just_below_lower_edge_is_delayed():
    settings = _fixed_months_settings(threshold_months=12.0)
    normal_range = get_normal_range("female", 120, settings, reference_table=None)

    result = compare_gap(107.9, 120, 3.0, normal_range, settings)

    assert result.gap_direction == "delayed"
    assert result.flag_status == "flagged"
    assert result.flag_reason == "delayed_outside_range"


def test_boundary_exactly_at_upper_edge_is_within_range():
    settings = _fixed_months_settings(threshold_months=12.0)
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    result = compare_gap(132.0, 120, 3.0, normal_range, settings)

    assert result.gap_direction == "within_range"
    assert result.flag_status == "cleared"


def test_boundary_just_above_upper_edge_is_advanced():
    settings = _fixed_months_settings(threshold_months=12.0)
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    result = compare_gap(132.1, 120, 3.0, normal_range, settings)

    assert result.gap_direction == "advanced"
    assert result.flag_status == "flagged"
    assert result.flag_reason == "advanced_outside_range"


def test_delayed_both_sexes_agree_under_fixed_months_rule():
    settings = _fixed_months_settings(threshold_months=12.0)
    for sex in ("male", "female"):
        normal_range = get_normal_range(sex, 120, settings, reference_table=None)
        result = compare_gap(90.0, 120, 3.0, normal_range, settings)
        assert result.gap_direction == "delayed", sex
        assert result.flag_status == "flagged", sex


def test_advanced_both_sexes_agree_under_fixed_months_rule():
    settings = _fixed_months_settings(threshold_months=12.0)
    for sex in ("male", "female"):
        normal_range = get_normal_range(sex, 120, settings, reference_table=None)
        result = compare_gap(150.0, 120, 3.0, normal_range, settings)
        assert result.gap_direction == "advanced", sex
        assert result.flag_status == "flagged", sex


def test_advanced_not_flagged_when_flag_advanced_disabled():
    settings = _fixed_months_settings(threshold_months=12.0, flag_advanced=False)
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    result = compare_gap(150.0, 120, 3.0, normal_range, settings)

    assert result.gap_direction == "advanced"  # still reported
    assert result.flag_status == "cleared"  # but not flagged
    assert result.flag_reason == "advanced_but_flag_advanced_disabled"


# ---- compare_gap: uncertainty boundary ----


def test_uncertainty_exactly_at_threshold_does_not_trigger_uncertain():
    settings = _fixed_months_settings(threshold_months=12.0, uncertainty_threshold_months=18.0)
    normal_range = get_normal_range("female", 120, settings, reference_table=None)

    result = compare_gap(120.0, 120, 18.0, normal_range, settings)

    assert result.gap_direction == "within_range"


def test_uncertainty_just_above_threshold_triggers_uncertain():
    settings = _fixed_months_settings(threshold_months=12.0, uncertainty_threshold_months=18.0)
    normal_range = get_normal_range("female", 120, settings, reference_table=None)

    result = compare_gap(120.0, 120, 18.01, normal_range, settings)

    assert result.gap_direction == "uncertain"
    assert result.flag_status == "needs_review"
    assert result.flag_reason == "high_model_uncertainty"


def test_uncertain_overrides_what_would_otherwise_be_within_range():
    settings = _fixed_months_settings(threshold_months=12.0, uncertainty_threshold_months=5.0)
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    # bone_age=120 is dead-center within range, but uncertainty is too wide to trust it.
    result = compare_gap(120.0, 120, 24.0, normal_range, settings)

    assert result.gap_direction == "uncertain"
    assert result.flag_status == "needs_review"


def test_flag_uncertain_disabled_ignores_high_uncertainty():
    settings = _fixed_months_settings(
        threshold_months=12.0, uncertainty_threshold_months=5.0, flag_uncertain_enabled=False
    )
    normal_range = get_normal_range("male", 120, settings, reference_table=None)

    result = compare_gap(120.0, 120, 999.0, normal_range, settings)

    assert result.gap_direction == "within_range"
    assert result.flag_status == "cleared"


# ---- SD-based rule type ----


def test_sd_rule_with_empty_reference_table_is_uncertain_regardless_of_toggle():
    empty_table = ReferenceTable({"male": [], "female": []}, source_path=None)
    for flag_uncertain_enabled in (True, False):
        settings = GrowthReviewRuleSettings(
            rule_type="sd",
            threshold_sd=2.0,
            threshold_months=12.0,
            flag_advanced=True,
            flag_uncertain_enabled=flag_uncertain_enabled,
            uncertainty_threshold_months=18.0,
            auto_clear_enabled=True,
        )
        normal_range = get_normal_range("female", 120, settings, reference_table=empty_table)
        assert normal_range.resolved is False

        result = compare_gap(130.0, 120, 3.0, normal_range, settings)
        assert result.gap_direction == "uncertain"
        assert result.flag_status == "needs_review"
        assert result.flag_reason == "normal_range_unresolved"


def test_sd_rule_with_populated_table_computes_mean_plus_minus_k_sd():
    table = ReferenceTable(
        {
            "female": [
                ReferenceEntry(
                    age_months_min=108, age_months_max=132, mean_bone_age_months=120.0, sd_months=6.0
                )
            ],
            "male": [],
        },
        source_path=None,
    )
    settings = GrowthReviewRuleSettings(
        rule_type="sd",
        threshold_sd=2.0,
        threshold_months=12.0,
        flag_advanced=True,
        flag_uncertain_enabled=True,
        uncertainty_threshold_months=18.0,
        auto_clear_enabled=True,
    )

    normal_range = get_normal_range("female", 120, settings, reference_table=table)

    assert normal_range.resolved is True
    assert normal_range.lower_bone_age_months == 108.0  # 120 - 2*6
    assert normal_range.upper_bone_age_months == 132.0  # 120 + 2*6

    delayed = compare_gap(100.0, 120, 3.0, normal_range, settings)
    assert delayed.gap_direction == "delayed"

    advanced = compare_gap(140.0, 120, 3.0, normal_range, settings)
    assert advanced.gap_direction == "advanced"

    within = compare_gap(120.0, 120, 3.0, normal_range, settings)
    assert within.gap_direction == "within_range"


def test_sd_rule_no_matching_age_band_is_uncertain():
    table = ReferenceTable(
        {
            "male": [
                ReferenceEntry(
                    age_months_min=0, age_months_max=60, mean_bone_age_months=30.0, sd_months=5.0
                )
            ],
            "female": [],
        },
        source_path=None,
    )
    settings = GrowthReviewRuleSettings(
        rule_type="sd",
        threshold_sd=2.0,
        threshold_months=12.0,
        flag_advanced=True,
        flag_uncertain_enabled=True,
        uncertainty_threshold_months=18.0,
        auto_clear_enabled=True,
    )

    # age 120 is outside the only band defined (0-60) for male.
    normal_range = get_normal_range("male", 120, settings, reference_table=table)
    assert normal_range.resolved is False

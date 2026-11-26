"""The privacy rule: no image or patient name/ID ever reaches the LLM call.

See AGENTS.md#guardrails ("Data minimisation in the LLM call") and
docs/safety-and-ethics.md#privacy.
"""
from __future__ import annotations

import datetime as dt

from app import models
from app.agent import note_writer
from app.agent.review import run_growth_review

ALLOWED_PAYLOAD_KEYS = {
    "sex",
    "chronological_age_months",
    "bone_age_months",
    "gap_months",
    "gap_direction",
    "normal_range_basis",
    "flag_status",
    "flag_reason",
    "uncertainty_months",
}

FORBIDDEN_SUBSTRINGS_IN_KEYS = ("name", "image", "path", "patient", "case", "id", "code")


def _default_settings_row() -> models.GrowthReviewSettings:
    return models.GrowthReviewSettings(
        id=1,
        rule_type="fixed_months",
        threshold_sd=2.0,
        threshold_months=12.0,
        reference_table_name=None,
        flag_advanced=True,
        flag_uncertain_enabled=True,
        uncertainty_threshold_months=18.0,
        auto_clear_enabled=True,
        write_note_enabled=True,
        retention_days=30,
        theme="light",
        age_unit="years_months",
    )


def test_llm_payload_contains_only_allowed_structured_fields(monkeypatch):
    captured_payloads = []

    def fake_llm_note(payload: dict) -> str:
        captured_payloads.append(payload)
        return "A fake LLM-authored note."

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(note_writer, "_llm_note", fake_llm_note)

    run_growth_review(
        sex="female",
        date_of_birth=dt.date(2015, 5, 26),
        xray_date=dt.date(2026, 11, 26),
        bone_age_months=110.0,
        uncertainty_months=4.0,
        settings_row=_default_settings_row(),
    )

    assert len(captured_payloads) == 1
    payload = captured_payloads[0]

    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS

    for key in payload.keys():
        lowered = key.lower()
        for forbidden in FORBIDDEN_SUBSTRINGS_IN_KEYS:
            assert forbidden not in lowered, f"payload key {key!r} looks identifying"


def test_llm_payload_never_contains_an_image_or_name_value(monkeypatch):
    captured_payloads = []

    def fake_llm_note(payload: dict) -> str:
        captured_payloads.append(payload)
        return "note"

    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(note_writer, "_llm_note", fake_llm_note)

    run_growth_review(
        sex="male",
        date_of_birth=dt.date(2014, 8, 23),
        xray_date=dt.date(2026, 11, 23),
        bone_age_months=116.0,
        uncertainty_months=4.0,
        settings_row=_default_settings_row(),
    )

    payload = captured_payloads[0]
    serialised_values = " ".join(str(v) for v in payload.values())

    # No path separators or image-file extensions should ever appear in the
    # values sent to the LLM.
    for marker in ("/", "\\", ".png", ".jpg", ".jpeg", ".dcm"):
        assert marker not in serialised_values


def test_no_api_key_falls_back_to_template_without_calling_llm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    called = {"n": 0}

    def fail_if_called(payload: dict) -> str:
        called["n"] += 1
        raise AssertionError("LLM should not be called when OPENAI_API_KEY is unset")

    monkeypatch.setattr(note_writer, "_llm_note", fail_if_called)

    result = run_growth_review(
        sex="female",
        date_of_birth=dt.date(2013, 11, 24),
        xray_date=dt.date(2026, 11, 24),
        bone_age_months=161.0,
        uncertainty_months=3.0,
        settings_row=_default_settings_row(),
    )

    assert called["n"] == 0
    assert result.doctor_note_source == "template"
    assert result.doctor_note is not None


def test_llm_failure_falls_back_to_template_note(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-test")

    def boom(payload: dict) -> str:
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr(note_writer, "_llm_note", boom)

    result = run_growth_review(
        sex="male",
        date_of_birth=dt.date(2020, 11, 26),
        xray_date=dt.date(2026, 11, 26),
        bone_age_months=101.0,
        uncertainty_months=5.0,
        settings_row=_default_settings_row(),
    )

    assert result.doctor_note_source == "template"
    assert result.doctor_note is not None


def test_every_note_ends_with_the_disclaimer(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    for direction_inputs in (
        dict(bone_age_months=110.0, uncertainty_months=4.0),  # delayed
        dict(bone_age_months=101.0, uncertainty_months=5.0),  # advanced (6y0m chron)
        dict(bone_age_months=120.0, uncertainty_months=3.0),  # within range
    ):
        result = run_growth_review(
            sex="female",
            date_of_birth=dt.date(2016, 11, 26),
            xray_date=dt.date(2026, 11, 26),
            settings_row=_default_settings_row(),
            **direction_inputs,
        )
        assert result.doctor_note is not None
        assert note_writer.DISCLAIMER in result.doctor_note


def test_write_note_disabled_skips_note_entirely():
    settings_row = _default_settings_row()
    settings_row.write_note_enabled = False

    result = run_growth_review(
        sex="male",
        date_of_birth=dt.date(2014, 8, 23),
        xray_date=dt.date(2026, 11, 23),
        bone_age_months=116.0,
        uncertainty_months=4.0,
        settings_row=settings_row,
    )

    assert result.doctor_note is None
    assert result.doctor_note_source is None

"""Pydantic request/response schemas. Shapes follow docs/api.md where it
gives one; docs/api.md itself says its shapes are "illustrative, not final",
so fields are extended here where the richer Settings/agent behaviour needs it.
"""
from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["doctor", "radiographer", "admin"]
Sex = Literal["male", "female"]
Decision = Literal["confirm_flag", "within_expected_range", "model_looks_wrong"]
FlagStatus = Literal["cleared", "flagged", "needs_review"]
GapDirection = Literal["within_range", "delayed", "advanced", "uncertain"]
RuleType = Literal["sd", "fixed_months"]
PredictionSource = Literal["real", "mock"]
NoteSource = Literal["llm", "template"]


class OkResponse(BaseModel):
    ok: bool = True


# ---- Auth ----
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    role: Role


# ---- Patients ----
class PatientCreate(BaseModel):
    name_or_id: str
    sex: Sex
    date_of_birth: dt.date


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_code: str
    name_or_id: str
    sex: Sex
    date_of_birth: dt.date


class PatientDetail(PatientOut):
    cases: list["CaseListItem"]


# ---- Cases ----
class CaseCreate(BaseModel):
    patient_id: int
    xray_date: dt.date
    height_cm: float | None = None
    weight_kg: float | None = None
    referral_reason: str | None = None


class CaseCreateResponse(BaseModel):
    id: int
    case_code: str
    chronological_age_months: int


class CaseListItem(BaseModel):
    id: int
    case_code: str
    patient_name_or_id: str
    sex: Sex
    chronological_age_months: int | None
    bone_age_months: float | None
    gap_months: float | None
    flag_status: FlagStatus | None
    gap_direction: GapDirection | None
    decision: Decision | None
    xray_date: dt.date


class CaseListResponse(BaseModel):
    cases: list[CaseListItem]
    page: int
    total_pages: int


class UploadResponse(BaseModel):
    quality_ok: bool
    issues: list[str] = Field(default_factory=list)
    image_id: str | None = None


class PredictResponse(BaseModel):
    bone_age_months: float
    uncertainty_months: float
    heatmap_url: str
    prediction_source: PredictionSource


class AgentReviewResponse(BaseModel):
    chronological_age_months: int
    gap_direction: GapDirection
    gap_magnitude_months: float
    flag_status: FlagStatus
    flag_reason: str | None
    doctor_note: str | None
    doctor_note_source: NoteSource | None


class DecisionRequest(BaseModel):
    decision: Decision
    manual_bone_age_months: float | None = None
    notes: str | None = None


class DecisionResponse(BaseModel):
    ok: bool
    decided_at: dt.datetime
    decided_by: int


class FollowUpRequest(BaseModel):
    follow_up_date: dt.date


class CaseDetail(BaseModel):
    id: int
    case_code: str
    patient: PatientOut
    xray_date: dt.date
    height_cm: float | None
    weight_kg: float | None
    referral_reason: str | None
    is_demo: bool

    quality_ok: bool | None
    quality_issues: list[str] | None

    bone_age_months: float | None
    uncertainty_months: float | None
    heatmap_url: str | None
    prediction_source: PredictionSource | None

    chronological_age_months: int | None
    gap_months: float | None
    gap_direction: GapDirection | None
    flag_status: FlagStatus | None
    flag_reason: str | None
    doctor_note: str | None
    doctor_note_source: NoteSource | None

    decision: Decision | None
    manual_bone_age_months: float | None
    decision_notes: str | None
    decided_by_user_id: int | None
    decided_at: dt.datetime | None

    follow_up_date: dt.date | None
    prior_cases: list[CaseListItem] = Field(default_factory=list)


# ---- Settings ----
class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_type: RuleType
    threshold_sd: float
    threshold_months: float
    reference_table_name: str | None
    flag_advanced: bool
    flag_uncertain_enabled: bool
    uncertainty_threshold_months: float
    auto_clear_enabled: bool
    write_note_enabled: bool
    retention_days: int
    theme: str
    age_unit: str


class SettingsUpdate(BaseModel):
    rule_type: RuleType | None = None
    threshold_sd: float | None = None
    threshold_months: float | None = None
    reference_table_name: str | None = None
    flag_advanced: bool | None = None
    flag_uncertain_enabled: bool | None = None
    uncertainty_threshold_months: float | None = None
    auto_clear_enabled: bool | None = None
    write_note_enabled: bool | None = None
    retention_days: int | None = None
    theme: str | None = None
    age_unit: str | None = None


# ---- Model performance ----
class ModelPerformanceResponse(BaseModel):
    mae_overall_months: float | str
    mae_by_sex: dict
    mae_by_age_band: dict
    pct_within_12_months: float | str
    model_card: dict

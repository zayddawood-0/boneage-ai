"""SQLAlchemy ORM models. See docs/architecture.md#system-components and
docs/api.md for the shapes these back. Migrations live in backend/migrations/
(Alembic) — see backend/README.md for how to run them.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))  # doctor | radiographer | admin
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. P-0213
    name_or_id: Mapped[str] = mapped_column(String(255))
    sex: Mapped[str] = mapped_column(String(10))  # male | female
    date_of_birth: Mapped[dt.date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))

    cases: Mapped[list["Case"]] = relationship(back_populates="patient")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. BA-1042
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    xray_date: Mapped[dt.date] = mapped_column(Date)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    referral_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    # Upload / image quality (docs/requirements.md#image-upload--quality)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quality_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quality_issues: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Prediction (ml/boneage/inference.py, or the mock fallback — see prediction_source)
    bone_age_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    heatmap_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    prediction_source: Mapped[str | None] = mapped_column(String(10), nullable=True)  # real | mock

    # Growth review agent (AGENTS.md#the-growth-review-agent)
    chronological_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gap_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    gap_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flag_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    flag_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    doctor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    doctor_note_source: Mapped[str | None] = mapped_column(String(20), nullable=True)  # llm | template

    # Doctor decision (docs/requirements.md FR-21/FR-22)
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    manual_bone_age_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    follow_up_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))

    patient: Mapped["Patient"] = relationship(back_populates="cases")


class GrowthReviewSettings(Base):
    """Singleton row (id=1) — admin-configurable flagging rules and agent behaviour.

    See docs/requirements.md#settings and the Settings screen in design/Settings.html.
    No clinical value here is a hard-coded fact — all of this is configuration,
    with safe hackathon defaults (see docs/model.md and AGENTS.md).
    """

    __tablename__ = "growth_review_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20), default="fixed_months")  # sd | fixed_months
    threshold_sd: Mapped[float] = mapped_column(Float, default=2.0)
    threshold_months: Mapped[float] = mapped_column(Float, default=12.0)
    reference_table_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flag_advanced: Mapped[bool] = mapped_column(Boolean, default=True)
    flag_uncertain_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    uncertainty_threshold_months: Mapped[float] = mapped_column(Float, default=18.0)
    auto_clear_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    write_note_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    theme: Mapped[str] = mapped_column(String(10), default="light")
    age_unit: Mapped[str] = mapped_column(String(20), default="years_months")

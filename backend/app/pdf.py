"""Case report PDF export — docs/api.md `GET /cases/{id}/report.pdf`.

A plain, text-first report (X-ray/heatmap image embedded if available) —
styling parity with the design/ mockups is a frontend concern (docs/design.md);
this PDF only needs to carry the same facts.
"""
from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from . import models
from .storage import read_case_image_bytes

DISCLAIMER = (
    "BoneAge AI is decision support only. It does not diagnose any medical "
    "condition. This report is intended to assist a qualified clinician, who "
    "makes the final call."
)


def build_case_report_pdf(case: models.Case, decided_by_name: str | None) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    def line(text: str, size: int = 11, gap: int = 16, bold: bool = False) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(margin, y, text)
        y -= gap

    line(f"BoneAge AI — Case report {case.case_code}", size=16, gap=24, bold=True)
    line(f"Patient: {case.patient.name_or_id}  ({case.patient.patient_code})")
    line(f"Sex: {case.patient.sex}   X-ray date: {case.xray_date.isoformat()}")
    y -= 8

    line("Measurements", size=13, bold=True)
    line(f"Predicted bone age: {_fmt(case.bone_age_months)} months")
    line(f"Chronological age: {_fmt(case.chronological_age_months)} months")
    line(f"Gap (bone − chronological): {_fmt(case.gap_months)} months")
    line(f"Model uncertainty: ±{_fmt(case.uncertainty_months)} months")
    line(f"Prediction source: {case.prediction_source or '[unknown]'}")
    y -= 8

    line("Growth review agent", size=13, bold=True)
    line(f"Direction: {case.gap_direction or '[pending]'}")
    line(f"Status: {case.flag_status or '[pending]'}")
    if case.doctor_note:
        y -= 4
        c.setFont("Helvetica", 10)
        for wrapped in _wrap(case.doctor_note, 95):
            c.drawString(margin, y, wrapped)
            y -= 13
    y -= 8

    line("Doctor's decision", size=13, bold=True)
    line(f"Decision: {case.decision or '[not yet recorded]'}")
    if case.manual_bone_age_months is not None:
        line(f"Manual bone age reading: {case.manual_bone_age_months} months")
    if decided_by_name:
        line(f"Decided by: {decided_by_name}")
    if case.decision_notes:
        y -= 4
        c.setFont("Helvetica", 10)
        for wrapped in _wrap(case.decision_notes, 95):
            c.drawString(margin, y, wrapped)
            y -= 13

    heatmap_bytes = read_case_image_bytes(case.heatmap_path)
    if heatmap_bytes:
        try:
            c.drawImage(
                ImageReader(io.BytesIO(heatmap_bytes)), margin, margin, width=60 * mm, height=60 * mm
            )
        except Exception:
            pass

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(margin, margin / 2, DISCLAIMER)

    c.showPage()
    c.save()
    return buffer.getvalue()


def _fmt(value: float | int | None) -> str:
    return "[pending]" if value is None else f"{value:g}"


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines

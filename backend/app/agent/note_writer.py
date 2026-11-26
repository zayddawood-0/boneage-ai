"""The one LLM-authored step of the growth review agent: turning an already
-decided rule-based result into a short doctor-facing note.

Privacy (AGENTS.md guardrail, docs/safety-and-ethics.md#privacy): the payload
passed in here must contain ONLY structured numbers and labels — sex, ages,
gap, threshold description, flag status/reason, uncertainty — and nothing
that identifies the patient or the image. Callers (review.py) are
responsible for building that minimal payload; this module never reaches
back into a Case/Patient record itself.

If `OPENAI_API_KEY` isn't set, or the LLM call fails for any reason, this
falls back to a fixed template note built from the same payload — the flag
decision itself was already made in tools.py either way, so a missing LLM
never blocks or changes the clinical outcome, only the wording.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is decision support only, not a diagnosis — the treating clinician "
    "must confirm using full clinical judgement."
)

AGENT_INSTRUCTIONS = """You write short, plain-language notes for a doctor reviewing a
bone age case for BoneAge AI, a decision-support tool — never a diagnostic tool.

You will receive a JSON object with: sex, chronological_age_months, bone_age_months,
gap_months, gap_direction (within_range | delayed | advanced | uncertain),
normal_range_basis, flag_status, flag_reason, uncertainty_months.

Write 2-4 short sentences that:
- State the direction and magnitude of the gap (or why it's uncertain).
- If delayed or advanced, name 1-2 possible causes the doctor may consider
  (e.g. constitutional delay, hypothyroidism, growth hormone deficiency for
  delayed; early puberty for advanced) — phrased strictly as possibilities
  to check, never as a diagnosis or clinical conclusion.
- Never claim a diagnosis, never state a definitive condition, never
  contradict or override the flag_status/gap_direction you were given.

Do not invent facts beyond what's in the JSON. Output plain text only, no markdown."""


def _llm_note(payload: dict) -> str:
    """Isolated so tests can monkeypatch it without any network access."""
    from agents import Agent, Runner

    agent = Agent(name="GrowthReviewNoteWriter", instructions=AGENT_INSTRUCTIONS)
    result = Runner.run_sync(agent, input=json.dumps(payload))
    text = result.final_output
    return str(text).strip()


def _fallback_template_note(payload: dict) -> str:
    direction = payload["gap_direction"]

    if direction == "uncertain":
        if payload.get("flag_reason") == "normal_range_unresolved":
            body = (
                "The configured normal-range reference table has no matching entry for this "
                "patient's sex and age, so the system cannot classify this case as within "
                "range, delayed, or advanced."
            )
        else:
            uncertainty = payload.get("uncertainty_months")
            body = (
                f"The model's uncertainty for this prediction (±{uncertainty:g} months) is wider "
                "than the configured limit, so the gap estimate is not reliable enough to "
                "classify automatically."
            )
        return f"{body} Please review this case manually. {DISCLAIMER}"

    if direction == "within_range":
        basis = payload.get("normal_range_basis", "the configured normal range")
        return (
            f"Predicted bone age is within the configured normal range for this patient's sex "
            f"and age ({basis}). {DISCLAIMER}"
        )

    gap_months = abs(payload.get("gap_months", 0))
    uncertainty = payload.get("uncertainty_months", 0)
    basis = payload.get("normal_range_basis", "the configured normal range")
    possible_causes = (
        "constitutional delay of growth, hypothyroidism, or growth hormone deficiency"
        if direction == "delayed"
        else "early puberty or other causes of advanced skeletal maturation"
    )
    return (
        f"Predicted bone age is {direction} relative to chronological age by "
        f"{gap_months:.0f} months, outside the configured normal range ({basis}) for this "
        f"patient's sex and age. Possible causes the doctor may consider include "
        f"{possible_causes}. Model uncertainty for this case is ±{uncertainty:.0f} months. "
        f"{DISCLAIMER}"
    )


def write_doctor_note(payload: dict) -> tuple[str, str]:
    """Returns (note_text, source) where source is "llm" or "template".

    `payload` must contain only the structured fields documented in the
    module docstring — never an image, patient name, or case/patient ID.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback_template_note(payload), "template"

    try:
        note = _llm_note(payload)
        if DISCLAIMER not in note:
            note = f"{note} {DISCLAIMER}"
        return note, "llm"
    except Exception:
        logger.warning(
            "Growth review agent LLM note-writing failed; using the fallback template note.",
            exc_info=True,
        )
        return _fallback_template_note(payload), "template"

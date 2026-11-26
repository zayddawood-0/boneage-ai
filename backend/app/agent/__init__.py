"""The growth review agent — see AGENTS.md#the-growth-review-agent.

`tools.py` is the deterministic, auditable flag decision. `note_writer.py`
is the one LLM-authored step (with a template fallback). `review.py` wires
the two together. `reference_table.py` loads the SD-based reference data
(an empty [TBD] template by default).
"""

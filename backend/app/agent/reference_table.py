"""Loads the SD-based reference table used by the "sd" rule type.

The shipped table (backend/data/reference_tables/greulich_pyle_sd_reference.json)
is an intentionally empty `[TBD — to verify]` template — see that file's
`_meta` block. `lookup()` returning `None` for every call is therefore the
*expected* state until a team member populates it with verified data; the
growth review agent (`backend/app/agent/review.py`) treats a missing entry
as "cannot determine," not as "normal."
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceEntry:
    age_months_min: int
    age_months_max: int
    mean_bone_age_months: float
    sd_months: float


class ReferenceTable:
    def __init__(self, entries_by_sex: dict[str, list[ReferenceEntry]], source_path: Path) -> None:
        self._entries_by_sex = entries_by_sex
        self.source_path = source_path

    @classmethod
    def load(cls, path: str | Path) -> "ReferenceTable":
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        entries_by_sex: dict[str, list[ReferenceEntry]] = {}
        for sex in ("male", "female"):
            entries_by_sex[sex] = [
                ReferenceEntry(
                    age_months_min=e["age_months_min"],
                    age_months_max=e["age_months_max"],
                    mean_bone_age_months=e["mean_bone_age_months"],
                    sd_months=e["sd_months"],
                )
                for e in raw.get(sex, [])
            ]
        return cls(entries_by_sex, source_path=path)

    def lookup(self, sex: str, chronological_age_months: int) -> ReferenceEntry | None:
        for entry in self._entries_by_sex.get(sex, []):
            if entry.age_months_min <= chronological_age_months < entry.age_months_max:
                return entry
        return None

    @property
    def is_empty(self) -> bool:
        return all(len(entries) == 0 for entries in self._entries_by_sex.values())

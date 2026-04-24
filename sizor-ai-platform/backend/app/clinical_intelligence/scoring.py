"""Scoring helpers for clinical intelligence.

Phase 2 keeps the categorical 0-10 -> 0-4 mapping used across the
platform. The previous score_domain + ScoreResult dataclass were
deleted in this move — they had zero production callers and are
being replaced by score_patient_domain + DomainClassification (keyed
to Pydantic models in clinical_intelligence.models) as part of the
later Phase 2 scoring refactor.
"""
from __future__ import annotations


def score_0_10_to_0_4(val: float | int | None) -> int | None:
    """Categorical mapping from 0-10 generic score to 0-4 domain score.

    Replaces ``round(val * 0.4)``. Linear scaling drops raw=1 to 0 ("none"),
    erasing a mild-symptom signal; categorical preserves it. None -> None
    (silent domain). Non-numeric / out-of-range inputs are clamped after
    a float coerce; unparseable inputs return None.

    Mapping: 0 -> 0 | 1-3 -> 1 | 4-6 -> 2 | 7-8 -> 3 | 9-10 -> 4
    """
    if val is None:
        return None
    try:
        v = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    v = max(0, min(10, v))
    if v == 0:
        return 0
    if v <= 3:
        return 1
    if v <= 6:
        return 2
    if v <= 8:
        return 3
    return 4

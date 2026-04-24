"""Phase 4 coverage-enforcement helpers.

Build-time filtering of the Phase 3 Required Questions and Red Flag
Probes registries for a given (opcs_code, call_day). Phase 4 does NOT
make clinical judgements about the content — it consumes the Phase 3
manifests verbatim. See PHASE_4_PLAN.md §Constants for the one
CLINICAL_REVIEW_NEEDED constant (the 80% coverage threshold).
"""
from __future__ import annotations

import logging

from .models import RedFlagProbe, RequiredQuestion
from .pathways import RED_FLAG_PROBES, REQUIRED_QUESTIONS


logger = logging.getLogger(__name__)


def build_required_questions(
    opcs_code: str | None, call_day: int,
) -> list[RequiredQuestion]:
    """Filter the Phase 3 Required Questions manifest for a specific
    pathway + day. Returns only questions whose day_ranges include the
    given call_day.

    Day-band match: any (start, end) tuple in q.day_ranges where
    start <= call_day <= end.

    Returns [] for unknown opcs_code, for the Z03_MH scaffold, or when
    no questions match the day-band (valid in late calls past the
    manifest's day coverage).
    """
    if opcs_code is None:
        return []
    questions = REQUIRED_QUESTIONS.get(opcs_code)
    if questions is None:
        logger.warning(
            "build_required_questions: unknown opcs_code=%r, returning []",
            opcs_code,
        )
        return []
    return [
        q for q in questions
        if any(start <= call_day <= end for (start, end) in q.day_ranges)
    ]


def build_red_flag_probes(opcs_code: str | None) -> list[RedFlagProbe]:
    """Return all Red Flag Probes for the pathway. Red flags have no
    day-band filter — they apply on every call regardless of day.

    Returns [] for unknown opcs_code or the Z03_MH scaffold. Order
    matches insertion order of the per-pathway RED_FLAG_PROBES dict
    (Python 3.7+ guarantees dict order).
    """
    if opcs_code is None:
        return []
    probes = RED_FLAG_PROBES.get(opcs_code)
    if probes is None:
        logger.warning(
            "build_red_flag_probes: unknown opcs_code=%r, returning []",
            opcs_code,
        )
        return []
    return list(probes.values())

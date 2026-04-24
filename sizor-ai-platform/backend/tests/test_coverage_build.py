"""Phase 4 D2+D3 — build_required_questions / build_red_flag_probes.

Verifies the helpers filter the Phase 3 manifest correctly across all
14 active pathways and the Z03_MH scaffold at day-band boundaries.
"""
from __future__ import annotations

import pytest

from app.clinical_intelligence.coverage import (
    build_red_flag_probes,
    build_required_questions,
)
from app.clinical_intelligence.pathways import PATHWAYS, REQUIRED_QUESTIONS, RED_FLAG_PROBES


ACTIVE_PATHWAYS = [
    opcs for opcs in sorted(PATHWAYS.keys()) if opcs != "Z03_MH"
]


# ─── Required Questions ────────────────────────────────────────────────

@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_required_questions_day_1_subset(opcs: str):
    """Day 1 returns a non-empty subset of the pathway manifest for
    every active pathway. Day 1 is always covered — every pathway has
    early-call RQs."""
    all_qs = REQUIRED_QUESTIONS[opcs]
    day1 = build_required_questions(opcs, 1)
    assert 0 < len(day1) <= len(all_qs), (
        f"{opcs} day 1: got {len(day1)} RQs (total manifest: {len(all_qs)})"
    )
    # Every returned question must have a day-range covering day 1.
    for q in day1:
        assert any(s <= 1 <= e for (s, e) in q.day_ranges)


@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_required_questions_mid_window(opcs: str):
    """Day 7 should return a subset — many pathways have 4-7 band RQs."""
    day7 = build_required_questions(opcs, 7)
    for q in day7:
        assert any(s <= 7 <= e for (s, e) in q.day_ranges)


def test_required_questions_z03_mh_empty():
    """Z03_MH scaffold has no required questions."""
    assert build_required_questions("Z03_MH", 1) == []
    assert build_required_questions("Z03_MH", 30) == []


def test_required_questions_unknown_opcs():
    """Unknown opcs logs a warning and returns []."""
    assert build_required_questions("BOGUS", 1) == []


def test_required_questions_none_opcs():
    """None opcs returns [] without hitting the registry."""
    assert build_required_questions(None, 1) == []


def test_required_questions_day_outside_manifest():
    """Calling at a day past the manifest's coverage returns [] without
    error. W37 monitoring window is 60 days; day 120 has no matches."""
    # W37 manifest max day is 60 (per call_days = [1, 3, 7, 14, 21, 28, 42, 60]).
    day120 = build_required_questions("W37", 120)
    assert day120 == []


# ─── Red Flag Probes ───────────────────────────────────────────────────

@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_red_flag_probes_match_registry(opcs: str):
    """build_red_flag_probes returns all probes in the pathway registry,
    in the same order. Red flags have no day-band filter."""
    probes = build_red_flag_probes(opcs)
    registry = RED_FLAG_PROBES[opcs]
    assert len(probes) == len(registry)
    assert [p.flag_code for p in probes] == list(registry.keys())


def test_red_flag_probes_z03_mh_empty():
    """Z03_MH scaffold has no red flag probes."""
    assert build_red_flag_probes("Z03_MH") == []


def test_red_flag_probes_unknown_opcs():
    """Unknown opcs returns []."""
    assert build_red_flag_probes("BOGUS") == []


def test_red_flag_probes_none_opcs():
    """None opcs returns []."""
    assert build_red_flag_probes(None) == []


# ─── Aggregate sanity ──────────────────────────────────────────────────

def test_total_active_rq_count_matches_phase_3():
    """Phase 3 close-of-commit totals: 107 RQs across 14 active pathways.
    This test anchors the coverage builder to that manifest state."""
    total = sum(len(REQUIRED_QUESTIONS[opcs]) for opcs in ACTIVE_PATHWAYS)
    assert total == 107, f"Expected 107 RQs across active pathways, got {total}"


def test_total_active_rfp_count_matches_phase_3():
    """Phase 3 close-of-commit totals: 167 RFPs across 14 active pathways."""
    total = sum(len(RED_FLAG_PROBES[opcs]) for opcs in ACTIVE_PATHWAYS)
    assert total == 167, f"Expected 167 RFPs across active pathways, got {total}"

"""
Tests for the scoring engine. Run with: pytest tests/ -v

Scenarios covered:
  1. Stable patient stays stable (no wild swings)
  2. Missed medication bumps but doesn't explode (the 23→82 test)
  3. Red flag forces RED regardless of scores
  4. Trajectory drift accumulates over multiple calls
  5. Compound pathway-specific red flag fires
  6. Expected curve interpolation works
  7. First call (no history) is handled
"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.scoring_v2 import (
    CallExtraction,
    DomainObservation,
    PatientHistory,
    RedFlag,
    RedFlagType,
    RiskBand,
    score_call,
    load_config,
)
from app.scoring_v2.models import AdherenceStatus, SocialFactors


CONFIG_PATH = Path(__file__).parent.parent / "app" / "scoring_v2" / "config" / "pathways.yaml"


@pytest.fixture
def config():
    return load_config(CONFIG_PATH)


def make_extraction(
    *,
    pathway: str = "post_cardiac_surgery",
    day: int = 5,
    domain_scores: dict[str, int] | None = None,
    red_flags: list[RedFlag] | None = None,
    meds_taken: bool = True,
    critical_med: bool = False,
    missed_doses: int = 0,
    missed_prev_call: bool = False,
    lives_alone: bool = False,
    call_id: str = "call_1",
) -> CallExtraction:
    """Test helper — build a CallExtraction with sensible defaults."""
    default_scores = {"pain": 1, "breathlessness": 1, "wound": 0,
                      "chest_symptoms": 0, "mood": 1, "adherence": 0}
    scores = {**default_scores, **(domain_scores or {})}
    return CallExtraction(
        patient_id="P001",
        call_id=call_id,
        call_timestamp=datetime(2026, 4, 22, 10, 0),
        pathway=pathway,
        day_post_discharge=day,
        domain_observations=[
            DomainObservation(domain=d, raw_score=s, evidence_quote="test", confidence=0.9)
            for d, s in scores.items()
        ],
        red_flags=red_flags or [],
        adherence=AdherenceStatus(
            medication_taken_as_prescribed=meds_taken,
            missed_doses_reported=missed_doses,
            critical_medication=critical_med,
        ),
        social=SocialFactors(
            lives_alone=lives_alone,
            has_support_contact=not lives_alone,
            missed_previous_call=missed_prev_call,
        ),
        extraction_model="test",
        extraction_schema_version="1.0",
    )


# --- Scenario 1: Stable patient ---

def test_stable_patient_is_green(config):
    ext = make_extraction()
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=20.0, prior_call_count=3)
    result = score_call(ext, hist, config)
    assert result.band == RiskBand.GREEN
    assert result.final_score < 40
    assert not result.breakdown.red_flag_override


# --- Scenario 2: THE KEY TEST — missed meds shouldn't explode the score ---

def test_missed_meds_on_stable_patient_does_not_jump_to_red(config):
    """The 23→82 scenario. Missed dose should nudge proportionally, not detonate.

    Test design: score the SAME patient state with vs without missed meds.
    The delta should be meaningful but small, and absolute score stays sub-RED.
    """
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=23.0, prior_call_count=4)

    baseline = score_call(make_extraction(), hist, config)
    with_missed = score_call(
        make_extraction(meds_taken=False, missed_doses=1, critical_med=False),
        hist, config,
    )

    delta = with_missed.final_score - baseline.final_score
    # Nudge, not detonation — the whole point of this architecture
    assert 3 < delta < 15, f"Delta of {delta:.1f} — should be a modest bump"
    assert with_missed.band in (RiskBand.GREEN, RiskBand.AMBER)
    assert with_missed.final_score < 70, "Missed dose alone must not produce RED"
    assert "adherence_lapse" in with_missed.breakdown.modifier_detail


def test_missed_critical_meds_moves_more_but_still_proportional(config):
    """Critical med (anticoagulant) missed: bigger bump than non-critical, but still not RED alone."""
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=23.0, prior_call_count=4)

    non_critical = score_call(
        make_extraction(meds_taken=False, missed_doses=2, critical_med=False),
        hist, config,
    )
    critical = score_call(
        make_extraction(meds_taken=False, missed_doses=2, critical_med=True),
        hist, config,
    )

    assert critical.final_score > non_critical.final_score
    assert critical.final_score < 70  # still not RED from adherence alone
    assert critical.breakdown.modifier_detail["adherence_lapse"] > 10


# --- Scenario 3: Red flag override ---

def test_red_flag_forces_red_regardless_of_scores(config):
    ext = make_extraction(
        domain_scores={"pain": 0, "breathlessness": 0},  # otherwise fine
        red_flags=[RedFlag(type=RedFlagType.CHEST_PAIN, evidence_quote="crushing chest pain")],
    )
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=15.0, prior_call_count=2)
    result = score_call(ext, hist, config)
    assert result.band == RiskBand.RED
    assert result.final_score == 100
    assert result.breakdown.red_flag_override
    assert result.next_call_interval_hours == 0


# --- Scenario 4: Trajectory accumulates over calls ---

def test_trajectory_accumulates_across_worsening_calls(config):
    """Three successive calls with mildly worsening symptoms — score should climb."""
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=None, prior_call_count=0)

    # Day 3, mildly elevated
    ext1 = make_extraction(day=3, domain_scores={"breathlessness": 2, "pain": 2}, call_id="c1")
    r1 = score_call(ext1, hist, config)

    # Day 5, worse
    hist2 = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                           prior_smoothed_state=r1.breakdown.smoothed_state,
                           prior_call_count=1)
    ext2 = make_extraction(day=5, domain_scores={"breathlessness": 3, "pain": 2}, call_id="c2")
    r2 = score_call(ext2, hist2, config)

    # Day 7, worse still
    hist3 = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                           prior_smoothed_state=r2.breakdown.smoothed_state,
                           prior_call_count=2)
    ext3 = make_extraction(day=7, domain_scores={"breathlessness": 3, "pain": 3}, call_id="c3")
    r3 = score_call(ext3, hist3, config)

    # Scores should monotonically increase
    assert r1.final_score < r2.final_score < r3.final_score
    # Trajectory component should grow
    assert r1.breakdown.trajectory_score <= r2.breakdown.trajectory_score <= r3.breakdown.trajectory_score


# --- Scenario 5: Compound pathway red flag ---

def test_compound_pathway_red_flag_fires(config):
    """Post-cardiac: wound ≥3 AND pain ≥3 is a defined red combination."""
    ext = make_extraction(domain_scores={"wound": 3, "pain": 3})
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=20.0, prior_call_count=3)
    result = score_call(ext, hist, config)
    assert result.band == RiskBand.RED
    assert RedFlagType.PATHWAY_SPECIFIC in result.breakdown.red_flags_triggered


# --- Scenario 6: Expected curve interpolation ---

def test_expected_score_interpolates_between_curve_points(config):
    from app.scoring_v2.config import expected_score_at_day
    pathway = config.pathways["post_cardiac_surgery"]
    # Day 0 = 55, Day 3 = 45 → Day 1 should be ~51.67
    interp = expected_score_at_day(pathway, 1)
    assert 51 < interp < 53


# --- Scenario 7: First call with no history ---

def test_first_call_no_history_handled(config):
    ext = make_extraction()
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=None, prior_call_count=0)
    result = score_call(ext, hist, config)
    # On first call, EWMA seeds to current state → trajectory is current - expected
    assert result.breakdown.smoothed_state == result.breakdown.state_score


# --- Audit: every score carries full breakdown ---

def test_audit_trail_is_complete(config):
    ext = make_extraction(meds_taken=False, missed_doses=1)
    hist = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                          prior_smoothed_state=25.0, prior_call_count=5)
    result = score_call(ext, hist, config)
    # All fields needed to reconstruct the calculation
    b = result.breakdown
    assert b.rubric_version
    assert b.scoring_engine_version
    assert b.w_state == 0.6
    assert b.w_trajectory == 0.4
    assert b.ewma_lambda == 0.3
    assert b.modifier_detail  # shows WHICH modifiers fired

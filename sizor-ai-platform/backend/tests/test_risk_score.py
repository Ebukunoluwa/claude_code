"""
Tests for the real 0-100 risk score.

These are the scenarios that matter for correcting the fake-hash problem:
  - Two patients with identical clinical state get identical scores
  - Worse clinical state always produces a higher score (monotonicity)
  - Score band agrees with flag band in normal cases
  - Safety floors fire when they should
  - Every component is in the breakdown (defensibility)
"""
from app.clinical_intelligence.smoothing import smooth_extraction, SmoothedScores
from app.clinical.risk_score import (
    compute_risk_score,
    breakdown_to_dict,
    RED_FLAG_MIN_FLOOR,
    ACUTE_SYMPTOM_FLOOR,
    W_WORST_SYMPTOM, W_MOOD, W_FTP, W_MODIFIERS, W_DAY_FACTOR,
)


def _smoothed(pain=None, breathlessness=None, mobility=None, appetite=None,
              mood=None, modifier_total=0.0, modifier_detail=None):
    return SmoothedScores(
        pain=pain, breathlessness=breathlessness, mobility=mobility,
        appetite=appetite, mood=mood, max_smoothed=max(
            (v for v in (pain, breathlessness, mobility, appetite) if v is not None),
            default=0.0
        ),
        modifier_total=modifier_total,
        modifier_detail=modifier_detail or {},
        lam=0.3,
    )


# --- The fundamental fix: deterministic, clinical-data-driven ---

def test_two_patients_with_identical_state_get_identical_scores():
    """The core bug fix: no more UUID-based jitter."""
    state = _smoothed(pain=5, breathlessness=4, mobility=3, appetite=4, mood=6)
    r1 = compute_risk_score(state, ftp_status="on_track", day_in_recovery=7)
    r2 = compute_risk_score(state, ftp_status="on_track", day_in_recovery=7)
    assert r1.final_score == r2.final_score
    assert r1 == r2  # full breakdown identical


def test_weights_sum_to_one():
    """Sanity: the composition weights must sum to 1.0."""
    total = W_WORST_SYMPTOM + W_MOOD + W_FTP + W_MODIFIERS + W_DAY_FACTOR
    assert abs(total - 1.0) < 1e-9


# --- Monotonicity: worse state → higher score ---

def test_higher_pain_means_higher_score():
    low = compute_risk_score(_smoothed(pain=2, mood=7), ftp_status="on_track", day_in_recovery=10)
    high = compute_risk_score(_smoothed(pain=7, mood=7), ftp_status="on_track", day_in_recovery=10)
    assert high.final_score > low.final_score


def test_worse_mood_means_higher_score():
    ok = compute_risk_score(_smoothed(pain=3, mood=7), ftp_status="on_track", day_in_recovery=10)
    low_mood = compute_risk_score(_smoothed(pain=3, mood=2), ftp_status="on_track", day_in_recovery=10)
    assert low_mood.final_score > ok.final_score


def test_ftp_behind_adds_meaningful_score():
    baseline = compute_risk_score(_smoothed(pain=3, mood=7), ftp_status="on_track", day_in_recovery=10)
    behind = compute_risk_score(_smoothed(pain=3, mood=7), ftp_status="behind", day_in_recovery=10)
    sig_behind = compute_risk_score(_smoothed(pain=3, mood=7), ftp_status="significantly_behind", day_in_recovery=10)
    assert baseline.final_score < behind.final_score < sig_behind.final_score


def test_early_days_elevate_score_slightly():
    """Day 0 patient scored higher than identical patient at day 10."""
    s = _smoothed(pain=3, mood=7)
    day0 = compute_risk_score(s, ftp_status="on_track", day_in_recovery=0)
    day10 = compute_risk_score(s, ftp_status="on_track", day_in_recovery=10)
    assert day0.final_score > day10.final_score


# --- Consistency with RAG bands ---

def test_stable_low_symptoms_scores_green():
    """Classic stable patient — should show GREEN band."""
    state = _smoothed(pain=2, breathlessness=1, mobility=2, appetite=2, mood=7)
    result = compute_risk_score(state, ftp_status="on_track", day_in_recovery=10)
    assert result.final_score < 40
    assert result.band_if_computed == "green"


def test_elevated_symptoms_scores_amber_range():
    """Patient with smoothed symptoms around 6 — should be AMBER territory."""
    state = _smoothed(pain=6, breathlessness=5, mobility=6, appetite=5, mood=5)
    result = compute_risk_score(state, ftp_status="on_track", day_in_recovery=7)
    assert 40 <= result.final_score < 70
    assert result.band_if_computed == "amber"


# --- Safety floors ---

def test_active_red_flag_floors_score_at_70():
    """Even if smoothed state is calm, an active RED flag forces score >= 70."""
    # Calm smoothed state
    state = _smoothed(pain=2, mood=7)
    result = compute_risk_score(
        state, ftp_status="on_track", day_in_recovery=10,
        has_active_red_flag=True,
    )
    assert result.final_score >= RED_FLAG_MIN_FLOOR
    assert result.red_flag_floor_applied
    assert result.band_if_computed == "red"


def test_acute_raw_pain_floors_score():
    """
    Single call reports pain=9 raw but smoothed is still low (lots of good history).
    Score must still reflect the acute reading, not the smoothed calm.
    """
    state = _smoothed(pain=3.5, mood=7)  # smoothed is calm
    result = compute_risk_score(
        state, ftp_status="on_track", day_in_recovery=7,
        raw_pain=9.0,
    )
    assert result.final_score >= ACUTE_SYMPTOM_FLOOR
    assert result.acute_symptom_floor_applied


def test_acute_breathlessness_floors_score():
    state = _smoothed(pain=2, breathlessness=2, mood=7)
    result = compute_risk_score(
        state, ftp_status="on_track", day_in_recovery=7,
        raw_breathlessness=9.0,
    )
    assert result.acute_symptom_floor_applied


def test_red_floor_beats_acute_floor_when_both_apply():
    """If both floors apply, red (70) wins over acute (65)."""
    state = _smoothed(pain=3, mood=7)
    result = compute_risk_score(
        state, ftp_status="on_track", day_in_recovery=7,
        raw_pain=9.0, has_active_red_flag=True,
    )
    assert result.final_score >= RED_FLAG_MIN_FLOOR


# --- Score is always in range ---

def test_score_never_exceeds_100():
    """Even maximally-bad state should cap at 100."""
    state = _smoothed(pain=10, breathlessness=10, mobility=10, appetite=10,
                      mood=0, modifier_total=2.5)
    result = compute_risk_score(
        state, ftp_status="significantly_behind", day_in_recovery=0,
        has_active_red_flag=True, raw_pain=10.0,
    )
    assert result.final_score <= 100.0


def test_score_never_below_zero():
    state = _smoothed()  # all None
    result = compute_risk_score(state, ftp_status="on_track")
    assert result.final_score >= 0.0


# --- Breakdown is complete (defensibility / audit) ---

def test_breakdown_shows_every_contribution():
    state = _smoothed(pain=5, mood=5, modifier_total=1.0)
    result = compute_risk_score(state, ftp_status="behind", day_in_recovery=2)
    # Every component present
    assert result.worst_symptom_component >= 0
    assert result.mood_component >= 0
    assert result.ftp_component >= 0
    assert result.modifier_component >= 0
    assert result.day_factor_component >= 0
    # Weighted versions present
    assert result.weighted_worst_symptom >= 0
    assert result.weighted_ftp > 0  # FTP is "behind"
    # Dominant driver identified
    assert result.dominant_driver in (
        "worst_symptom", "mood", "ftp", "modifiers", "day_factor",
        "red_flag_override", "none",
    )


def test_breakdown_serialises_to_dict():
    """Breakdown must be JSON-serialisable for storage in JSONB column."""
    import json
    state = _smoothed(pain=4, mood=6)
    result = compute_risk_score(state, ftp_status="on_track", day_in_recovery=5)
    d = breakdown_to_dict(result)
    # Should be JSON-round-trippable
    roundtrip = json.loads(json.dumps(d))
    assert roundtrip["final_score"] == result.final_score


# --- Integration with smoothing ---

def test_end_to_end_with_real_smoothing():
    """Score computed from output of smooth_extraction should work without adjustment."""
    extraction = {
        "pain_score": 4, "breathlessness_score": 3, "mobility_score": 5,
        "appetite_score": 4, "mood_score": 6, "medication_adherence": True,
    }
    smoothed = smooth_extraction(extraction, prior_smoothed=None)
    result = compute_risk_score(smoothed, ftp_status="on_track", day_in_recovery=7)
    assert 0 <= result.final_score <= 100
    assert result.dominant_driver != "none"


# --- The fix in action: Claude Code's exact scenario ---

def test_red_patient_score_reflects_clinical_state_not_uuid():
    """
    Claude Code said: 'A red patient might show 73 or 84 — both are just 70 +
    (some fixed number derived from their ID).'

    This test proves: two red patients with DIFFERENT clinical state get
    DIFFERENT scores, but the difference reflects CLINICAL reality.
    """
    # Red patient 1: severe pain, FTP behind
    red1 = compute_risk_score(
        _smoothed(pain=7, breathlessness=5, mood=4),
        ftp_status="behind", day_in_recovery=5,
        has_active_red_flag=True,
    )
    # Red patient 2: chest pain flag but otherwise moderate
    red2 = compute_risk_score(
        _smoothed(pain=3, breathlessness=3, mood=7),
        ftp_status="on_track", day_in_recovery=5,
        has_active_red_flag=True,
    )
    # Both are red
    assert red1.band_if_computed == "red"
    assert red2.band_if_computed == "red"
    # But red1 should score HIGHER than red2 — because it's clinically worse
    assert red1.final_score > red2.final_score, (
        f"red1 ({red1.final_score}) clinically worse than red2 "
        f"({red2.final_score}) but didn't score higher"
    )

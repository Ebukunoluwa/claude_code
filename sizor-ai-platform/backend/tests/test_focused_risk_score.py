"""Tests for scoring_scope='probe_focused' in compute_risk_score.

Phase 2.5 Fix 1. Probe calls compute a FOCUSED risk score over only the
domains they asked about — missing domains are excluded from the
calculation, not treated as zero. Weights are renormalised over the
components that actually have data.

Run: PYTHONPATH=. python -m pytest tests/test_focused_risk_score.py -v
"""
from app.clinical_intelligence.risk_score import (
    ACUTE_SYMPTOM_FLOOR,
    RED_FLAG_MIN_FLOOR,
    W_MOOD,
    W_WORST_SYMPTOM,
    compute_risk_score,
)
from app.clinical_intelligence.smoothing import SmoothedScores


def _smoothed(
    pain=None, breathlessness=None, mobility=None,
    appetite=None, mood=None, modifier_total=0.0,
):
    """Minimal SmoothedScores constructor. Everything None by default —
    the caller specifies only the domains relevant to the scenario."""
    values = [v for v in (pain, breathlessness, mobility, appetite) if v is not None]
    return SmoothedScores(
        pain=pain,
        breathlessness=breathlessness,
        mobility=mobility,
        appetite=appetite,
        mood=mood,
        max_smoothed=max(values, default=0.0),
        modifier_total=modifier_total,
        modifier_detail={},
        lam=0.3,
    )


class TestFocusedPainOnly:
    def test_pain_only_renormalises_to_full_weight(self):
        # smoothed pain=7 → _worst_symptom_component curve gives 80.
        # Full mode would apply weight 0.55 → 44. Focused mode puts
        # worst_symptom at the full renormalised weight (1.0) → ≈80.
        result = compute_risk_score(
            _smoothed(pain=7), scoring_scope="probe_focused",
        )
        assert 78 <= result.final_score <= 82
        assert result.dominant_driver == "worst_symptom"

    def test_pain_only_vs_full_mode_diverge(self):
        full = compute_risk_score(_smoothed(pain=7), scoring_scope="full")
        focused = compute_risk_score(_smoothed(pain=7), scoring_scope="probe_focused")
        # Focused must score higher — it's the point of the fix.
        assert focused.final_score > full.final_score
        assert focused.final_score - full.final_score > 30


class TestFocusedPainPlusMood:
    def test_pain_and_mood_renormalised(self):
        # smoothed pain=7 → worst_symptom=80 (via the curve)
        # smoothed mood=3 → mood concern = (10-3)*10 = 70
        # Renormalised weights: 0.55/(0.55+0.15)=0.786 on symptom,
        #                       0.15/(0.55+0.15)=0.214 on mood.
        # Expected ≈ 0.786*80 + 0.214*70 = 77.9
        result = compute_risk_score(
            _smoothed(pain=7, mood=3),
            scoring_scope="probe_focused",
        )
        assert 76 <= result.final_score <= 80


class TestFocusedNoData:
    def test_no_data_scores_zero(self):
        result = compute_risk_score(_smoothed(), scoring_scope="probe_focused")
        assert result.final_score == 0.0
        # No acute floor fires because no raw_pain/raw_breathlessness supplied.
        assert result.acute_symptom_floor_applied is False
        assert result.red_flag_floor_applied is False


class TestFocusedSkipsLongitudinalComponents:
    def test_ftp_ignored_in_focused(self):
        # Probe with no ftp-relevant call history — ftp_status wouldn't
        # apply even if passed. Assert the final doesn't move when we
        # change ftp_status on a focused call.
        a = compute_risk_score(
            _smoothed(pain=7), scoring_scope="probe_focused",
            ftp_status="on_track",
        )
        b = compute_risk_score(
            _smoothed(pain=7), scoring_scope="probe_focused",
            ftp_status="significantly_behind",
        )
        assert a.final_score == b.final_score
        assert a.ftp_component == 0.0
        assert b.ftp_component == 0.0

    def test_day_factor_ignored_in_focused(self):
        a = compute_risk_score(
            _smoothed(pain=7), scoring_scope="probe_focused",
            day_in_recovery=0,
        )
        b = compute_risk_score(
            _smoothed(pain=7), scoring_scope="probe_focused",
            day_in_recovery=30,
        )
        assert a.final_score == b.final_score
        assert a.day_factor_component == 0.0
        assert b.day_factor_component == 0.0

    def test_modifier_ignored_in_focused(self):
        a = compute_risk_score(
            _smoothed(pain=7, modifier_total=0.0),
            scoring_scope="probe_focused",
        )
        b = compute_risk_score(
            _smoothed(pain=7, modifier_total=2.5),   # max non-zero modifier
            scoring_scope="probe_focused",
        )
        assert a.final_score == b.final_score
        assert b.modifier_component == 0.0


class TestFocusedSafetyFloors:
    def test_red_flag_floor_still_applies(self):
        # No symptom data at all, but red flag set → floor at 70.
        result = compute_risk_score(
            _smoothed(),
            scoring_scope="probe_focused",
            has_active_red_flag=True,
        )
        assert result.final_score >= RED_FLAG_MIN_FLOOR
        assert result.red_flag_floor_applied is True

    def test_acute_pain_floor_still_applies(self):
        # Focused mode without smoothed data, but raw_pain=9 → floor at 65.
        result = compute_risk_score(
            _smoothed(),
            scoring_scope="probe_focused",
            raw_pain=9.0,
        )
        assert result.final_score >= ACUTE_SYMPTOM_FLOOR
        assert result.acute_symptom_floor_applied is True


class TestFullModeUntouched:
    def test_default_scoping_is_full(self):
        # Default behaviour must still be 'full'. Anyone not passing
        # scoring_scope must get the historical contract.
        same_inputs_full = compute_risk_score(
            _smoothed(pain=3, mood=7),
            ftp_status="on_track", day_in_recovery=10,
        )
        explicit_full = compute_risk_score(
            _smoothed(pain=3, mood=7),
            ftp_status="on_track", day_in_recovery=10,
            scoring_scope="full",
        )
        assert same_inputs_full.final_score == explicit_full.final_score
        # All five weighted fields present in full mode — asserting no
        # focused-mode zeroing leaked into the default path.
        assert same_inputs_full.weighted_worst_symptom > 0


class TestFocusedMoodOnly:
    def test_mood_only_renormalises(self):
        # Probe asking only about mood. smoothed mood=2 → concern=80.
        # In focused mode with only mood present, weight = 1.0 → score ≈ 80.
        result = compute_risk_score(
            _smoothed(mood=2), scoring_scope="probe_focused",
        )
        assert 78 <= result.final_score <= 82


class TestWeightConstants:
    """Guardrails on the weight constants. If someone changes W_WORST_SYMPTOM
    or W_MOOD in the full-mode config, focused-mode scoring changes too —
    both must be re-validated clinically."""

    def test_weights_known_values(self):
        assert W_WORST_SYMPTOM == 0.55
        assert W_MOOD == 0.15

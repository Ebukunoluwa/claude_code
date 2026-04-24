"""Tests for compute_overall_call_status.

Rule order (first match wins):
  1. Red Flag override  (any escalation_flag OR any red_flags_detected)
  2. Double-Amber       (2+ domains in monitor status)
  3. Fall through to CallRiskAssessment band

Run: PYTHONPATH=. python -m pytest tests/test_call_status.py -v
"""
from app.clinical_intelligence import (
    DomainClassification,
    DomainTrend,
    EscalationTier,
    RedFlagCategory,
    RiskBand,
    compute_overall_call_status,
)


def _cls(
    *,
    domain: str = "pain",
    score: int = 1,
    expected: int = 1,
    upper_bound: int = 2,
    trajectory: DomainTrend = DomainTrend.STABLE,
    escalation_flag: bool = False,
    tier: EscalationTier = EscalationTier.NONE,
) -> DomainClassification:
    return DomainClassification(
        domain=domain,
        score=score,
        expected=expected,
        upper_bound=upper_bound,
        above_upper_bound=score > upper_bound,
        trajectory=trajectory,
        ftp_flag=False,
        escalation_flag=escalation_flag,
        escalation_tier=tier,
        nice_basis=None,
    )


class TestRedFlagOverride:
    def test_single_domain_escalation_flag_fires_red(self):
        classifications = [
            _cls(domain="pain", score=4, expected=1, upper_bound=2,
                 escalation_flag=True, tier=EscalationTier.EMERGENCY_999),
            _cls(domain="mood", score=0),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.band == RiskBand.RED
        assert result.primary_reason == "red_flag_override"
        assert result.contributing == ["pain"]

    def test_system_level_red_flag_fires_red_without_domain_escalation(self):
        classifications = [_cls(score=1)]
        result = compute_overall_call_status(
            classifications, [RedFlagCategory.SEPSIS_SIGNS], RiskBand.GREEN,
        )
        assert result.band == RiskBand.RED
        assert result.primary_reason == "red_flag_override"
        assert result.contributing == ["sepsis_signs"]

    def test_red_flag_override_beats_double_amber_ordering(self):
        # Two monitor-status domains would Double-Amber on their own,
        # but a red flag on a third domain takes precedence.
        classifications = [
            _cls(domain="pain",   score=2, expected=1, upper_bound=3),
            _cls(domain="mood",   score=2, expected=1, upper_bound=3),
            _cls(domain="wound",  score=4, expected=1, upper_bound=2,
                 escalation_flag=True, tier=EscalationTier.EMERGENCY_999),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.AMBER)
        assert result.band == RiskBand.RED
        assert result.primary_reason == "red_flag_override"
        assert "wound" in result.contributing
        # Monitor domains must NOT appear in contributing for a red-flag path.
        assert "pain" not in result.contributing
        assert "mood" not in result.contributing


class TestDoubleAmber:
    def test_two_monitor_domains_fires_amber(self):
        # Both above expected, both within upper_bound, neither at 4.
        classifications = [
            _cls(domain="pain",   score=2, expected=1, upper_bound=3),
            _cls(domain="mood",   score=2, expected=1, upper_bound=3),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.band == RiskBand.AMBER
        assert result.primary_reason == "double_amber"
        assert set(result.contributing) == {"pain", "mood"}

    def test_three_monitor_domains_still_fires_amber(self):
        classifications = [
            _cls(domain="pain",  score=2, expected=1, upper_bound=3),
            _cls(domain="mood",  score=2, expected=1, upper_bound=3),
            _cls(domain="wound", score=2, expected=1, upper_bound=3),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.band == RiskBand.AMBER
        assert result.primary_reason == "double_amber"
        assert len(result.contributing) == 3

    def test_single_monitor_domain_falls_through(self):
        classifications = [
            _cls(domain="pain", score=2, expected=1, upper_bound=3),
            _cls(domain="mood", score=1, expected=1, upper_bound=3),  # at expected
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.primary_reason == "call_risk_assessment_band"
        assert result.band == RiskBand.GREEN

    def test_two_at_expected_does_not_fire(self):
        # Exactly at expected -> not monitor.
        classifications = [
            _cls(domain="pain", score=1, expected=1, upper_bound=3),
            _cls(domain="mood", score=1, expected=1, upper_bound=3),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.primary_reason == "call_risk_assessment_band"

    def test_above_upper_bound_not_counted_as_monitor(self):
        # score > upper_bound is "expedite" status, not "monitor".
        # The Double-Amber rule only counts monitor — this one has escalation
        # flag off (Q2 answer: STRICT = count monitor specifically).
        classifications = [
            _cls(domain="pain", score=3, expected=1, upper_bound=2),  # expedite
            _cls(domain="mood", score=3, expected=1, upper_bound=2),  # expedite
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        # No Double-Amber fire because neither is in monitor status.
        # Falls through to the call assessment band.
        assert result.primary_reason == "call_risk_assessment_band"

    def test_score_4_excluded_from_monitor_count(self):
        # Score 4 is "escalate" status, always triggers red-flag override
        # via escalation_flag. But even without the flag set, score==4
        # is not monitor.
        classifications = [
            _cls(domain="pain", score=4, expected=1, upper_bound=4),  # escalate
            _cls(domain="mood", score=2, expected=1, upper_bound=3),  # monitor
        ]
        # No escalation_flag set here, so not a red-flag path.
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.primary_reason == "call_risk_assessment_band"


class TestFallThrough:
    def test_empty_classifications_returns_assessment_band(self):
        result = compute_overall_call_status([], [], RiskBand.AMBER)
        assert result.band == RiskBand.AMBER
        assert result.primary_reason == "call_risk_assessment_band"
        assert result.contributing == []

    def test_all_expected_returns_assessment_band(self):
        classifications = [
            _cls(domain="pain", score=1, expected=1, upper_bound=3),
            _cls(domain="mood", score=0, expected=0, upper_bound=2),
        ]
        result = compute_overall_call_status(classifications, [], RiskBand.GREEN)
        assert result.band == RiskBand.GREEN
        assert result.primary_reason == "call_risk_assessment_band"

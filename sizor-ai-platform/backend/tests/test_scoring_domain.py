"""Tests for score_patient_domain — per-domain classification against
pathway+day trajectory. Replaces the test coverage that would have
existed for the deleted clinical/scoring.py::score_domain.

Run: PYTHONPATH=. python -m pytest tests/test_scoring_domain.py -v
"""
from app.clinical_intelligence import (
    ConfidenceLevel,
    DomainScore,
    DomainTrajectoryEntry,
    DomainTrend,
    EscalationTier,
    score_patient_domain,
)


def _score(value: int, domain: str = "pain") -> DomainScore:
    return DomainScore(
        domain=domain,
        raw_score=value,
        evidence_quote="stub",
        confidence=ConfidenceLevel.HIGH,
    )


def _trajectory(expected: int, upper_bound: int, domain: str = "pain") -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code="W37",
        domain=domain,
        day_range_start=0,
        day_range_end=7,
        expected_score=expected,
        upper_bound_score=upper_bound,
        nice_source="NG226-test",
    )


class TestTrajectoryTrend:
    def test_no_priors_is_insufficient_data(self):
        c = score_patient_domain(_score(2), [], _trajectory(1, 2))
        assert c.trajectory == DomainTrend.INSUFFICIENT_DATA

    def test_lower_than_prior_is_improving(self):
        c = score_patient_domain(_score(1), [_score(3)], _trajectory(1, 2))
        assert c.trajectory == DomainTrend.IMPROVING

    def test_equal_to_prior_is_stable(self):
        c = score_patient_domain(_score(2), [_score(2)], _trajectory(1, 2))
        assert c.trajectory == DomainTrend.STABLE

    def test_higher_than_prior_is_deteriorating(self):
        c = score_patient_domain(_score(3), [_score(2)], _trajectory(1, 2))
        assert c.trajectory == DomainTrend.DETERIORATING

    def test_uses_most_recent_prior_only(self):
        # Priors of [1, 3], current=2 -> last prior was 3, current<3 -> improving.
        c = score_patient_domain(_score(2), [_score(1), _score(3)], _trajectory(1, 2))
        assert c.trajectory == DomainTrend.IMPROVING


class TestFtpFlag:
    def test_not_set_with_single_prior(self):
        c = score_patient_domain(_score(2), [_score(2)], _trajectory(1, 2))
        assert c.ftp_flag is False

    def test_fires_on_two_consecutive_at_upper_bound(self):
        c = score_patient_domain(_score(2), [_score(2), _score(2)], _trajectory(1, 2))
        assert c.ftp_flag is True

    def test_does_not_fire_if_current_below_upper_bound(self):
        c = score_patient_domain(_score(1), [_score(2), _score(2)], _trajectory(1, 2))
        assert c.ftp_flag is False

    def test_does_not_fire_if_last_two_priors_not_both_above(self):
        c = score_patient_domain(_score(2), [_score(1), _score(2)], _trajectory(1, 2))
        assert c.ftp_flag is False


class TestEscalationTier:
    def test_score_4_is_emergency(self):
        c = score_patient_domain(_score(4), [_score(3)], _trajectory(1, 2))
        assert c.escalation_tier == EscalationTier.EMERGENCY_999
        assert c.escalation_flag is True

    def test_score_3_is_same_day(self):
        c = score_patient_domain(_score(3), [_score(2)], _trajectory(1, 2))
        assert c.escalation_tier == EscalationTier.SAME_DAY
        assert c.escalation_flag is True

    def test_above_upper_and_deteriorating_is_urgent_gp(self):
        # expected=0, upper_bound=1, score=2 (above upper), prior=1 -> deteriorating.
        c = score_patient_domain(_score(2), [_score(1)], _trajectory(0, 1))
        assert c.escalation_tier == EscalationTier.URGENT_GP
        assert c.escalation_flag is True

    def test_above_upper_but_improving_is_not_urgent(self):
        # Above upper bound but improving from higher — no urgent tier.
        # score=2 at upper_bound=1, prior=3 -> improving (score<prior).
        # Still, the ftp rule would check: last two at upper_bound or above?
        # Priors of [3] only, so ftp needs 2 priors.
        c = score_patient_domain(_score(2), [_score(3)], _trajectory(0, 1))
        assert c.trajectory == DomainTrend.IMPROVING
        assert c.escalation_tier == EscalationTier.NONE
        assert c.escalation_flag is False

    def test_ftp_without_score_34_is_next_call(self):
        # score=2 == upper_bound, 2 priors both at upper_bound -> FTP.
        # Score not 3 or 4, not above upper, not deteriorating relative to
        # stable prior -> falls through to NEXT_CALL.
        c = score_patient_domain(_score(2), [_score(2), _score(2)], _trajectory(1, 2))
        assert c.ftp_flag is True
        assert c.escalation_tier == EscalationTier.NEXT_CALL
        assert c.escalation_flag is True

    def test_on_track_no_escalation(self):
        c = score_patient_domain(_score(1), [_score(1)], _trajectory(1, 2))
        assert c.escalation_flag is False
        assert c.escalation_tier == EscalationTier.NONE


class TestMonitorStatus:
    """Expected < score <= upper_bound AND score < 4 — the state the
    Double-Amber rule counts on. Verified here at the per-domain level."""

    def test_at_monitor_boundary(self):
        # expected=1, upper_bound=3, score=2 -> monitor.
        c = score_patient_domain(_score(2), [_score(2)], _trajectory(1, 3))
        assert c.expected < c.score <= c.upper_bound
        assert c.score < 4
        # No escalation — monitor status is not an emergency trigger on its own.
        assert c.escalation_flag is False


class TestFields:
    def test_preserves_domain_name(self):
        c = score_patient_domain(_score(2, "wound"), [], _trajectory(1, 2, "wound"))
        assert c.domain == "wound"

    def test_carries_nice_source(self):
        c = score_patient_domain(_score(2), [], _trajectory(1, 2))
        assert c.nice_basis == "NG226-test"

    def test_above_upper_flag(self):
        c = score_patient_domain(_score(3), [], _trajectory(1, 2))
        assert c.above_upper_bound is True

    def test_not_above_upper_at_boundary(self):
        c = score_patient_domain(_score(2), [], _trajectory(1, 2))
        assert c.above_upper_bound is False

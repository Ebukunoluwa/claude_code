"""Tests for validate_extraction_plausibility.

Two detectors per PLAN.md Sec 4 (Q3-approved TIGHT scope, no
generalisation):
  - first_call_all_fours: first call + 3 or more domains scored 4
  - all_domains_dropped_to_empty: prior had 2+ non-zero, current empty

Run: PYTHONPATH=. python -m pytest tests/test_validation.py -v
"""
from app.clinical_intelligence import (
    ConfidenceLevel,
    DomainScore,
    validate_extraction_plausibility,
)


def _s(domain: str, score: int) -> DomainScore:
    return DomainScore(
        domain=domain,
        raw_score=score,
        evidence_quote="stub",
        confidence=ConfidenceLevel.HIGH,
    )


class TestFirstCallAllFours:
    def test_first_call_three_fours_fires(self):
        current = [_s("pain", 4), _s("mood", 4), _s("wound", 4)]
        warnings = validate_extraction_plausibility(current, [])
        codes = [w.code for w in warnings]
        assert "first_call_all_fours" in codes

        w = next(w for w in warnings if w.code == "first_call_all_fours")
        assert w.severity == "warn"
        assert set(w.affected_domains) == {"pain", "mood", "wound"}

    def test_first_call_five_fours_fires(self):
        current = [
            _s("pain", 4), _s("mood", 4), _s("wound", 4),
            _s("mobility", 4), _s("breathlessness", 4),
        ]
        warnings = validate_extraction_plausibility(current, [])
        assert any(w.code == "first_call_all_fours" for w in warnings)

    def test_first_call_two_fours_does_not_fire(self):
        current = [_s("pain", 4), _s("mood", 4), _s("wound", 2)]
        warnings = validate_extraction_plausibility(current, [])
        assert not any(w.code == "first_call_all_fours" for w in warnings)

    def test_first_call_no_fours_does_not_fire(self):
        current = [_s("pain", 2), _s("mood", 1)]
        warnings = validate_extraction_plausibility(current, [])
        assert not any(w.code == "first_call_all_fours" for w in warnings)

    def test_mid_history_with_three_fours_does_not_fire(self):
        # Not a first call — the detector only applies to empty history.
        current = [_s("pain", 4), _s("mood", 4), _s("wound", 4)]
        prior = [[_s("pain", 2), _s("mood", 3)]]
        warnings = validate_extraction_plausibility(current, prior)
        assert not any(w.code == "first_call_all_fours" for w in warnings)


class TestAllDomainsDroppedToEmpty:
    def test_drop_from_two_nonzero_to_empty_fires(self):
        prior = [[_s("pain", 2), _s("mood", 3)]]
        warnings = validate_extraction_plausibility([], prior)
        codes = [w.code for w in warnings]
        assert "all_domains_dropped_to_empty" in codes

        w = next(w for w in warnings if w.code == "all_domains_dropped_to_empty")
        assert w.severity == "warn"
        assert set(w.affected_domains) == {"pain", "mood"}

    def test_drop_uses_most_recent_prior_call(self):
        # Earlier call was empty-ish; most recent was rich.
        prior = [
            [],
            [_s("pain", 2), _s("mood", 3), _s("wound", 1)],
        ]
        warnings = validate_extraction_plausibility([], prior)
        assert any(w.code == "all_domains_dropped_to_empty" for w in warnings)

    def test_drop_from_one_nonzero_to_empty_does_not_fire(self):
        prior = [[_s("pain", 2), _s("mood", 0)]]
        warnings = validate_extraction_plausibility([], prior)
        assert not any(
            w.code == "all_domains_dropped_to_empty" for w in warnings
        )

    def test_drop_from_prior_with_only_zeros_does_not_fire(self):
        prior = [[_s("pain", 0), _s("mood", 0)]]
        warnings = validate_extraction_plausibility([], prior)
        assert not any(
            w.code == "all_domains_dropped_to_empty" for w in warnings
        )

    def test_current_populated_does_not_fire(self):
        current = [_s("pain", 1)]
        prior = [[_s("pain", 2), _s("mood", 3)]]
        warnings = validate_extraction_plausibility(current, prior)
        assert not any(
            w.code == "all_domains_dropped_to_empty" for w in warnings
        )

    def test_no_prior_history_does_not_fire(self):
        warnings = validate_extraction_plausibility([], [])
        assert not any(
            w.code == "all_domains_dropped_to_empty" for w in warnings
        )

    def test_drop_from_already_empty_prior_does_not_fire(self):
        prior = [[]]
        warnings = validate_extraction_plausibility([], prior)
        assert not any(
            w.code == "all_domains_dropped_to_empty" for w in warnings
        )


class TestDetectorIndependence:
    def test_detectors_are_not_both_triggered_by_first_empty(self):
        # First call, but current is also empty. Neither detector fires
        # (first-call-fours needs fours; drop-to-empty needs prior).
        warnings = validate_extraction_plausibility([], [])
        assert warnings == []

    def test_nothing_fires_on_normal_post_discharge_call(self):
        current = [_s("pain", 2), _s("mood", 1), _s("wound", 1)]
        prior = [[_s("pain", 3), _s("mood", 2), _s("wound", 2)]]
        warnings = validate_extraction_plausibility(current, prior)
        assert warnings == []

    def test_returns_empty_list_not_none_when_nothing_fires(self):
        result = validate_extraction_plausibility([], [])
        assert result == []
        assert isinstance(result, list)

"""Tests for app.clinical.scoring.score_0_10_to_0_4 — the categorical 0-10 →
0-4 mapping that replaces the clinically unsafe linear 0.4 multiplier.

Run: PYTHONPATH=. python -m pytest tests/test_categorical_mapping.py -v
"""
import pytest

from app.clinical_intelligence.scoring import score_0_10_to_0_4


class TestBoundaries:
    """Every bucket boundary from the brief."""

    def test_zero_maps_to_zero(self):
        assert score_0_10_to_0_4(0) == 0

    def test_one_maps_to_one(self):
        # The key clinical-safety case: linear 0.4×1 rounds to 0 (signal lost);
        # categorical preserves "mild" at 1.
        assert score_0_10_to_0_4(1) == 1

    def test_three_maps_to_one(self):
        assert score_0_10_to_0_4(3) == 1

    def test_four_maps_to_two(self):
        assert score_0_10_to_0_4(4) == 2

    def test_six_maps_to_two(self):
        assert score_0_10_to_0_4(6) == 2

    def test_seven_maps_to_three(self):
        assert score_0_10_to_0_4(7) == 3

    def test_eight_maps_to_three(self):
        assert score_0_10_to_0_4(8) == 3

    def test_nine_maps_to_four(self):
        assert score_0_10_to_0_4(9) == 4

    def test_ten_maps_to_four(self):
        assert score_0_10_to_0_4(10) == 4


class TestLinearDivergence:
    """Cases where linear and categorical disagree. These are the reason we
    are making the change — document them explicitly in tests."""

    @pytest.mark.parametrize("raw", [1])
    def test_categorical_preserves_mild_signal_that_linear_drops(self, raw):
        # round(1 * 0.4) == 0, categorical == 1
        linear = max(0, min(4, round(raw * 0.4)))
        categorical = score_0_10_to_0_4(raw)
        assert linear == 0
        assert categorical == 1


class TestNoneAndMissing:
    def test_none_in_none_out(self):
        assert score_0_10_to_0_4(None) is None

    def test_unparseable_string_returns_none(self):
        assert score_0_10_to_0_4("not a number") is None  # type: ignore[arg-type]


class TestRangeClamping:
    def test_negative_clamps_to_zero(self):
        assert score_0_10_to_0_4(-5) == 0

    def test_above_ten_clamps_to_four(self):
        assert score_0_10_to_0_4(15) == 4

    def test_exactly_zero_float(self):
        assert score_0_10_to_0_4(0.0) == 0


class TestFloatInputs:
    def test_half_rounds_and_maps(self):
        # 7.5 → round to 8 → 3
        assert score_0_10_to_0_4(7.5) == 3

    def test_three_point_four_rounds_to_three(self):
        # 3.4 → round to 3 → 1
        assert score_0_10_to_0_4(3.4) == 1

    def test_three_point_six_rounds_to_four(self):
        # 3.6 → round to 4 → 2 (crosses bucket boundary)
        assert score_0_10_to_0_4(3.6) == 2


class TestFullSweep:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (0, 0),
            (1, 1), (2, 1), (3, 1),
            (4, 2), (5, 2), (6, 2),
            (7, 3), (8, 3),
            (9, 4), (10, 4),
        ],
    )
    def test_every_integer(self, raw, expected):
        assert score_0_10_to_0_4(raw) == expected

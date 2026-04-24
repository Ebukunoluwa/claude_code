"""Tests for collapse_same_day_observations + is_consecutive_day_ftp.

Phase 2.5 Fix 2. Europe/London timezone is the day boundary per PLAN.md
Q2. Fixture timestamps are crafted to exercise midnight-crossing and
BST/GMT edge cases.

Run: PYTHONPATH=. python -m pytest tests/test_ftp_same_day_collapse.py -v
"""
from datetime import datetime, timedelta, timezone

from app.clinical_intelligence.ftp_detector import (
    TimestampedScore,
    collapse_same_day_observations,
    is_consecutive_day_ftp,
)


def _ts(yyyy, mm, dd, hh=12, mi=0) -> datetime:
    return datetime(yyyy, mm, dd, hh, mi, tzinfo=timezone.utc)


def _cluster_11_in_90min(year, month, day) -> list[TimestampedScore]:
    """Eleven pain=4 observations spaced ~9 minutes apart starting at
    00:00 on the given calendar date. Stays within one calendar day."""
    base = datetime(year, month, day, 0, 0, tzinfo=timezone.utc)
    return [
        TimestampedScore("pain", 4, base + timedelta(minutes=9 * i))
        for i in range(11)
    ]


class TestCollapse:
    def test_empty_returns_empty(self):
        assert collapse_same_day_observations([]) == []

    def test_single_observation_passes_through(self):
        o = TimestampedScore("pain", 2, _ts(2026, 6, 1))
        assert collapse_same_day_observations([o]) == [o]

    def test_same_day_same_domain_keeps_max(self):
        low = TimestampedScore("pain", 1, _ts(2026, 6, 1, 10))
        high = TimestampedScore("pain", 4, _ts(2026, 6, 1, 12))
        also_low = TimestampedScore("pain", 2, _ts(2026, 6, 1, 14))
        out = collapse_same_day_observations([low, high, also_low])
        assert out == [high]

    def test_tie_score_keeps_latest_timestamp(self):
        earlier = TimestampedScore("pain", 3, _ts(2026, 6, 1, 9))
        later = TimestampedScore("pain", 3, _ts(2026, 6, 1, 18))
        out = collapse_same_day_observations([earlier, later])
        assert out == [later]

    def test_different_domains_do_not_collapse(self):
        pain = TimestampedScore("pain", 3, _ts(2026, 6, 1))
        mood = TimestampedScore("mood", 3, _ts(2026, 6, 1))
        out = collapse_same_day_observations([pain, mood])
        assert len(out) == 2
        assert {o.domain for o in out} == {"pain", "mood"}

    def test_cross_day_observations_preserved(self):
        d1 = TimestampedScore("pain", 2, _ts(2026, 6, 1, 12))
        d2 = TimestampedScore("pain", 3, _ts(2026, 6, 2, 12))
        d3 = TimestampedScore("pain", 4, _ts(2026, 6, 3, 12))
        out = collapse_same_day_observations([d1, d2, d3])
        assert out == [d1, d2, d3]

    def test_output_sorted_chronologically(self):
        # Intentionally reversed input.
        d3 = TimestampedScore("pain", 4, _ts(2026, 6, 3, 12))
        d1 = TimestampedScore("pain", 2, _ts(2026, 6, 1, 12))
        d2 = TimestampedScore("pain", 3, _ts(2026, 6, 2, 12))
        out = collapse_same_day_observations([d3, d1, d2])
        assert [o.extracted_at for o in out] == [
            d1.extracted_at, d2.extracted_at, d3.extracted_at,
        ]


class TestLondonTimezoneDayBoundary:
    def test_bst_summer_late_evening_utc_is_next_london_day(self):
        # 2026-06-01 23:30 UTC is 2026-06-02 00:30 BST (London).
        # Should be a different calendar day from a 2026-06-02 01:00 UTC
        # observation (which is 2026-06-02 02:00 BST).
        late_utc = TimestampedScore("pain", 3, _ts(2026, 6, 1, 23, 30))
        early_next_utc = TimestampedScore("pain", 4, _ts(2026, 6, 2, 1, 0))
        out = collapse_same_day_observations([late_utc, early_next_utc])
        # Both fall on Europe/London 2026-06-02 — collapse takes max.
        assert len(out) == 1
        assert out[0].raw_score == 4

    def test_gmt_winter_day_boundary(self):
        # 2026-12-01 23:30 UTC = 2026-12-01 23:30 GMT (London winter).
        # 2026-12-02 00:30 UTC = 2026-12-02 00:30 GMT.
        # Different London calendar days.
        dec_1 = TimestampedScore("pain", 3, _ts(2026, 12, 1, 23, 30))
        dec_2 = TimestampedScore("pain", 4, _ts(2026, 12, 2, 0, 30))
        out = collapse_same_day_observations([dec_1, dec_2])
        assert len(out) == 2


class TestConsecutiveDayFtp:
    def test_runaway_cluster_does_not_fire(self):
        # 11 extractions spaced ~9 minutes apart, all at score 4, all same
        # calendar day. Post-collapse: one observation. FTP window=2 needs
        # 2 consecutive DAYS — cluster doesn't satisfy.
        cluster = _cluster_11_in_90min(2026, 6, 15)
        daily = collapse_same_day_observations(cluster)
        assert len(daily) == 1
        assert is_consecutive_day_ftp(daily, upper_bound=2) is False

    def test_two_consecutive_days_above_fires(self):
        d1 = TimestampedScore("pain", 3, _ts(2026, 6, 1))
        d2 = TimestampedScore("pain", 3, _ts(2026, 6, 2))
        assert is_consecutive_day_ftp([d1, d2], upper_bound=2) is True

    def test_gap_day_does_not_fire(self):
        d1 = TimestampedScore("pain", 3, _ts(2026, 6, 1))
        d3 = TimestampedScore("pain", 3, _ts(2026, 6, 3))  # gap — no 2026-06-02
        assert is_consecutive_day_ftp([d1, d3], upper_bound=2) is False

    def test_one_below_upper_bound_does_not_fire(self):
        d1 = TimestampedScore("pain", 3, _ts(2026, 6, 1))
        d2 = TimestampedScore("pain", 1, _ts(2026, 6, 2))  # below upper_bound=2
        assert is_consecutive_day_ftp([d1, d2], upper_bound=2) is False

    def test_three_day_streak_with_window_2(self):
        d1 = TimestampedScore("pain", 3, _ts(2026, 6, 1))
        d2 = TimestampedScore("pain", 3, _ts(2026, 6, 2))
        d3 = TimestampedScore("pain", 3, _ts(2026, 6, 3))
        assert is_consecutive_day_ftp([d1, d2, d3], upper_bound=2) is True

    def test_raises_noop_below_window_size(self):
        # Single-day streak with window=2 — can't fire.
        d1 = TimestampedScore("pain", 4, _ts(2026, 6, 1))
        assert is_consecutive_day_ftp([d1], upper_bound=2) is False

    def test_empty_list_does_not_fire(self):
        assert is_consecutive_day_ftp([], upper_bound=2) is False

    def test_runaway_plus_single_next_day_still_does_not_fire_if_next_day_below(self):
        cluster = _cluster_11_in_90min(2026, 6, 15)
        next_day = TimestampedScore("pain", 1, _ts(2026, 6, 16, 12))
        daily = collapse_same_day_observations(cluster + [next_day])
        assert len(daily) == 2
        # Day 1 max=4 (>=2), day 2 max=1 (<2) — FTP should NOT fire.
        assert is_consecutive_day_ftp(daily, upper_bound=2) is False

    def test_runaway_plus_next_day_above_does_fire(self):
        cluster = _cluster_11_in_90min(2026, 6, 15)
        next_day = TimestampedScore("pain", 3, _ts(2026, 6, 16, 12))
        daily = collapse_same_day_observations(cluster + [next_day])
        assert len(daily) == 2
        # Day 1 max=4, day 2 max=3, both >=2 → FTP fires.
        assert is_consecutive_day_ftp(daily, upper_bound=2) is True

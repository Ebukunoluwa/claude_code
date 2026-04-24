"""FTP (Failure to Progress) helpers for clinical_intelligence.

Phase 2.5 Fix 2 adds collapse_same_day_observations — a pre-processor
that groups per-domain extractions by Europe/London calendar day and
keeps the day's maximum score. Downstream, score_patient_domain's
consecutive-calls FTP rule (added in Phase 2) counts consecutive
calendar days instead of consecutive raw extraction rows.

Not wired into the live pipeline in Phase 2.5 — the live FTP engine
is services.ftp_service::compute_ftp, which is variance-based and
per-call, with no consecutive-row concept. score_patient_domain is
the eventual consumer; Phase 4 will wire it and use this helper.

Timezone: Europe/London per PLAN.md Phase 2.5 Q2. Flagged as a
platform-wide implicit assumption that should become a Patient.timezone
or Hospital.timezone field in a later phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


_LONDON = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class TimestampedScore:
    """A single per-domain observation with its extraction timestamp.

    Intentionally minimal — the collapse helper doesn't need DomainScore's
    full Pydantic shape (evidence_quote, confidence). Callers build these
    from either DomainScore + timestamp or directly from ClinicalExtraction
    rows.
    """
    domain: str
    raw_score: int
    extracted_at: datetime


def _to_london_date(ts: datetime):
    """Convert a (naive or aware) timestamp to its Europe/London calendar
    date. A naive timestamp is assumed to be UTC (matches what asyncpg
    returns for TIMESTAMPTZ columns — already timezone-aware, but belt-
    and-braces for any callers that pass naive)."""
    if ts.tzinfo is None:
        # Assume UTC for naive inputs (matches platform convention).
        from datetime import timezone as _tz
        ts = ts.replace(tzinfo=_tz.utc)
    return ts.astimezone(_LONDON).date()


def collapse_same_day_observations(
    observations: list[TimestampedScore],
) -> list[TimestampedScore]:
    """Collapse same-day-same-domain observations to one per calendar day.

    For each (domain, Europe/London date) bucket, keep the observation with
    the highest raw_score. Ties broken by latest timestamp.

    Returns a new list sorted chronologically by the kept observation's
    original extracted_at. Input order is not required to be sorted.
    """
    if not observations:
        return []

    # Group by (domain, london_date) -> best observation.
    best: dict[tuple[str, object], TimestampedScore] = {}
    for obs in observations:
        key = (obs.domain, _to_london_date(obs.extracted_at))
        incumbent = best.get(key)
        if (
            incumbent is None
            or obs.raw_score > incumbent.raw_score
            or (
                obs.raw_score == incumbent.raw_score
                and obs.extracted_at > incumbent.extracted_at
            )
        ):
            best[key] = obs

    return sorted(best.values(), key=lambda o: o.extracted_at)


def is_consecutive_day_ftp(
    daily: list[TimestampedScore],
    upper_bound: int,
    window: int = 2,
) -> bool:
    """FTP fires when `window` CONSECUTIVE calendar days all have
    raw_score >= upper_bound. Input must be collapsed-by-day (one
    observation per calendar day) and sorted chronologically — use
    collapse_same_day_observations first.

    window=2 matches the legacy "2 consecutive calls" rule but interpreted
    over calendar days per PLAN.md Phase 2.5 Q2. A 5-calendar-day streak
    with a one-day gap does not fire.
    """
    if len(daily) < window:
        return False
    # Scan for `window` consecutive calendar days where every score is
    # at-or-above upper_bound. "Consecutive" means date delta of exactly
    # one day between adjacent entries.
    for i in range(len(daily) - window + 1):
        run = daily[i : i + window]
        if not all(o.raw_score >= upper_bound for o in run):
            continue
        dates = [_to_london_date(o.extracted_at) for o in run]
        ok = True
        for d_prev, d_next in zip(dates, dates[1:]):
            if (d_next - d_prev).days != 1:
                ok = False
                break
        if ok:
            return True
    return False

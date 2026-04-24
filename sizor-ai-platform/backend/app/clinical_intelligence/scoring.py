"""Scoring helpers for clinical intelligence.

Three functions:
  - score_0_10_to_0_4: categorical mapping (landed in Phase 1).
  - score_patient_domain: per-domain classification — replaces the
    dead score_domain/ScoreResult that previously lived here, keyed
    to the Pydantic types in clinical_intelligence.models.
  - compute_overall_call_status: single GREEN/AMBER/RED band for one
    call, combining Red Flag override, Double-Amber rule, and the
    live CallRiskAssessment band.

Domain status categories (from the docstring in the legacy
clinical_intelligence.py module; the call-status logic hinges on these):
    0                                -> resolved
    score <= expected                -> expected   (on track)
    expected < score <= upper_bound  -> monitor    (above expected, watchful)
    upper_bound < score < 4          -> expedite   (above upper_bound)
    score == 4                       -> escalate   (emergency)
"""
from __future__ import annotations

from .models import (
    DomainClassification,
    DomainScore,
    DomainTrajectoryEntry,
    DomainTrend,
    EscalationTier,
    OverallCallStatus,
    RedFlagCategory,
    RiskBand,
)


# ======================================================================
# Categorical 0-10 -> 0-4 mapping (Phase 1, unchanged)
# ======================================================================

def score_0_10_to_0_4(val: float | int | None) -> int | None:
    """Categorical mapping from 0-10 generic score to 0-4 domain score.

    Replaces ``round(val * 0.4)``. Linear scaling drops raw=1 to 0 ("none"),
    erasing a mild-symptom signal; categorical preserves it. None -> None
    (silent domain). Non-numeric / out-of-range inputs are clamped after
    a float coerce; unparseable inputs return None.

    Mapping: 0 -> 0 | 1-3 -> 1 | 4-6 -> 2 | 7-8 -> 3 | 9-10 -> 4
    """
    if val is None:
        return None
    try:
        v = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    v = max(0, min(10, v))
    if v == 0:
        return 0
    if v <= 3:
        return 1
    if v <= 6:
        return 2
    if v <= 8:
        return 3
    return 4


# ======================================================================
# Per-domain classification
# ======================================================================

def score_patient_domain(
    current: DomainScore,
    prior_scores: list[DomainScore],
    trajectory: DomainTrajectoryEntry,
) -> DomainClassification:
    """Classify one domain on one call against the pathway+day trajectory.

    Ports the logic from the deleted clinical/scoring.py::score_domain to
    the new Pydantic types:
      - Trajectory trend from the most recent prior score.
      - FTP flag: score at-or-above upper_bound on two consecutive calls.
      - Escalation tier from score and trajectory.

    prior_scores must be chronological with the most recent last.
    """
    score = current.raw_score
    expected = trajectory.expected_score
    upper_bound = trajectory.upper_bound_score
    above_upper = score > upper_bound

    if not prior_scores:
        trend = DomainTrend.INSUFFICIENT_DATA
    else:
        last = prior_scores[-1].raw_score
        if score < last:
            trend = DomainTrend.IMPROVING
        elif score == last:
            trend = DomainTrend.STABLE
        else:
            trend = DomainTrend.DETERIORATING

    ftp_flag = (
        len(prior_scores) >= 2
        and score >= upper_bound
        and all(p.raw_score >= upper_bound for p in prior_scores[-2:])
    )

    if score == 4:
        tier = EscalationTier.EMERGENCY_999
        flag = True
    elif score == 3:
        tier = EscalationTier.SAME_DAY
        flag = True
    elif above_upper and trend == DomainTrend.DETERIORATING:
        tier = EscalationTier.URGENT_GP
        flag = True
    elif ftp_flag:
        tier = EscalationTier.NEXT_CALL
        flag = True
    else:
        tier = EscalationTier.NONE
        flag = False

    return DomainClassification(
        domain=current.domain,
        score=score,
        expected=expected,
        upper_bound=upper_bound,
        above_upper_bound=above_upper,
        trajectory=trend,
        ftp_flag=ftp_flag,
        escalation_flag=flag,
        escalation_tier=tier,
        nice_basis=trajectory.nice_source,
    )


# ======================================================================
# Overall call status
# ======================================================================

def _is_monitor_status(c: DomainClassification) -> bool:
    """Monitor = score above expected but within upper_bound (and not 4).

    See the status-category docstring at the top of this module. The
    Double-Amber rule triggers on counts of this status, per the approved
    Q2 answer: 'STRICT — any 2 Monitor domains -> Expedite regardless of
    clinical cluster.'
    """
    return c.expected < c.score <= c.upper_bound and c.score < 4


def compute_overall_call_status(
    classifications: list[DomainClassification],
    red_flags_detected: list[RedFlagCategory],
    call_assessment_band: RiskBand,
) -> OverallCallStatus:
    """Decide the single band for one call.

    Rule order (first match wins):
      1. Red Flag override: any domain with escalation_flag True OR any
         entry in red_flags_detected -> RED.
      2. Double-Amber: 2+ domains in 'monitor' status (above expected,
         within upper_bound, not yet 4) -> AMBER with reason 'double_amber'.
         Deliberately stricter than the CallRiskAssessment band alone —
         the live scorer can rate this GREEN when two domains are quietly
         drifting together. Q2 confirmed: no clinical-cluster gating in v1.
      3. Default: use the CallRiskAssessment band (the live
         compute_risk_score output).

    contributing identifies which domains drove the decision. For the
    red-flag path, it lists domain names whose escalation_flag fired; if
    the override came purely from a system-level red_flags_detected entry,
    contributing is the stringified red-flag category values.
    """
    # Rule 1: Red Flag override.
    escalation_domains = [c.domain for c in classifications if c.escalation_flag]
    if escalation_domains or red_flags_detected:
        contributing = (
            escalation_domains
            if escalation_domains
            else [rf.value for rf in red_flags_detected]
        )
        return OverallCallStatus(
            band=RiskBand.RED,
            primary_reason="red_flag_override",
            contributing=contributing,
        )

    # Rule 2: Double-Amber.
    monitor_domains = [c.domain for c in classifications if _is_monitor_status(c)]
    if len(monitor_domains) >= 2:
        return OverallCallStatus(
            band=RiskBand.AMBER,
            primary_reason="double_amber",
            contributing=monitor_domains,
        )

    # Rule 3: fall through to live CallRiskAssessment band.
    return OverallCallStatus(
        band=call_assessment_band,
        primary_reason="call_risk_assessment_band",
        contributing=[],
    )

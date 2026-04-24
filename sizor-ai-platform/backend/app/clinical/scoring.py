"""Domain scoring logic — compares actual scores to benchmark expectations."""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass


def score_0_10_to_0_4(val: float | int | None) -> int | None:
    """Categorical mapping from 0-10 generic score to 0-4 domain score.

    Replaces ``round(val * 0.4)``. Linear scaling drops raw=1 to 0 ("none"),
    erasing a mild-symptom signal; categorical preserves it. None → None
    (silent domain). Non-numeric / out-of-range inputs are clamped after
    a float coerce; unparseable inputs return None.

    Mapping: 0 → 0 | 1-3 → 1 | 4-6 → 2 | 7-8 → 3 | 9-10 → 4
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


@dataclass
class ScoreResult:
    domain: str
    score: int
    expected_score: int
    upper_bound_score: int
    above_upper_bound: bool
    trajectory: str  # improving/stable/deteriorating/insufficient_data
    ftp_flag: bool
    escalation_flag: bool
    escalation_tier: Optional[str]  # 999/same_day/urgent_gp/next_call/None
    nice_basis: Optional[str]


def score_domain(
    domain: str,
    score: int,
    expected_score: int,
    upper_bound_score: int,
    prior_scores: list[int] | None = None,
    nice_source: str = "",
) -> ScoreResult:
    above_upper = score > upper_bound_score

    # Trajectory from prior scores
    trajectory = "insufficient_data"
    ftp = False
    if prior_scores and len(prior_scores) >= 1:
        if score < prior_scores[-1]:
            trajectory = "improving"
        elif score == prior_scores[-1]:
            trajectory = "stable"
        else:
            trajectory = "deteriorating"

        # FTP: score >= upper_bound on 2 consecutive calls
        if len(prior_scores) >= 2 and score >= upper_bound_score and all(p >= upper_bound_score for p in prior_scores[-2:]):
            ftp = True

    # Escalation tier
    escalation_tier = None
    escalation_flag = False
    if score == 4:
        escalation_flag = True
        escalation_tier = "999"
    elif score == 3:
        escalation_flag = True
        escalation_tier = "same_day"
    elif above_upper and trajectory == "deteriorating":
        escalation_flag = True
        escalation_tier = "urgent_gp"
    elif ftp:
        escalation_flag = True
        escalation_tier = "next_call"

    return ScoreResult(
        domain=domain,
        score=score,
        expected_score=expected_score,
        upper_bound_score=upper_bound_score,
        above_upper_bound=above_upper,
        trajectory=trajectory,
        ftp_flag=ftp,
        escalation_flag=escalation_flag,
        escalation_tier=escalation_tier,
        nice_basis=nice_source,
    )

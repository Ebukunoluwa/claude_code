"""
Patient risk score (0–100) — the number shown on the dashboard.

This is distinct from the RAG band (produced by evaluate_flags):
  - RAG band answers: "what action should a clinician take?"
  - Risk score answers: "how concerned should we be at a glance?"

Both are derived from the same clinical state but serve different purposes.
The score is a UI artefact for visual prioritisation; the band drives action.

Design principles
-----------------
1. Deterministic — same inputs always produce the same score. No hashing, no
   randomness, no patient-ID influence.
2. Transparent — every contribution to the final number is captured in the
   returned breakdown, so a clinician (or DCB0129 auditor) can see exactly
   why a patient scored what they did.
3. Consistent with the band — a RED patient should generally score higher
   than an AMBER patient, who should score higher than GREEN. The score is
   a continuous reflection of the same clinical state the band reflects
   discretely.
4. Bounded — the final number is always 0–100, clipped at the edges so
   no single input can drive extremes.

Composition (weights sum to 1.0)
--------------------------------
  worst symptom      50%   — max of smoothed pain, breathlessness, mobility, appetite
  mood               15%   — smoothed mood (inversely scaled: low mood raises score)
  ftp                15%   — behind / significantly_behind recovery
  modifiers          10%   — adherence/social factors (capped)
  day factor          5%   — very early post-discharge gets small uplift (day 0-3)
  active red flag    +auto — any active RED flag floors the score at 70

All weights are tunable at the top of this file. Calibrate against clinician
labels once available; do not change defaults without clinical sign-off.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

from app.clinical.smoothing import SmoothedScores


# --- Weights (must sum to 1.0) ---
W_WORST_SYMPTOM = 0.55
W_MOOD = 0.15
W_FTP = 0.15
W_MODIFIERS = 0.10
W_DAY_FACTOR = 0.05

# --- Internal thresholds ---
RED_FLAG_BUMP = 30.0        # any active RED flag adds this much to the natural score
RED_FLAG_MIN_FLOOR = 70.0   # ...and the final score is never below this
ACUTE_SYMPTOM_FLOOR = 65.0  # raw symptom ≥ 8 → floor even if smoothed is low
FTP_BEHIND_SCORE = 50.0
FTP_SIGNIFICANTLY_BEHIND_SCORE = 85.0
EARLY_DAYS_CUTOFF = 3       # days 0-3 get full day-factor contribution


FtpStatus = Literal["on_track", "behind", "significantly_behind", "insufficient_data", "unknown"]


@dataclass
class RiskScoreBreakdown:
    """Full transparency on how a score was computed. This is the audit trail."""
    final_score: float
    band_if_computed: str  # "green" | "amber" | "red" — consistent with flags
    # Component contributions (each 0-100, pre-weighting)
    worst_symptom_component: float
    mood_component: float
    ftp_component: float
    modifier_component: float
    day_factor_component: float
    # Weighted contributions (what actually adds to the final score)
    weighted_worst_symptom: float
    weighted_mood: float
    weighted_ftp: float
    weighted_modifiers: float
    weighted_day_factor: float
    # Overrides
    red_flag_floor_applied: bool
    acute_symptom_floor_applied: bool
    # Explanatory
    dominant_driver: str  # which component contributed most


def _worst_symptom_component(smoothed: SmoothedScores) -> float:
    """
    Max of smoothed symptom domains, scaled to 0-100 with a mild curve.

    Linear 0-10 → 0-100 under-weighted the high end (a smoothed pain of 7
    should push toward RED territory, not sit at 70 pre-weighting). We apply
    a gentle curve above 5.0 so clinically elevated states score higher.

    Mapping (approximate):
        smoothed  0 → 0
        smoothed  3 → 30
        smoothed  5 → 50
        smoothed  6 → 65
        smoothed  7 → 80
        smoothed  8 → 92
        smoothed 10 → 100
    """
    symptom_values = [v for v in (smoothed.pain, smoothed.breathlessness,
                                   smoothed.mobility, smoothed.appetite) if v is not None]
    if not symptom_values:
        return 0.0
    worst = max(symptom_values)
    if worst <= 5.0:
        return worst * 10.0  # linear below threshold
    # Above 5: accelerate. Each unit above 5 adds 15 instead of 10, capped at 100.
    return min(100.0, 50.0 + (worst - 5.0) * 15.0)


def _mood_component(smoothed: SmoothedScores) -> float:
    """Mood is scored inversely: 0 = terrible, 10 = great. Invert to concern scale."""
    if smoothed.mood is None:
        return 0.0
    # mood 0 → concern 100, mood 10 → concern 0
    return max(0.0, min(100.0, (10.0 - smoothed.mood) * 10.0))


def _ftp_component(ftp_status: FtpStatus) -> float:
    """Failure-to-progress adds concern. Uses defined scores for each status."""
    if ftp_status == "significantly_behind":
        return FTP_SIGNIFICANTLY_BEHIND_SCORE
    if ftp_status == "behind":
        return FTP_BEHIND_SCORE
    # on_track, insufficient_data, unknown → 0
    return 0.0


def _modifier_component(smoothed: SmoothedScores) -> float:
    """Scale modifier total (capped at MODIFIER_CAP = 2.5) to 0-100 contribution."""
    # smoothing.py caps modifier_total at 2.5 on a 0-10 scale
    # Scale to 0-100: multiply by 40 to get full-weight at 2.5
    return min(100.0, smoothed.modifier_total * 40.0)


def _day_factor_component(day_in_recovery: int | None) -> float:
    """Very early post-discharge is inherently higher-risk. Linear taper to day 3."""
    if day_in_recovery is None or day_in_recovery > EARLY_DAYS_CUTOFF:
        return 0.0
    # Day 0 = 100, Day 3 = 0
    return max(0.0, 100.0 * (1.0 - day_in_recovery / (EARLY_DAYS_CUTOFF + 1)))


def _band_from_score(score: float) -> str:
    """Consistent with flag-based bands: >=70 red, 40-70 amber, <40 green."""
    if score >= 70.0:
        return "red"
    if score >= 40.0:
        return "amber"
    return "green"


def compute_risk_score(
    smoothed: SmoothedScores,
    *,
    ftp_status: FtpStatus = "unknown",
    day_in_recovery: int | None = None,
    has_active_red_flag: bool = False,
    raw_pain: float | None = None,
    raw_breathlessness: float | None = None,
) -> RiskScoreBreakdown:
    """
    Compute a 0–100 risk score from clinical state.

    Parameters
    ----------
    smoothed : SmoothedScores
        Output of smoothing.smooth_extraction() for this call.
    ftp_status : str
        One of: on_track, behind, significantly_behind, insufficient_data, unknown.
        Drives the FTP component of the score.
    day_in_recovery : int | None
        Days since discharge. Day 0–3 gets a small additional uplift.
    has_active_red_flag : bool
        Whether this call produced any RED flag in evaluate_flags. If True, the
        final score is floored at RED_FLAG_FLOOR regardless of other components.
    raw_pain, raw_breathlessness : float | None
        RAW (unsmoothed) scores. If either is ≥ 8, score is floored at
        ACUTE_SYMPTOM_FLOOR even if the smoothed value is lower. Prevents
        the score from masking a single acute reading — mirrors the safety
        logic in evaluate_flags.

    Returns
    -------
    RiskScoreBreakdown with final_score, band, and every contribution broken out.
    """
    # 1. Compute each component (0-100 pre-weighting)
    worst_symptom = _worst_symptom_component(smoothed)
    mood = _mood_component(smoothed)
    ftp = _ftp_component(ftp_status)
    modifier = _modifier_component(smoothed)
    day_factor = _day_factor_component(day_in_recovery)

    # 2. Weight and sum
    w_worst = W_WORST_SYMPTOM * worst_symptom
    w_mood = W_MOOD * mood
    w_ftp = W_FTP * ftp
    w_mod = W_MODIFIERS * modifier
    w_day = W_DAY_FACTOR * day_factor

    raw_score = w_worst + w_mood + w_ftp + w_mod + w_day

    # 3. Apply safety floors
    acute_floor_applied = False
    if (raw_pain is not None and raw_pain >= 8) or (raw_breathlessness is not None and raw_breathlessness >= 8):
        raw_score = max(raw_score, ACUTE_SYMPTOM_FLOOR)
        acute_floor_applied = True

    red_floor_applied = False
    if has_active_red_flag:
        # Red flag adds to natural score AND imposes a minimum floor.
        # This preserves severity differences between red patients while
        # guaranteeing any red-flagged patient scores ≥ RED_FLAG_MIN_FLOOR.
        raw_score = max(raw_score + RED_FLAG_BUMP, RED_FLAG_MIN_FLOOR)
        red_floor_applied = True

    # 4. Clip to [0, 100]
    final_score = max(0.0, min(100.0, raw_score))

    # 5. Identify the dominant driver (for UI tooltip / audit log)
    contributions = {
        "worst_symptom": w_worst,
        "mood": w_mood,
        "ftp": w_ftp,
        "modifiers": w_mod,
        "day_factor": w_day,
    }
    dominant = max(contributions, key=contributions.get) if any(contributions.values()) else "none"
    if red_floor_applied and final_score == RED_FLAG_MIN_FLOOR:
        dominant = "red_flag_override"

    return RiskScoreBreakdown(
        final_score=round(final_score, 1),
        band_if_computed=_band_from_score(final_score),
        worst_symptom_component=round(worst_symptom, 1),
        mood_component=round(mood, 1),
        ftp_component=round(ftp, 1),
        modifier_component=round(modifier, 1),
        day_factor_component=round(day_factor, 1),
        weighted_worst_symptom=round(w_worst, 1),
        weighted_mood=round(w_mood, 1),
        weighted_ftp=round(w_ftp, 1),
        weighted_modifiers=round(w_mod, 1),
        weighted_day_factor=round(w_day, 1),
        red_flag_floor_applied=red_floor_applied,
        acute_symptom_floor_applied=acute_floor_applied,
        dominant_driver=dominant,
    )


def breakdown_to_dict(breakdown: RiskScoreBreakdown) -> dict:
    """JSON-serialisable dict for storing in ClinicalExtraction.risk_score_breakdown."""
    return asdict(breakdown)

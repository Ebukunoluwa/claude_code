"""
Call-to-call score smoothing and modifier logic.

Addresses the volatility problem: a single call (e.g. a missed med report) should
not flip a stable patient to RED. This module provides:

  1. EWMA smoothing of domain scores across consecutive calls
  2. Capped modifier bumps for non-symptom risk factors (adherence, social)

Design notes
------------
- Hard RED thresholds (e.g. pain >= 8) remain as RAW-score triggers. A single
  acute reading must still fire a red flag — we do not want smoothing to mask
  an acute safety signal.
- Smoothing is applied to the AMBER band logic, where brittleness is the
  actual clinical problem.
- Scale: 0–10 (matching ClinicalExtraction columns). Do not change this without
  coordinating with the extraction prompt and the frontend.
- Adherence/social factors are MODIFIERS (capped bumps on an aggregate concern
  score), not symptom scores. They should never, on their own, flip a stable
  patient to RED — consistent with the guidance in scoring_v2/README.md.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Tunables. Calibrate against clinician-labelled data once available. ---
EWMA_LAMBDA = 0.3            # lower = more smoothing
AMBER_THRESHOLD = 6.0        # smoothed domain score >= this → AMBER-worthy
MOOD_LOW_THRESHOLD = 3.0     # mood is scored inversely (lower = worse)
MODIFIER_CAP = 2.5           # max total bump added to a smoothed score
ADHERENCE_BUMP_NON_CRITICAL = 1.0
ADHERENCE_BUMP_CRITICAL = 2.0
MISSED_PREVIOUS_CALL_BUMP = 1.0


@dataclass
class SmoothedScores:
    """The smoothed state used for AMBER band logic and trajectory tracking."""
    pain: float | None
    breathlessness: float | None
    mobility: float | None
    appetite: float | None
    mood: float | None
    max_smoothed: float  # highest of the symptom domains post-smoothing
    modifier_total: float
    modifier_detail: dict[str, float]
    lam: float


def ewma(current: float | None, prior: float | None, lam: float = EWMA_LAMBDA) -> float | None:
    """
    Exponentially weighted moving average.

    - First call (no prior): returns current (seeds the series).
    - Missing current score: returns prior (don't erase history on a silent call).
    - Both missing: returns None.
    """
    if current is None and prior is None:
        return None
    if current is None:
        return prior
    if prior is None:
        return float(current)
    return lam * float(current) + (1 - lam) * float(prior)


def compute_modifiers(
    adherence: bool | None,
    critical_medication: bool = False,
    missed_previous_call: bool = False,
) -> tuple[float, dict[str, float]]:
    """
    Additive, capped bumps for non-symptom risk factors.

    Returns (total, detail) where detail shows which modifiers fired.
    `adherence=False` means patient did NOT take meds as prescribed.
    `adherence=None` means unknown — we do not penalise unknowns.
    """
    detail: dict[str, float] = {}

    if adherence is False:
        detail["adherence_lapse"] = (
            ADHERENCE_BUMP_CRITICAL if critical_medication else ADHERENCE_BUMP_NON_CRITICAL
        )
    if missed_previous_call:
        detail["missed_previous_call"] = MISSED_PREVIOUS_CALL_BUMP

    total = sum(detail.values())
    if total > MODIFIER_CAP:
        scale = MODIFIER_CAP / total
        detail = {k: round(v * scale, 2) for k, v in detail.items()}
        total = MODIFIER_CAP

    return total, detail


def smooth_extraction(
    extraction: dict,
    prior_smoothed: dict | None,
    *,
    critical_medication: bool = False,
    missed_previous_call: bool = False,
    lam: float = EWMA_LAMBDA,
) -> SmoothedScores:
    """
    Top-level entry. Takes the current extraction dict and prior smoothed state
    (loaded from DB, or None on first call) and returns a SmoothedScores.

    Prior smoothed state shape (JSON-serialisable dict):
        {"pain": 2.3, "breathlessness": 1.1, "mobility": 4.0,
         "appetite": 3.2, "mood": 5.8}
    """
    prior = prior_smoothed or {}

    pain = ewma(extraction.get("pain_score"), prior.get("pain"), lam)
    breathlessness = ewma(extraction.get("breathlessness_score"), prior.get("breathlessness"), lam)
    mobility = ewma(extraction.get("mobility_score"), prior.get("mobility"), lam)
    appetite = ewma(extraction.get("appetite_score"), prior.get("appetite"), lam)
    mood = ewma(extraction.get("mood_score"), prior.get("mood"), lam)

    # For AMBER aggregate logic: max across symptom domains where higher = worse.
    # Mood is excluded because it's scored inversely (lower = worse).
    symptom_domains = [pain, breathlessness, mobility, appetite]
    max_smoothed = max((s for s in symptom_domains if s is not None), default=0.0)

    modifier_total, modifier_detail = compute_modifiers(
        adherence=extraction.get("medication_adherence"),
        critical_medication=critical_medication,
        missed_previous_call=missed_previous_call,
    )

    return SmoothedScores(
        pain=pain,
        breathlessness=breathlessness,
        mobility=mobility,
        appetite=appetite,
        mood=mood,
        max_smoothed=max_smoothed,
        modifier_total=modifier_total,
        modifier_detail=modifier_detail,
        lam=lam,
    )


def to_persistable_dict(smoothed: SmoothedScores) -> dict:
    """Shape to store in ClinicalExtraction.smoothed_scores (JSONB column)."""
    return {
        "pain": smoothed.pain,
        "breathlessness": smoothed.breathlessness,
        "mobility": smoothed.mobility,
        "appetite": smoothed.appetite,
        "mood": smoothed.mood,
        "modifier_total": smoothed.modifier_total,
        "modifier_detail": smoothed.modifier_detail,
        "lam": smoothed.lam,
    }

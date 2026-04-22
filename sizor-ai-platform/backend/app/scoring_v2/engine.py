"""
Deterministic risk scoring engine.

Takes a CallExtraction + PatientHistory → produces a RiskScore.
No LLM calls. No randomness. Pure function of inputs.

The maths (from the spec):
    S_t = w_state * State_t + w_trajectory * Trajectory_t + Modifiers_t

    State_t    = 25 * Σ α_i * d_i         (domain scores weighted, normalised to 0-100)
    EWMA_t     = λ * State_t + (1-λ) * EWMA_{t-1}
    Trajectory = max(0, EWMA_t - E(pathway, day))
    Modifiers  = capped sum of adherence + social + missed-call penalties
    Red flags  = deterministic override → final = 100, band = RED
"""
from __future__ import annotations

from .config import PathwayConfig, ScoringConfig, config_hash, expected_score_at_day
from .models import (
    CallExtraction,
    PatientHistory,
    RedFlagType,
    RiskBand,
    RiskScore,
    ScoringBreakdown,
)


# --- Component calculations ---

def compute_state_score(extraction: CallExtraction, pathway: PathwayConfig) -> float:
    """State_t = 25 * Σ α_i * d_i, producing a 0–100 score."""
    obs_by_domain = {o.domain: o.raw_score for o in extraction.domain_observations}
    weighted = 0.0
    for weight in pathway.domains:
        d = obs_by_domain.get(weight.domain, 0)  # missing domain → 0, conservative
        weighted += weight.weight * d
    return min(100.0, 25.0 * weighted)


def update_ewma(current_state: float, prior_ewma: float | None, lam: float) -> float:
    """λ * current + (1-λ) * prior. On first call, seed with current."""
    if prior_ewma is None:
        return current_state
    return lam * current_state + (1 - lam) * prior_ewma


def compute_trajectory_score(smoothed_state: float, expected: float) -> float:
    """How far above expected recovery curve. Non-negative."""
    return max(0.0, smoothed_state - expected)


def compute_modifiers(extraction: CallExtraction, cap: float) -> tuple[float, dict[str, float]]:
    """Additive bumps for risk factors. Returns (total, breakdown)."""
    detail: dict[str, float] = {}

    # Medication adherence
    if not extraction.adherence.medication_taken_as_prescribed:
        base = 15.0 if extraction.adherence.critical_medication else 7.0
        # Scale mildly with number of missed doses, capped
        dose_bump = min(5.0, extraction.adherence.missed_doses_reported * 2.0)
        detail["adherence_lapse"] = base + dose_bump

    # Missed previous call — lost visibility is itself risk
    if extraction.social.missed_previous_call:
        detail["missed_previous_call"] = 10.0

    # Social isolation baseline
    if extraction.social.lives_alone and not extraction.social.has_support_contact:
        detail["social_isolation"] = 5.0

    total = sum(detail.values())
    # Cap applied proportionally so detail stays honest
    if total > cap:
        scale = cap / total
        detail = {k: round(v * scale, 2) for k, v in detail.items()}
        total = cap

    return total, detail


def detect_red_flag_override(
    extraction: CallExtraction, pathway: PathwayConfig
) -> tuple[bool, list[RedFlagType]]:
    """Hard red flags bypass scoring. Returns (triggered, list_of_types)."""
    triggered = [f.type for f in extraction.red_flags]

    # Pathway-specific compound red flags
    # (e.g. post-op: pain ≥3 AND fever AND wound change → PATHWAY_SPECIFIC)
    obs_by_domain = {o.domain: o.raw_score for o in extraction.domain_observations}
    for rule in pathway.compound_red_flags:
        if all(obs_by_domain.get(domain, 0) >= min_score for domain, min_score in rule):
            if RedFlagType.PATHWAY_SPECIFIC not in triggered:
                triggered.append(RedFlagType.PATHWAY_SPECIFIC)
            break

    return len(triggered) > 0, triggered


def band_for(score: float, config: ScoringConfig) -> RiskBand:
    if score >= config.band_red_threshold:
        return RiskBand.RED
    if score >= config.band_amber_threshold:
        return RiskBand.AMBER
    return RiskBand.GREEN


def recommend_action(band: RiskBand, red_flag: bool) -> tuple[str, int]:
    """Returns (human-readable action, next call interval in hours)."""
    if red_flag:
        return ("Immediate clinician review — red flag detected", 0)
    if band == RiskBand.RED:
        return ("Clinician review within 4 hours", 4)
    if band == RiskBand.AMBER:
        return ("Earlier probe call, review within 24 hours", 24)
    return ("Routine monitoring", 72)


# --- Top-level entry point ---

def score_call(
    extraction: CallExtraction,
    history: PatientHistory,
    config: ScoringConfig,
) -> RiskScore:
    """Compute a risk score for one call. Pure function."""
    pathway = config.pathways.get(extraction.pathway)
    if pathway is None:
        raise ValueError(f"Unknown pathway: {extraction.pathway}")

    # 1. Red flag override — short-circuits everything
    red_flag_override, red_flags_triggered = detect_red_flag_override(extraction, pathway)

    # 2. State score (always computed, for audit even on override)
    state = compute_state_score(extraction, pathway)

    # 3. EWMA update
    smoothed = update_ewma(state, history.prior_smoothed_state, config.ewma_lambda)

    # 4. Trajectory vs expected curve
    expected = expected_score_at_day(pathway, extraction.day_post_discharge)
    trajectory = compute_trajectory_score(smoothed, expected)

    # 5. Modifiers
    modifier_total, modifier_detail = compute_modifiers(extraction, config.modifier_cap)

    # 6. Final score
    if red_flag_override:
        final_score = 100.0
        band = RiskBand.RED
    else:
        raw = (
            config.w_state * state
            + config.w_trajectory * trajectory
            + modifier_total
        )
        final_score = min(100.0, max(0.0, raw))
        band = band_for(final_score, config)

    action, next_interval = recommend_action(band, red_flag_override)

    breakdown = ScoringBreakdown(
        state_score=state,
        trajectory_score=trajectory,
        modifier_total=modifier_total,
        modifier_detail=modifier_detail,
        w_state=config.w_state,
        w_trajectory=config.w_trajectory,
        ewma_lambda=config.ewma_lambda,
        expected_score_at_day=expected,
        smoothed_state=smoothed,
        red_flag_override=red_flag_override,
        red_flags_triggered=red_flags_triggered,
        rubric_version=pathway.rubric_version,
        scoring_engine_version=f"{config.engine_version}+{config_hash(config)}",
    )

    return RiskScore(
        patient_id=extraction.patient_id,
        call_id=extraction.call_id,
        call_timestamp=extraction.call_timestamp,
        pathway=extraction.pathway,
        day_post_discharge=extraction.day_post_discharge,
        final_score=final_score,
        band=band,
        breakdown=breakdown,
        recommended_action=action,
        next_call_interval_hours=next_interval,
    )

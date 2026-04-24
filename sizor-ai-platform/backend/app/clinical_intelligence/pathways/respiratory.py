"""Respiratory pathway — J44 (COPD Exacerbation).

Phase 3 status: **J44** complete. No other respiratory pathways in
scope for Phase 3 (J18_PNEUMONIA et al. remain in benchmarks.py but
are outside the 15-pathway active set).

Content sources:
  - Trajectories ported verbatim from benchmarks.py. validation_status
    set to draft on every row.
  - Playbook metadata from monolith PLAYBOOKS.
  - Required Questions and Red Flag Probes net-new for Phase 3.

Decisions during port (not open flags):
  Five upstream red flag codes from the monolith
  (oxygen_saturation_below_88, acute_severe_breathlessness, cyanosis,
  acute_confusion, unable_to_complete_sentences) are each atomic
  single-observation events — no parent_flag_code splitting needed.
  Each becomes one RedFlagProbe with parent_flag_code=None.

  oxygen_saturation probe scopes to "if you have a pulse oximeter"
  because many COPD patients don't have one at home; the four other
  probes cover the symptomatic presentations of hypoxia for those
  who don't.

Primary NICE sources: NG115 (COPD over 16), QS10. Reviewer specialty:
Respiratory physician / COPD specialist nurse.
"""
from ..models import (
    DomainTrajectoryEntry,
    EscalationTier,
    PathwayPlaybook,
    RedFlagCategory,
    RedFlagProbe,
    RequiredQuestion,
)


_DRAFT = "draft_awaiting_clinical_review"


# ═══════════════════════════════════════════════════════════════════════
# J44 — COPD Exacerbation
# ═══════════════════════════════════════════════════════════════════════

J44_PLAYBOOK = PathwayPlaybook(
    opcs_code="J44",
    label="COPD Exacerbation",
    category="respiratory",
    nice_ids=["NG115", "QS10"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "breathlessness_score",
        "inhaler_adherence_and_technique",
        "steroid_and_antibiotic_course",
        "oxygen_saturation",
        "smoking_cessation",
        "pulmonary_rehab_referral",
    ],
    red_flag_codes=[
        "oxygen_saturation_below_88",
        "acute_severe_breathlessness",
        "cyanosis",
        "acute_confusion",
        "unable_to_complete_sentences",
    ],
    validation_status=_DRAFT,
)


def _traj(
    domain: str, day: int, expected: int, upper: int, state: str, nice: str,
) -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code="J44",
        domain=domain,
        day_range_start=day,
        day_range_end=day,
        expected_score=expected,
        upper_bound_score=upper,
        expected_state=state,
        nice_source=nice,
        validation_status=_DRAFT,
    )


J44_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # breathlessness_score — NG115
    _traj("breathlessness_score",  1, 2, 3, "Breathlessness improving post-exacerbation", "NG115"),
    _traj("breathlessness_score",  3, 2, 2, "Reducing breathlessness", "NG115"),
    _traj("breathlessness_score",  7, 2, 2, "Should be at pre-exacerbation baseline", "NG115"),
    _traj("breathlessness_score", 14, 1, 2, "Stable breathlessness", "NG115"),
    _traj("breathlessness_score", 21, 1, 1, "At or near baseline", "NG115"),
    _traj("breathlessness_score", 28, 1, 1, "Baseline achieved", "NG115"),
    _traj("breathlessness_score", 42, 1, 1, "Stable", "NG115"),
    _traj("breathlessness_score", 60, 1, 1, "Stable — chronic disease management", "NG115"),

    # inhaler_adherence_and_technique — NG115
    # CLINICAL_REVIEW_NEEDED: inhaler technique is visually assessed in
    # practice. Voice agent can only ask about self-reported adherence
    # and whether a clinician has recently checked technique. Reviewer
    # to confirm whether trust wants a separate home-visit or video
    # technique check flagged from this pathway.
    _traj("inhaler_adherence_and_technique",  1, 1, 2, "Inhaler technique reviewed", "NG115"),
    _traj("inhaler_adherence_and_technique",  3, 1, 2, "Technique and adherence", "NG115"),
    _traj("inhaler_adherence_and_technique",  7, 1, 1, "Adherent and correct technique", "NG115"),
    _traj("inhaler_adherence_and_technique", 14, 1, 1, "Adherent", "NG115"),
    _traj("inhaler_adherence_and_technique", 21, 1, 1, "Adherent", "NG115"),
    _traj("inhaler_adherence_and_technique", 28, 1, 1, "Adherent", "NG115"),
    _traj("inhaler_adherence_and_technique", 42, 1, 1, "Adherent", "NG115"),
    _traj("inhaler_adherence_and_technique", 60, 1, 1, "Adherent — ongoing", "NG115"),

    # steroid_and_antibiotic_course — NG115
    _traj("steroid_and_antibiotic_course",  1, 1, 2, "Prednisolone 5-day course commenced", "NG115"),
    _traj("steroid_and_antibiotic_course",  3, 1, 1, "Day 3 of steroid course", "NG115"),
    _traj("steroid_and_antibiotic_course",  7, 0, 1, "Course completed by day 5-7", "NG115"),
    _traj("steroid_and_antibiotic_course", 14, 0, 0, "Course completed", "NG115"),
    _traj("steroid_and_antibiotic_course", 21, 0, 0, "Completed", "NG115"),
    _traj("steroid_and_antibiotic_course", 28, 0, 0, "Completed", "NG115"),
    _traj("steroid_and_antibiotic_course", 42, 0, 0, "Completed", "NG115"),
    _traj("steroid_and_antibiotic_course", 60, 0, 0, "Completed", "NG115"),

    # oxygen_saturation — NG115
    # CLINICAL_REVIEW_NEEDED: 88% SpO2 threshold is the NG115 COPD target.
    # Reviewer to confirm whether trust uses 88% or 92% for the specific
    # patient cohort (some trusts use higher threshold for non-CO2-
    # retaining COPD patients). Also confirm whether absence of a pulse
    # oximeter at home downgrades this domain's scoreability.
    _traj("oxygen_saturation",  1, 1, 2, "SpO2 monitoring — target >=88% COPD", "NG115"),
    _traj("oxygen_saturation",  3, 1, 2, "Monitor SpO2", "NG115"),
    _traj("oxygen_saturation",  7, 1, 1, "Stable SpO2", "NG115"),
    _traj("oxygen_saturation", 14, 1, 1, "Stable", "NG115"),
    _traj("oxygen_saturation", 21, 1, 1, "Stable", "NG115"),
    _traj("oxygen_saturation", 28, 1, 1, "Stable", "NG115"),
    _traj("oxygen_saturation", 42, 1, 1, "Stable", "NG115"),
    _traj("oxygen_saturation", 60, 1, 1, "Stable", "NG115"),

    # smoking_cessation — NG115
    _traj("smoking_cessation",  1, 1, 2, "Cessation offered at every opportunity", "NG115"),
    _traj("smoking_cessation",  3, 1, 2, "Support offered", "NG115"),
    _traj("smoking_cessation",  7, 1, 2, "Cessation ongoing", "NG115"),
    _traj("smoking_cessation", 14, 1, 1, "Engaged with cessation support", "NG115"),
    _traj("smoking_cessation", 21, 1, 1, "Cessation maintained", "NG115"),
    _traj("smoking_cessation", 28, 1, 1, "Cessation maintained", "NG115"),
    _traj("smoking_cessation", 42, 1, 1, "Cessation maintained", "NG115"),
    _traj("smoking_cessation", 60, 1, 1, "Cessation maintained", "NG115"),

    # pulmonary_rehab_referral — NG115
    # CLINICAL_REVIEW_NEEDED: this trajectory assumes near-100% referral
    # uptake and attendance. In practice PR dropout/non-attendance is
    # high (~30-40% in some NHS datasets). Reviewer to calibrate
    # expected/upper_bound values — current draft may be too optimistic
    # and produce spurious "expedite" bands for real-world non-attendance.
    _traj("pulmonary_rehab_referral",  1, 1, 2, "Referral made to PR", "NG115"),
    _traj("pulmonary_rehab_referral",  3, 1, 2, "Awaiting start", "NG115"),
    _traj("pulmonary_rehab_referral",  7, 1, 1, "PR programme starting", "NG115"),
    _traj("pulmonary_rehab_referral", 14, 1, 1, "Attending PR", "NG115"),
    _traj("pulmonary_rehab_referral", 21, 1, 1, "Attending PR", "NG115"),
    _traj("pulmonary_rehab_referral", 28, 1, 1, "Ongoing PR", "NG115"),
    _traj("pulmonary_rehab_referral", 42, 1, 1, "Ongoing PR", "NG115"),
    _traj("pulmonary_rehab_referral", 60, 0, 1, "Programme completing", "NG115"),
]


def _rq(
    domain: str, text: str, bands: list[tuple[int, int]], nice: str,
) -> RequiredQuestion:
    return RequiredQuestion(
        opcs_code="J44",
        domain=domain,
        question_text=text,
        required=True,
        day_ranges=bands,
        validation_status=_DRAFT,
    )


J44_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # All-window breathlessness screen (chronic baseline tracking)
    _rq(
        "breathlessness_score",
        "How breathless are you today compared to before this flare-up — back to your usual, worse, or somewhere in between?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG115 §1.2",
    ),

    # Day 1-3: drug course underway
    _rq(
        "steroid_and_antibiotic_course",
        "Are you still taking the steroid tablets — what day are you on, and have you had any side effects?",
        [(1, 3), (4, 7)],
        "NG115 §1.4",
    ),
    _rq(
        "inhaler_adherence_and_technique",
        "Are you using all your inhalers as prescribed — and has anyone recently checked you're using them correctly?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG115 §1.3",
    ),
    _rq(
        "oxygen_saturation",
        "If you have a pulse oximeter at home, what reading have you been getting?",
        [(1, 3), (4, 7), (8, 14)],
        "NG115 §1.5",
    ),

    # Day 4-7: course completion, self-management plan
    _rq(
        "steroid_and_antibiotic_course",
        "Have you finished the steroid course, and do you know what to do if you feel worse again?",
        [(4, 7), (8, 14)],
        "NG115 §1.4",
    ),

    # Day 8-14 onwards: PR engagement
    _rq(
        "pulmonary_rehab_referral",
        "Have you heard back about pulmonary rehab — or started the programme yet?",
        [(8, 14), (15, 28)],
        "NG115 §1.6",
    ),
    _rq(
        "pulmonary_rehab_referral",
        "How are you getting on with pulmonary rehab — managing to attend the sessions?",
        [(15, 28), (29, 60)],
        "NG115 §1.6",
    ),

    # All-window smoking cessation (non-judgmental, every call)
    _rq(
        "smoking_cessation",
        "How are you getting on with cigarettes — still off them, or having a few? No judgment either way.",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG115 §1.7",
    ),

    # Coverage check — inhaler technique re-assessment by GP/nurse
    _rq(
        "inhaler_adherence_and_technique",
        "Has your GP or practice nurse had a look at your inhaler technique since you got home from hospital?",
        [(15, 28), (29, 60)],
        "NG115 §1.3",
    ),
]


# ─── J44 Red Flag Probes (net-new Phase 3 content) ─────────────────────
# The 5 upstream flag codes are already atomic single-observation events
# — no splitting required. parent_flag_code stays None. All escalate to
# EMERGENCY_999: each is a sign of acute respiratory failure.

J44_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {
    "oxygen_saturation_below_88": RedFlagProbe(
        flag_code="oxygen_saturation_below_88",
        parent_flag_code=None,
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG115 §1.5",
        patient_facing_question=(
            "If you have a pulse oximeter at home — has the reading been below 88?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "acute_severe_breathlessness": RedFlagProbe(
        flag_code="acute_severe_breathlessness",
        parent_flag_code=None,
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG115 §1.2",
        patient_facing_question=(
            "Is your breathlessness much worse today than it usually is during a flare-up?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "cyanosis": RedFlagProbe(
        flag_code="cyanosis",
        parent_flag_code=None,
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG115 §1.2",
        patient_facing_question=(
            "Have your lips, fingertips, or tongue turned a bluish or grey colour?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "acute_confusion": RedFlagProbe(
        flag_code="acute_confusion",
        parent_flag_code=None,
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG115 §1.2",
        patient_facing_question=(
            "Have you or someone close to you noticed you're more confused or muddled than usual today?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "unable_to_complete_sentences": RedFlagProbe(
        flag_code="unable_to_complete_sentences",
        parent_flag_code=None,
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG115 §1.2",
        patient_facing_question=(
            "Are you having to stop partway through a sentence to catch your breath?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {"J44": J44_PLAYBOOK}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {"J44": J44_TRAJECTORIES}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {"J44": J44_REQUIRED_QUESTIONS}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {"J44": J44_RED_FLAG_PROBES}

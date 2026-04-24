"""Orthopaedic pathways — W37, W38, W40, W43.

Phase 3 status: **W40 only** in this commit (Gate 2 per PLAN.md §7).
W37, W38, W43 deferred to the next orthopaedic commit once the W40
template has been reviewed and approved — confirms the R17/R18
template translates cleanly to a non-obstetric surgical cluster.

Content sources:
  - Trajectories ported verbatim from benchmarks.py.
  - Playbook metadata from monolith PLAYBOOKS.
  - Required Questions and Red Flag Probes net-new for Phase 3.

Decisions during port (not open flags):
  - Upstream fever_above_38_5 splits into two probes (reading vs
    symptoms) because not every patient has a home thermometer.
    Both SAME_DAY — post-surgical fever is a prosthetic joint
    infection suspicion; 999 only if paired with sepsis signs
    (covered in other pathways).
  - knee_effusion_severe splits into three probes (swelling,
    redness/heat, sudden pain) — each is an independent clinical
    observation of an evolving joint problem. All SAME_DAY.
  - dvt_symptoms is one atomic probe (not split) — the calf
    presentation is one clinical observation with multiple anchors
    (pain / swelling / warmth / tenderness), same pattern as the
    DVT calf probe in R17/R18.
  - pe_symptoms splits into breathing and chest pain, both 999,
    same as R17/R18 (no calf probe duplicated here since
    dvt_symptoms covers that).

Primary NICE sources: NG226 (joint replacement), TA304 (TKR devices),
QS48 (surgical site infection), QS89 (VTE in hospital). Reviewer
specialty: Orthopaedic surgeon.
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
# W40 — Total Knee Replacement
# ═══════════════════════════════════════════════════════════════════════

W40_PLAYBOOK = PathwayPlaybook(
    opcs_code="W40",
    label="Total Knee Replacement",
    category="surgical",
    nice_ids=["NG226", "TA304", "QS48", "QS89"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "wound_healing",
        "pain_management",
        "vte_prophylaxis",
        "mobility_progress",
        "infection_signs",
        "physiotherapy_compliance",
    ],
    red_flag_codes=[
        "wound_dehiscence",
        "dvt_symptoms",
        "fever_above_38_5",
        "pe_symptoms",
        "knee_effusion_severe",
    ],
    validation_status=_DRAFT,
)


def _traj(
    domain: str, day: int, expected: int, upper: int, state: str, nice: str,
) -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code="W40",
        domain=domain,
        day_range_start=day,
        day_range_end=day,
        expected_score=expected,
        upper_bound_score=upper,
        expected_state=state,
        nice_source=nice,
        validation_status=_DRAFT,
    )


W40_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG226 §1.8 (post-op wound care)
    _traj("wound_healing",  1, 2, 3, "Wound intact, bruising and swelling expected", "NG226"),
    _traj("wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG226"),
    _traj("wound_healing",  7, 1, 2, "Wound closing well", "NG226"),
    _traj("wound_healing", 14, 1, 2, "Healing well", "NG226"),
    _traj("wound_healing", 21, 1, 1, "Well healed", "NG226"),
    _traj("wound_healing", 28, 0, 1, "Healed", "NG226"),
    _traj("wound_healing", 42, 0, 1, "Healed", "NG226"),
    _traj("wound_healing", 60, 0, 0, "Fully healed", "NG226"),

    # pain_management — NG226 §1.6
    _traj("pain_management",  1, 2, 3, "Moderate pain expected post-op", "NG226"),
    _traj("pain_management",  3, 2, 3, "Pain reducing with analgesia", "NG226"),
    _traj("pain_management",  7, 2, 2, "Mild-moderate pain at activity", "NG226"),
    _traj("pain_management", 14, 1, 2, "Mild pain reducing", "NG226"),
    _traj("pain_management", 21, 1, 2, "Mild pain", "NG226"),
    _traj("pain_management", 28, 1, 1, "Minimal pain", "NG226"),
    _traj("pain_management", 42, 0, 1, "Pain resolving", "NG226"),
    _traj("pain_management", 60, 0, 1, "Pain resolved or minimal", "NG226"),

    # vte_prophylaxis — NG89 §1.9 (VTE in arthroplasty)
    _traj("vte_prophylaxis",  1, 1, 2, "LMWH/anticoagulant commenced", "NG89"),
    _traj("vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("vte_prophylaxis",  7, 1, 2, "Adherent — 14-day course for knee", "NG89"),
    _traj("vte_prophylaxis", 14, 1, 1, "Course completed at day 14 for TKR", "NG89"),
    _traj("vte_prophylaxis", 21, 0, 1, "Completed", "NG89"),
    _traj("vte_prophylaxis", 28, 0, 1, "Completed", "NG89"),
    _traj("vte_prophylaxis", 42, 0, 0, "N/A", "NG89"),
    _traj("vte_prophylaxis", 60, 0, 0, "N/A", "NG89"),

    # mobility_progress — NG226 §1.10 (early mobilisation)
    _traj("mobility_progress",  1, 2, 3, "Walking with frame expected", "NG226"),
    _traj("mobility_progress",  3, 2, 3, "Mobilising short distances", "NG226"),
    _traj("mobility_progress",  7, 2, 2, "Walking with crutches/stick", "NG226"),
    _traj("mobility_progress", 14, 1, 2, "Improving mobility", "NG226"),
    _traj("mobility_progress", 21, 1, 2, "Increasing range of movement", "NG226"),
    _traj("mobility_progress", 28, 1, 1, "Good progress, reduced aid", "NG226"),
    _traj("mobility_progress", 42, 1, 1, "Near-normal mobility", "NG226"),
    _traj("mobility_progress", 60, 0, 1, "Normal mobility expected", "NG226"),

    # infection_signs — QS48 §1 (SSI surveillance)
    _traj("infection_signs",  1, 1, 2, "Normal post-op inflammation", "NG226"),
    _traj("infection_signs",  3, 1, 2, "Monitor for increasing redness/heat/swelling", "NG226"),
    _traj("infection_signs",  7, 1, 2, "Should be settling", "NG226"),
    _traj("infection_signs", 14, 0, 1, "No signs expected", "NG226"),
    _traj("infection_signs", 21, 0, 1, "No signs expected", "NG226"),
    _traj("infection_signs", 28, 0, 1, "No signs expected", "NG226"),
    _traj("infection_signs", 42, 0, 0, "Resolved", "NG226"),
    _traj("infection_signs", 60, 0, 0, "Resolved", "NG226"),

    # physiotherapy_compliance — NG226 §1.11
    # CLINICAL_REVIEW_NEEDED: trajectory assumes consistent outpatient
    # physio attendance. Real NHS attendance varies — reviewer to confirm
    # whether these expected values need softening for standard-care
    # vs enhanced-pathway patients.
    _traj("physiotherapy_compliance",  1, 1, 2, "Exercises commenced, CPM if prescribed", "NG226"),
    _traj("physiotherapy_compliance",  3, 1, 2, "Daily exercises ongoing", "NG226"),
    _traj("physiotherapy_compliance",  7, 1, 2, "Outpatient physio commenced", "NG226"),
    _traj("physiotherapy_compliance", 14, 1, 1, "Attending/doing physio regularly", "NG226"),
    _traj("physiotherapy_compliance", 21, 1, 1, "Regular physio", "NG226"),
    _traj("physiotherapy_compliance", 28, 1, 1, "Ongoing adherence", "NG226"),
    _traj("physiotherapy_compliance", 42, 1, 1, "Ongoing adherence", "NG226"),
    _traj("physiotherapy_compliance", 60, 0, 1, "Programme completing", "NG226"),
]


def _rq(
    domain: str, text: str, bands: list[tuple[int, int]], nice: str,
) -> RequiredQuestion:
    return RequiredQuestion(
        opcs_code="W40",
        domain=domain,
        question_text=text,
        required=True,
        day_ranges=bands,
        validation_status=_DRAFT,
    )


W40_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Wound + infection are the two dominant Day 1-28 concerns (SSI risk).
    _rq(
        "wound_healing",
        "How is the wound looking — any redness, swelling beyond what you had a few days ago, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.8",
    ),
    _rq(
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable enough to move around and do your exercises?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.6",
    ),
    _rq(
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14)],
        "NG89 §1.9",
    ),
    _rq(
        "mobility_progress",
        "How are you getting around — walking aids you're using, distance you're managing, stairs?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.10",
    ),
    _rq(
        "physiotherapy_compliance",
        "How are you getting on with the physio exercises — doing them at home, and have you started outpatient sessions yet?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.11",
    ),
    _rq(
        "infection_signs",
        "Any increasing heat or redness around the wound, or a fever or feeling generally unwell?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "QS48",
    ),

    # Day 15-28: progress on range of movement, return to daily activities
    _rq(
        "mobility_progress",
        "How is the knee bending and straightening — any particular movements that still feel stiff or stuck?",
        [(15, 28), (29, 60)],
        "NG226 §1.10",
    ),

    # Day 29-60: longer-term function
    _rq(
        "physiotherapy_compliance",
        "How's physio going overall — nearing the end of your sessions, or still working on specific goals?",
        [(29, 60)],
        "NG226 §1.11",
    ),
]


# ─── W40 Red Flag Probes (net-new Phase 3 content) ─────────────────────

W40_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ wound_dehiscence — 2 probes (same pattern as R17/R18) ═══════════
    "wound_dehiscence_gaping": RedFlagProbe(
        flag_code="wound_dehiscence_gaping",
        parent_flag_code="wound_dehiscence",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8",
        patient_facing_question=(
            "Has the wound opened up at all — the edges of the scar coming apart?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "wound_dehiscence_discharge": RedFlagProbe(
        flag_code="wound_dehiscence_discharge",
        parent_flag_code="wound_dehiscence",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ dvt_symptoms — 1 atomic probe (calf presentation) ══════════════
    # Single clinical observation with multiple anchors, same pattern as
    # the DVT calf probe in R17/R18. The "non-operated leg" cue helps the
    # patient distinguish DVT from normal post-op swelling.
    "dvt_symptoms": RedFlagProbe(
        flag_code="dvt_symptoms",
        parent_flag_code=None,
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "Any new pain, swelling, or warmth in your calf that feels different "
            "from your normal post-surgery swelling — especially tender when you "
            "press on it, and particularly in your non-operated leg?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ fever_above_38_5 — 2 probes (reading vs symptoms) ══════════════
    "fever_above_38_5_reading": RedFlagProbe(
        flag_code="fever_above_38_5_reading",
        parent_flag_code="fever_above_38_5",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG226 §1.8",
        patient_facing_question=(
            "If you have a thermometer — has your temperature been above 38.5?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "fever_above_38_5_symptoms": RedFlagProbe(
        flag_code="fever_above_38_5_symptoms",
        parent_flag_code="fever_above_38_5",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG226 §1.8",
        patient_facing_question=(
            "Have you felt very hot-and-cold, shivery, or feverish since the last call?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: fever alone is SAME_DAY in this draft.
    # Reviewer to confirm whether fever + sepsis signs (rigors, tachycardia,
    # confusion) should upgrade to EMERGENCY_999 via a separate compound
    # rule at the call-status layer, or whether a new probe captures the
    # sepsis combination.

    # ══ pe_symptoms — 2 probes (same pattern as R17/R18) ═══════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "Have you had any sudden breathlessness that wasn't there before?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pe_symptoms_chest_pain": RedFlagProbe(
        flag_code="pe_symptoms_chest_pain",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "Any sharp chest pain — especially when you breathe in deeply?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ knee_effusion_severe — 3 probes ═══════════════════════════════
    # Prosthetic joint infection / haemarthrosis / large effusion all
    # present with overlapping signs. Split into three single-observation
    # probes so the trigger condition is clean; each is a distinct
    # clinical event clinicians would want to know about separately.
    "knee_effusion_severe_swelling": RedFlagProbe(
        flag_code="knee_effusion_severe_swelling",
        parent_flag_code="knee_effusion_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "Has the knee suddenly become much more swollen than it was a few days ago?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "knee_effusion_severe_redness_heat": RedFlagProbe(
        flag_code="knee_effusion_severe_redness_heat",
        parent_flag_code="knee_effusion_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "Has the knee become hot to the touch or noticeably more red than before?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "knee_effusion_severe_pain": RedFlagProbe(
        flag_code="knee_effusion_severe_pain",
        parent_flag_code="knee_effusion_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "Has the knee pain suddenly got much worse — out of proportion to what you had before?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {"W40": W40_PLAYBOOK}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {"W40": W40_TRAJECTORIES}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {"W40": W40_REQUIRED_QUESTIONS}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {"W40": W40_RED_FLAG_PROBES}

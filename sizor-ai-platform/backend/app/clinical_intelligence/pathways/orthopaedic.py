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
  - Upstream fever_above_38_5 splits into three probes: reading
    (SAME_DAY, threshold 38°C per QS48), symptoms (SAME_DAY, generic
    feverish feeling), and rigors (EMERGENCY_999 — uncontrollable
    shivering indicates bacteraemia). Parent_flag_code stays as the
    monolith's 'fever_above_38_5' even though the clinical threshold
    is 38°C per QS48 SSI surveillance — CLINICAL_REVIEW_NEEDED below.
  - knee_effusion_severe splits into three single-observation
    probes (swelling, redness/heat, pain), all SAME_DAY individually.
    A compound rule — two+ effusion probes firing with any fever
    probe firing should auto-escalate to EMERGENCY_999 for suspected
    PJI sepsis — is flagged for Phase 4 call-status implementation,
    not encoded at the probe layer here.
  - dvt_symptoms splits into operated vs non-operated leg probes.
    Post-TKR DVT most commonly occurs in the NON-operated leg; the
    operated-leg question specifically excludes normal post-op
    swelling to avoid both false positives (normal swelling) and
    false negatives (patient focuses only on non-operated leg).
    Both EMERGENCY_999.
  - pe_symptoms splits into breathing and chest pain, both 999,
    same as R17/R18 (no calf probe duplicated here since
    dvt_symptoms covers that).

Wording principles applied throughout:
  No patient-memory-comparison phrasings ("worse than before",
  "more than usual", "beyond what you had", "different from your
  normal"). Use concrete anchors instead: spreading redness,
  24-hour change windows, absolute thresholds, or behavioural
  anchors (can't walk / can't sleep / stopped what you were doing).
  For genuine baseline comparisons, convert to a coverage-check
  question asking whether the care team has noted a change rather
  than asking the patient.

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
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
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
        "Any heat or redness around the wound that has spread further than the scar area, a fever in the last 24 hours, or feeling generally unwell?",
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

    # ══ dvt_symptoms — split by leg (both EMERGENCY_999) ═══════════════
    # Post-TKR DVT most commonly occurs in the NON-operated leg, so that
    # probe gets the simpler wording. The operated-leg probe has to
    # distinguish new/worsening calf pain from the expected post-op
    # swelling — the 24-hour change window anchors this without asking
    # the patient to compare to a memory baseline. Both probes share
    # parent_flag_code='dvt_symptoms' for dashboard aggregation.
    "dvt_symptoms_non_operated_leg": RedFlagProbe(
        flag_code="dvt_symptoms_non_operated_leg",
        parent_flag_code="dvt_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "Any new pain, swelling, or tenderness in your non-operated leg's calf?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "dvt_symptoms_operated_leg": RedFlagProbe(
        flag_code="dvt_symptoms_operated_leg",
        parent_flag_code="dvt_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "In your operated leg — any calf pain or tenderness that's new "
            "or worsening in the last day or two, separate from the general "
            "post-op swelling you had before?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
        # CLINICAL_REVIEW_NEEDED: wording still contains "you had before"
        # which edges close to a memory-comparison phrasing. Reviewer to
        # confirm whether the "last day or two" anchor is sufficient or
        # whether the phrase needs tightening to a pure 24-hour / pure
        # behavioural anchor.
    ),

    # ══ fever_above_38_5 — 3 probes: reading, symptoms, rigors ═════════
    # QS48 SSI surveillance threshold is 38°C (not 38.5°C). The upstream
    # monolith code 'fever_above_38_5' is retained as parent for
    # compatibility, but probes reflect the correct clinical threshold.
    # Rigors split out as EMERGENCY_999 — uncontrollable shivering
    # indicates bacteraemia and warrants immediate escalation.
    "fever_above_38_5_reading": RedFlagProbe(
        flag_code="fever_above_38_5_reading",
        parent_flag_code="fever_above_38_5",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG226 §1.8",
        patient_facing_question=(
            "If you have a thermometer — has your temperature been above 38?"
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
            "Have you felt hot-and-cold, sweaty, or feverish in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "fever_with_rigors": RedFlagProbe(
        flag_code="fever_with_rigors",
        parent_flag_code="fever_above_38_5",
        category=RedFlagCategory.SEPSIS_SIGNS,
        nice_basis="QS48 / NG51 §1.1",
        patient_facing_question=(
            "Have you had any episodes of uncontrollable shivering or shaking?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: probe name 'fever_above_38_5_reading' still
    # references the 38.5 threshold but the question now asks about 38°C
    # (the QS48 SSI surveillance threshold). Parent_flag_code kept as
    # 'fever_above_38_5' for upstream monolith compatibility. Reviewer
    # to decide whether to rename the upstream code to 'fever_above_38'
    # across the pathway set (would propagate to monolith and dashboards).
    #
    # CLINICAL_REVIEW_NEEDED: PJI sepsis compound rule for Phase 4 call-
    # status logic — when two or more knee_effusion_severe_* probes fire
    # AND any fever_above_38_5_* probe fires, the combined picture
    # suggests PJI sepsis and should auto-escalate to EMERGENCY_999.
    # Current draft treats the probes as isolated SAME_DAY signals;
    # reviewer to confirm this compound rule lands in Phase 4
    # compute_overall_call_status.

    # ══ pe_symptoms — 2 probes (same pattern as R17/R18) ═══════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.9 / NG158",
        patient_facing_question=(
            "Have you had any sudden breathlessness today that made you stop what you were doing?"
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
    # All use 24-hour change windows or concrete anchors instead of
    # memory-comparison phrasings.
    "knee_effusion_severe_swelling": RedFlagProbe(
        flag_code="knee_effusion_severe_swelling",
        parent_flag_code="knee_effusion_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "Has the knee become noticeably more swollen in the last 24 hours?"
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
            "Has the knee become hot to the touch, or has redness spread beyond the immediate wound area?"
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
            "In the last 24 hours, has the knee pain become severe enough to stop you walking, doing your exercises, or sleeping?"
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

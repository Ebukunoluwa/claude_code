"""Orthopaedic pathways — W37, W38, W40, W43.

Phase 3 orthopaedic cluster. W40 landed first as the Gate-2 template
confirming the R17/R18 obstetric template translates cleanly to a
non-obstetric surgical cluster. W37/W38/W43 follow in separate commits
applying the same template with pathway-specific divergences.

Content sources:
  - Trajectories ported verbatim from benchmarks.py.
  - Playbook metadata from pathway_map.OPCS_TO_NICE_MAP.
  - Required Questions and Red Flag Probes net-new for Phase 3.

Decisions during port (not open flags):
  - Upstream fever_above_38_5 splits into three probes: reading
    (SAME_DAY, threshold 38°C per QS48), symptoms (SAME_DAY, generic
    feverish feeling), and rigors (EMERGENCY_999 — uncontrollable
    shivering indicates bacteraemia). Parent_flag_code stays as the
    monolith's 'fever_above_38_5' even though the clinical threshold
    is 38°C per QS48 SSI surveillance — CLINICAL_REVIEW_NEEDED below.
  - knee_effusion_severe (W40) splits into three single-observation
    probes (swelling, redness/heat, pain), all SAME_DAY individually.
    A compound rule — two+ effusion probes firing with any fever
    probe firing should auto-escalate to EMERGENCY_999 for suspected
    PJI sepsis — is flagged for Phase 4 call-status implementation,
    not encoded at the probe layer here.
  - dvt_symptoms splits into operated vs non-operated leg probes.
    Post-arthroplasty DVT most commonly occurs in the NON-operated
    leg; the operated-leg question specifically excludes normal
    post-op swelling to avoid both false positives (normal swelling)
    and false negatives (patient focuses only on non-operated leg).
    Both EMERGENCY_999.
  - pe_symptoms splits into breathing and chest pain, both 999,
    same as R17/R18 (no calf probe duplicated here since
    dvt_symptoms covers that).
  - hip_dislocation (W37, W38) splits into three probes covering the
    classic triad: sudden severe pain on movement, leg looking
    shortened/externally rotated, and inability to bear weight after
    a specific movement. All EMERGENCY_999. Patient-facing wording
    avoids clinical terms ("dislocation", "external rotation").

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
TA455 (THR devices), NG124 (hip fracture), QS16 (falls), QS48 (SSI),
QS89 (VTE), NG89 (VTE in arthroplasty). Reviewer specialty:
Orthopaedic surgeon (W38 is shared-care with geriatrician).
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
    opcs: str, domain: str, day: int, expected: int, upper: int, state: str, nice: str,
) -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code=opcs,
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
    _traj("W40", "wound_healing",  1, 2, 3, "Wound intact, bruising and swelling expected", "NG226"),
    _traj("W40", "wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG226"),
    _traj("W40", "wound_healing",  7, 1, 2, "Wound closing well", "NG226"),
    _traj("W40", "wound_healing", 14, 1, 2, "Healing well", "NG226"),
    _traj("W40", "wound_healing", 21, 1, 1, "Well healed", "NG226"),
    _traj("W40", "wound_healing", 28, 0, 1, "Healed", "NG226"),
    _traj("W40", "wound_healing", 42, 0, 1, "Healed", "NG226"),
    _traj("W40", "wound_healing", 60, 0, 0, "Fully healed", "NG226"),

    # pain_management — NG226 §1.6
    _traj("W40", "pain_management",  1, 2, 3, "Moderate pain expected post-op", "NG226"),
    _traj("W40", "pain_management",  3, 2, 3, "Pain reducing with analgesia", "NG226"),
    _traj("W40", "pain_management",  7, 2, 2, "Mild-moderate pain at activity", "NG226"),
    _traj("W40", "pain_management", 14, 1, 2, "Mild pain reducing", "NG226"),
    _traj("W40", "pain_management", 21, 1, 2, "Mild pain", "NG226"),
    _traj("W40", "pain_management", 28, 1, 1, "Minimal pain", "NG226"),
    _traj("W40", "pain_management", 42, 0, 1, "Pain resolving", "NG226"),
    _traj("W40", "pain_management", 60, 0, 1, "Pain resolved or minimal", "NG226"),

    # vte_prophylaxis — NG89 §1.9 (VTE in arthroplasty)
    _traj("W40", "vte_prophylaxis",  1, 1, 2, "LMWH/anticoagulant commenced", "NG89"),
    _traj("W40", "vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("W40", "vte_prophylaxis",  7, 1, 2, "Adherent — 14-day course for knee", "NG89"),
    _traj("W40", "vte_prophylaxis", 14, 1, 1, "Course completed at day 14 for TKR", "NG89"),
    _traj("W40", "vte_prophylaxis", 21, 0, 1, "Completed", "NG89"),
    _traj("W40", "vte_prophylaxis", 28, 0, 1, "Completed", "NG89"),
    _traj("W40", "vte_prophylaxis", 42, 0, 0, "N/A", "NG89"),
    _traj("W40", "vte_prophylaxis", 60, 0, 0, "N/A", "NG89"),

    # mobility_progress — NG226 §1.10 (early mobilisation)
    _traj("W40", "mobility_progress",  1, 2, 3, "Walking with frame expected", "NG226"),
    _traj("W40", "mobility_progress",  3, 2, 3, "Mobilising short distances", "NG226"),
    _traj("W40", "mobility_progress",  7, 2, 2, "Walking with crutches/stick", "NG226"),
    _traj("W40", "mobility_progress", 14, 1, 2, "Improving mobility", "NG226"),
    _traj("W40", "mobility_progress", 21, 1, 2, "Increasing range of movement", "NG226"),
    _traj("W40", "mobility_progress", 28, 1, 1, "Good progress, reduced aid", "NG226"),
    _traj("W40", "mobility_progress", 42, 1, 1, "Near-normal mobility", "NG226"),
    _traj("W40", "mobility_progress", 60, 0, 1, "Normal mobility expected", "NG226"),

    # infection_signs — QS48 §1 (SSI surveillance)
    _traj("W40", "infection_signs",  1, 1, 2, "Normal post-op inflammation", "NG226"),
    _traj("W40", "infection_signs",  3, 1, 2, "Monitor for increasing redness/heat/swelling", "NG226"),
    _traj("W40", "infection_signs",  7, 1, 2, "Should be settling", "NG226"),
    _traj("W40", "infection_signs", 14, 0, 1, "No signs expected", "NG226"),
    _traj("W40", "infection_signs", 21, 0, 1, "No signs expected", "NG226"),
    _traj("W40", "infection_signs", 28, 0, 1, "No signs expected", "NG226"),
    _traj("W40", "infection_signs", 42, 0, 0, "Resolved", "NG226"),
    _traj("W40", "infection_signs", 60, 0, 0, "Resolved", "NG226"),

    # physiotherapy_compliance — NG226 §1.11
    # CLINICAL_REVIEW_NEEDED: trajectory assumes consistent outpatient
    # physio attendance. Real NHS attendance varies — reviewer to confirm
    # whether these expected values need softening for standard-care
    # vs enhanced-pathway patients.
    _traj("W40", "physiotherapy_compliance",  1, 1, 2, "Exercises commenced, CPM if prescribed", "NG226"),
    _traj("W40", "physiotherapy_compliance",  3, 1, 2, "Daily exercises ongoing", "NG226"),
    _traj("W40", "physiotherapy_compliance",  7, 1, 2, "Outpatient physio commenced", "NG226"),
    _traj("W40", "physiotherapy_compliance", 14, 1, 1, "Attending/doing physio regularly", "NG226"),
    _traj("W40", "physiotherapy_compliance", 21, 1, 1, "Regular physio", "NG226"),
    _traj("W40", "physiotherapy_compliance", 28, 1, 1, "Ongoing adherence", "NG226"),
    _traj("W40", "physiotherapy_compliance", 42, 1, 1, "Ongoing adherence", "NG226"),
    _traj("W40", "physiotherapy_compliance", 60, 0, 1, "Programme completing", "NG226"),
]


def _rq(
    opcs: str, domain: str, text: str, bands: list[tuple[int, int]], nice: str,
) -> RequiredQuestion:
    return RequiredQuestion(
        opcs_code=opcs,
        domain=domain,
        question_text=text,
        required=True,
        day_ranges=bands,
        validation_status=_DRAFT,
    )


W40_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Wound + infection are the two dominant Day 1-28 concerns (SSI risk).
    _rq(
        "W40",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.8",
    ),
    _rq(
        "W40",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable enough to move around and do your exercises?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.6",
    ),
    _rq(
        "W40",
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14)],
        "NG89 §1.9",
    ),
    _rq(
        "W40",
        "mobility_progress",
        "How are you getting around — walking aids you're using, distance you're managing, stairs?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.10",
    ),
    _rq(
        "W40",
        "physiotherapy_compliance",
        "How are you getting on with the physio exercises — doing them at home, and have you started outpatient sessions yet?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.11",
    ),
    _rq(
        "W40",
        "infection_signs",
        "Any heat or redness around the wound that has spread further than the scar area, a fever in the last 24 hours, or feeling generally unwell?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "QS48",
    ),

    # Day 15-28: progress on range of movement, return to daily activities
    _rq(
        "W40",
        "mobility_progress",
        "How is the knee bending and straightening — any particular movements that still feel stiff or stuck?",
        [(15, 28), (29, 60)],
        "NG226 §1.10",
    ),

    # Day 29-60: longer-term function
    _rq(
        "W40",
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


# ═══════════════════════════════════════════════════════════════════════
# W37 — Total Hip Replacement
# ═══════════════════════════════════════════════════════════════════════
#
# Divergences from W40 (TKR) worth flagging for the reviewer:
#   - LMWH course is 28 days for THR (vs 14 days for TKR per NG89 §1.9).
#     The vte_prophylaxis trajectory reflects adherence expected through
#     day 28. RQ injection question extends into the (15, 28) band.
#   - hip_dislocation replaces knee_effusion_severe as the pathway-
#     specific red flag. Three probes: sudden severe pain on movement,
#     leg appearing shortened or externally rotated, inability to bear
#     weight after a specific movement. All EMERGENCY_999.
#   - mobility_progress RQ includes hip-precaution framing: bending
#     past 90°, crossing legs, twisting the operated leg inward. These
#     are the classic posterior-approach precautions per NG226 §1.10.
#   - Physiotherapy emphasis shifts to abduction strengthening and
#     gait retraining rather than knee flexion range-of-movement.

W37_PLAYBOOK = PathwayPlaybook(
    opcs_code="W37",
    label="Total Hip Replacement",
    category="surgical",
    nice_ids=["NG226", "TA455", "QS48", "QS89", "NG89"],
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
        "hip_dislocation",
        "fever_above_38_5",
        "pe_symptoms",
    ],
    validation_status=_DRAFT,
)


W37_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG226 §1.8
    _traj("W37", "wound_healing",  1, 2, 3, "Wound intact, bruising expected", "NG226"),
    _traj("W37", "wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG226"),
    _traj("W37", "wound_healing",  7, 1, 2, "Wound closing, sutures/clips in place", "NG226"),
    _traj("W37", "wound_healing", 14, 1, 2, "Wound healing well", "NG226"),
    _traj("W37", "wound_healing", 21, 1, 1, "Well healed", "NG226"),
    _traj("W37", "wound_healing", 28, 0, 1, "Healed", "NG226"),
    _traj("W37", "wound_healing", 42, 0, 1, "Healed", "NG226"),
    _traj("W37", "wound_healing", 60, 0, 0, "Fully healed", "NG226"),

    # pain_management — NG226 §1.6
    _traj("W37", "pain_management",  1, 2, 3, "Moderate pain expected", "NG226"),
    _traj("W37", "pain_management",  3, 2, 3, "Pain reducing with analgesia", "NG226"),
    _traj("W37", "pain_management",  7, 2, 2, "Mild-moderate pain at activity", "NG226"),
    _traj("W37", "pain_management", 14, 1, 2, "Mild pain reducing", "NG226"),
    _traj("W37", "pain_management", 21, 1, 2, "Mild pain", "NG226"),
    _traj("W37", "pain_management", 28, 1, 1, "Minimal pain", "NG226"),
    _traj("W37", "pain_management", 42, 0, 1, "Pain resolving", "NG226"),
    _traj("W37", "pain_management", 60, 0, 1, "Pain resolved or minimal", "NG226"),

    # vte_prophylaxis — NG89 §1.9 (28-day course for THR)
    _traj("W37", "vte_prophylaxis",  1, 1, 2, "LMWH/anticoagulant taken", "NG89"),
    _traj("W37", "vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("W37", "vte_prophylaxis",  7, 1, 2, "Adherent — 28-day course", "NG89"),
    _traj("W37", "vte_prophylaxis", 14, 1, 2, "Adherent", "NG89"),
    _traj("W37", "vte_prophylaxis", 21, 1, 2, "Adherent", "NG89"),
    _traj("W37", "vte_prophylaxis", 28, 1, 1, "Course completed", "NG89"),
    _traj("W37", "vte_prophylaxis", 42, 0, 1, "Course completed", "NG89"),
    _traj("W37", "vte_prophylaxis", 60, 0, 0, "N/A", "NG89"),

    # mobility_progress — NG226 §1.10
    _traj("W37", "mobility_progress",  1, 2, 3, "Walking with frame expected", "NG226"),
    _traj("W37", "mobility_progress",  3, 2, 3, "Mobilising short distances", "NG226"),
    _traj("W37", "mobility_progress",  7, 2, 2, "Walking with aid", "NG226"),
    _traj("W37", "mobility_progress", 14, 1, 2, "Improving mobility", "NG226"),
    _traj("W37", "mobility_progress", 21, 1, 2, "Walking further", "NG226"),
    _traj("W37", "mobility_progress", 28, 1, 1, "Good progress", "NG226"),
    _traj("W37", "mobility_progress", 42, 1, 1, "Near-normal mobility", "NG226"),
    _traj("W37", "mobility_progress", 60, 0, 1, "Normal mobility expected", "NG226"),

    # infection_signs — QS48 §1
    _traj("W37", "infection_signs",  1, 1, 2, "Normal post-op inflammation", "NG226"),
    _traj("W37", "infection_signs",  3, 1, 2, "Monitor for increasing redness/heat", "NG226"),
    _traj("W37", "infection_signs",  7, 1, 2, "Should be settling", "NG226"),
    _traj("W37", "infection_signs", 14, 0, 1, "No signs expected", "NG226"),
    _traj("W37", "infection_signs", 21, 0, 1, "No signs expected", "NG226"),
    _traj("W37", "infection_signs", 28, 0, 1, "No signs expected", "NG226"),
    _traj("W37", "infection_signs", 42, 0, 0, "Resolved", "NG226"),
    _traj("W37", "infection_signs", 60, 0, 0, "Resolved", "NG226"),

    # physiotherapy_compliance — NG226 §1.11
    _traj("W37", "physiotherapy_compliance",  1, 1, 2, "Exercises commenced", "NG226"),
    _traj("W37", "physiotherapy_compliance",  3, 1, 2, "Daily exercises in progress", "NG226"),
    _traj("W37", "physiotherapy_compliance",  7, 1, 2, "Exercise programme ongoing", "NG226"),
    _traj("W37", "physiotherapy_compliance", 14, 1, 1, "Attending/doing physio", "NG226"),
    _traj("W37", "physiotherapy_compliance", 21, 1, 1, "Regular physio", "NG226"),
    _traj("W37", "physiotherapy_compliance", 28, 1, 1, "Ongoing adherence", "NG226"),
    _traj("W37", "physiotherapy_compliance", 42, 1, 1, "Ongoing adherence", "NG226"),
    _traj("W37", "physiotherapy_compliance", 60, 0, 1, "Programme completing", "NG226"),
]


W37_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Wound + infection are the two dominant Day 1-28 concerns (SSI risk).
    _rq(
        "W37",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.8",
    ),
    _rq(
        "W37",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable enough to move around and do your exercises?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.6",
    ),
    # VTE course is 28 days for THR — injection question extends to day 28.
    _rq(
        "W37",
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG89 §1.9",
    ),
    _rq(
        "W37",
        "mobility_progress",
        "How are you getting around — walking aids you're using, distance you're managing, stairs?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.10",
    ),
    # Hip-specific: precautions against posterior dislocation in the
    # first 6 weeks. Framed as concrete behaviours rather than clinical
    # terms ("dislocation", "flexion past 90°").
    #
    # TEMPLATE DEVIATION — compound phrasing by design. Hip precautions
    # are taught to the patient pre-op as a bundled behavioural rule
    # set and reinforced post-op as a bundle. Splitting into three
    # separate RQs (one per precaution) would fragment a single
    # clinical concept the patient already holds as one thing. This is
    # a conscious, one-off exception to the one-observation-per-RQ
    # principle applied elsewhere. Future pathways MUST NOT treat this
    # as license for general compound RQ phrasing; the exception
    # applies only to bundled patient-education constructs like hip
    # precautions where the bundle is the clinical unit.
    _rq(
        "W37",
        "mobility_progress",
        "Are you keeping to the hip precautions — not bending the hip past a right angle, not crossing your legs, not twisting the operated leg inward?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.10",
    ),
    _rq(
        "W37",
        "physiotherapy_compliance",
        "How are you getting on with the physio exercises — doing them at home, and have you started outpatient sessions yet?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG226 §1.11",
    ),
    _rq(
        "W37",
        "infection_signs",
        "Any heat or redness around the wound that has spread further than the scar area, a fever in the last 24 hours, or feeling generally unwell?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "QS48",
    ),

    # Day 29-60: longer-term function + physio completion
    _rq(
        "W37",
        "physiotherapy_compliance",
        "How's physio going overall — nearing the end of your sessions, or still working on specific goals?",
        [(29, 60)],
        "NG226 §1.11",
    ),
]


# ─── W37 Red Flag Probes ───────────────────────────────────────────────

W37_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ wound_dehiscence — 2 probes (same pattern as W40/R17/R18) ══════
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
    # Same principle as W40: post-arthroplasty DVT most commonly occurs
    # in the NON-operated leg, and the operated-leg probe must
    # distinguish new/worsening calf pain from the expected post-op
    # swelling using a 24-hour anchor rather than memory comparison.
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
            "in the last 24 hours, separate from the general post-op swelling?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ hip_dislocation — 3 probes (all EMERGENCY_999) ═════════════════
    # Classic triad of posterior hip dislocation: sudden severe pain
    # triggered by a specific movement, leg appearing shortened and
    # externally rotated, inability to bear weight on the operated leg.
    # Highest risk window is weeks 2-6 per NG226 §1.10. Patient-facing
    # wording avoids the word "dislocation" (frightening, ambiguous).
    "hip_dislocation_sudden_pain": RedFlagProbe(
        flag_code="hip_dislocation_sudden_pain",
        parent_flag_code="hip_dislocation",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.10",
        patient_facing_question=(
            "Have you had any sudden, severe pain in the operated hip — the "
            "kind that came on with a specific movement or a twist?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "hip_dislocation_leg_appearance": RedFlagProbe(
        flag_code="hip_dislocation_leg_appearance",
        parent_flag_code="hip_dislocation",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.10",
        patient_facing_question=(
            "Does the operated leg look shorter than the other one now, or "
            "is the foot pointing outward in a way it wasn't this morning?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "hip_dislocation_cannot_weight_bear": RedFlagProbe(
        flag_code="hip_dislocation_cannot_weight_bear",
        parent_flag_code="hip_dislocation",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.10",
        patient_facing_question=(
            "After a particular movement today, have you found you suddenly "
            "can't put any weight on the operated leg at all?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ fever_above_38_5 — 3 probes: reading, symptoms, rigors ═════════
    # Same structure as W40. QS48 SSI threshold is 38°C; upstream
    # monolith code retains 'fever_above_38_5' parent for compatibility.
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

    # ══ pe_symptoms — 2 probes (same pattern as W40/R17/R18) ═══════════
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
}


# ═══════════════════════════════════════════════════════════════════════
# W38 — Hip Fracture / Hemiarthroplasty
# ═══════════════════════════════════════════════════════════════════════
#
# Divergences from W37/W40 worth flagging for the reviewer:
#   - W38 is shared-care: orthopaedic surgeon + geriatrician. Cohort is
#     elderly and frail, often on baseline anticoagulants and living
#     with cognitive impairment. Probe wording leans on coverage-check
#     phrasings (ask about third-party observation) where the patient
#     themselves may not reliably notice the change.
#   - delirium_cognitive_screen is a W38/W37-W40-absent domain.
#     Patient-facing questions use carer-observed framing rather than
#     asking the patient to self-assess cognition.
#   - falls_risk is also new vs W37/W40. The corresponding red flag
#     (falls_with_injury) splits into three probes: fall with new pain,
#     fall with head strike (EMERGENCY_999 given anticoagulation risk),
#     and post-fall inability to bear weight (EMERGENCY_999 — suggests
#     refracture or implant failure).
#   - wound_infection parent code (not wound_dehiscence as in W37/W40)
#     per the upstream pathway_map. Probes split into spreading-redness
#     and discharge.
#   - VTE 28-day course (same as W37, longer than W40). RQ injection
#     question extends into day 15-28 band.

W38_PLAYBOOK = PathwayPlaybook(
    opcs_code="W38",
    label="Hip Fracture / Hemiarthroplasty",
    category="surgical",
    nice_ids=["NG124", "NG226", "QS16", "QS89"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "wound_healing",
        "pain_management",
        "delirium_cognitive_screen",
        "falls_risk",
        "vte_prophylaxis",
        "mobility_and_rehabilitation",
    ],
    red_flag_codes=[
        "delirium_acute",
        "dvt_symptoms",
        "pe_symptoms",
        "wound_infection",
        "falls_with_injury",
    ],
    validation_status=_DRAFT,
)


W38_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG124 §1.8
    _traj("W38", "wound_healing",  1, 2, 3, "Wound intact", "NG124"),
    _traj("W38", "wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG124"),
    _traj("W38", "wound_healing",  7, 1, 2, "Wound healing", "NG124"),
    _traj("W38", "wound_healing", 14, 1, 2, "Healing well", "NG124"),
    _traj("W38", "wound_healing", 21, 1, 1, "Well healed", "NG124"),
    _traj("W38", "wound_healing", 28, 0, 1, "Healed", "NG124"),
    _traj("W38", "wound_healing", 42, 0, 1, "Healed", "NG124"),
    _traj("W38", "wound_healing", 60, 0, 0, "Fully healed", "NG124"),

    # pain_management — NG124 §1.7
    _traj("W38", "pain_management",  1, 2, 3, "Moderate pain expected", "NG124"),
    _traj("W38", "pain_management",  3, 2, 3, "Analgesia being managed", "NG124"),
    _traj("W38", "pain_management",  7, 2, 2, "Mild-moderate pain", "NG124"),
    _traj("W38", "pain_management", 14, 1, 2, "Reducing pain", "NG124"),
    _traj("W38", "pain_management", 21, 1, 2, "Mild pain", "NG124"),
    _traj("W38", "pain_management", 28, 1, 1, "Minimal pain", "NG124"),
    _traj("W38", "pain_management", 42, 0, 1, "Resolving", "NG124"),
    _traj("W38", "pain_management", 60, 0, 1, "Resolved or minimal", "NG124"),

    # delirium_cognitive_screen — NG124 §1.6 (screen for post-op delirium)
    _traj("W38", "delirium_cognitive_screen",  1, 2, 3, "Screen for delirium — high risk elderly", "NG124"),
    _traj("W38", "delirium_cognitive_screen",  3, 2, 3, "Monitor for confusion/disorientation", "NG124"),
    _traj("W38", "delirium_cognitive_screen",  7, 1, 2, "Should be resolving if present", "NG124"),
    _traj("W38", "delirium_cognitive_screen", 14, 1, 1, "Cognitive function expected to normalise", "NG124"),
    _traj("W38", "delirium_cognitive_screen", 21, 0, 1, "No delirium expected", "NG124"),
    _traj("W38", "delirium_cognitive_screen", 28, 0, 1, "No delirium expected", "NG124"),
    _traj("W38", "delirium_cognitive_screen", 42, 0, 0, "Resolved", "NG124"),
    _traj("W38", "delirium_cognitive_screen", 60, 0, 0, "Resolved", "NG124"),

    # falls_risk — QS16 (falls in older people)
    _traj("W38", "falls_risk",  1, 2, 3, "High falls risk post-op", "QS16"),
    _traj("W38", "falls_risk",  3, 2, 3, "Still high risk", "QS16"),
    _traj("W38", "falls_risk",  7, 2, 2, "Ongoing high risk", "QS16"),
    _traj("W38", "falls_risk", 14, 1, 2, "Reducing with rehab", "QS16"),
    _traj("W38", "falls_risk", 21, 1, 2, "Improving stability", "QS16"),
    _traj("W38", "falls_risk", 28, 1, 1, "Managed falls risk", "QS16"),
    _traj("W38", "falls_risk", 42, 1, 1, "Ongoing monitoring", "QS16"),
    _traj("W38", "falls_risk", 60, 0, 1, "Near-baseline", "QS16"),

    # vte_prophylaxis — NG89 §1.9
    _traj("W38", "vte_prophylaxis",  1, 1, 2, "Anticoagulant commenced", "NG89"),
    _traj("W38", "vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("W38", "vte_prophylaxis",  7, 1, 2, "Adherent", "NG89"),
    _traj("W38", "vte_prophylaxis", 14, 1, 2, "Adherent", "NG89"),
    _traj("W38", "vte_prophylaxis", 21, 1, 2, "Adherent", "NG89"),
    _traj("W38", "vte_prophylaxis", 28, 1, 1, "Course completed", "NG89"),
    _traj("W38", "vte_prophylaxis", 42, 0, 1, "Completed", "NG89"),
    _traj("W38", "vte_prophylaxis", 60, 0, 0, "N/A", "NG89"),

    # mobility_and_rehabilitation — NG124 §1.10
    _traj("W38", "mobility_and_rehabilitation",  1, 2, 3, "Mobilising with assistance", "NG124"),
    _traj("W38", "mobility_and_rehabilitation",  3, 2, 3, "Short distance mobilisation", "NG124"),
    _traj("W38", "mobility_and_rehabilitation",  7, 2, 2, "Walking with aid", "NG124"),
    _traj("W38", "mobility_and_rehabilitation", 14, 1, 2, "Improving", "NG124"),
    _traj("W38", "mobility_and_rehabilitation", 21, 1, 2, "Progressing", "NG124"),
    _traj("W38", "mobility_and_rehabilitation", 28, 1, 1, "Good progress", "NG124"),
    _traj("W38", "mobility_and_rehabilitation", 42, 1, 1, "Ongoing rehab", "NG124"),
    _traj("W38", "mobility_and_rehabilitation", 60, 0, 1, "Near-normal", "NG124"),
]


W38_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    _rq(
        "W38",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG124 §1.8",
    ),
    _rq(
        "W38",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable enough to move around and do your exercises?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG124 §1.7",
    ),
    # Delirium screen — coverage-check phrasing asks about third-party
    # observation because the patient themselves may not notice the
    # fluctuating confusion that characterises delirium.
    _rq(
        "W38",
        "delirium_cognitive_screen",
        "Has anyone around you — family, carer, district nurse — mentioned that you've seemed more confused, drowsy, or different from your usual self in the last 24 hours?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG124 §1.6",
    ),
    _rq(
        "W38",
        "falls_risk",
        "Have you had any falls or near-falls since we last spoke — even slips you caught yourself on?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "QS16",
    ),
    # VTE course is 28 days for hip fracture — injection question
    # extends to day 28 (same as W37).
    _rq(
        "W38",
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG89 §1.9",
    ),
    _rq(
        "W38",
        "mobility_and_rehabilitation",
        "How are you getting around — what walking aids you're using, how far you're walking, and are you managing stairs and getting in and out of chairs?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG124 §1.10",
    ),
    _rq(
        "W38",
        "mobility_and_rehabilitation",
        "How are you getting on with the exercises the physio gave you, and have you started rehab or outpatient sessions yet?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG124 §1.10",
    ),

    # Day 29-60: longer-term recovery
    _rq(
        "W38",
        "mobility_and_rehabilitation",
        "Are you back to the level of independence you had before the fracture, or is there still support you're needing around the house?",
        [(29, 60)],
        "NG124 §1.10",
    ),
]


# ─── W38 Red Flag Probes ───────────────────────────────────────────────

W38_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ delirium_acute — 3 probes (all SAME_DAY) ═══════════════════════
    # Post-op delirium in elderly hip-fracture patients is common and
    # time-sensitive but not a 999 emergency on its own; NG124 §1.6
    # expects same-day clinical review. Probes split into three classic
    # features: acute onset confusion, agitation/distress, and
    # perceptual disturbance (hallucinations). Wording uses carer-
    # observed framing since the patient may not self-recognise the
    # change — this is a coverage-check question per the module
    # docstring's baseline-comparison rule.
    "delirium_acute_confusion_onset": RedFlagProbe(
        flag_code="delirium_acute_confusion_onset",
        parent_flag_code="delirium_acute",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG124 §1.6",
        patient_facing_question=(
            "Has anyone around you said you've become more confused or "
            "drowsy in the last day or two — trouble keeping track of "
            "conversations, forgetting what you just said?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "delirium_acute_agitation": RedFlagProbe(
        flag_code="delirium_acute_agitation",
        parent_flag_code="delirium_acute",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG124 §1.6",
        patient_facing_question=(
            "Has anyone around you noticed you've been unusually restless, "
            "agitated, or distressed — particularly in the evenings or at night?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "delirium_acute_perceptual": RedFlagProbe(
        flag_code="delirium_acute_perceptual",
        parent_flag_code="delirium_acute",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG124 §1.6",
        patient_facing_question=(
            "Have you — or has anyone with you noticed you — been seeing or "
            "hearing things that other people don't?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: delirium_acute probes set to SAME_DAY per
    # NG124 §1.6. Reviewer to confirm whether severe agitation posing
    # an immediate safety risk should escalate to EMERGENCY_999, and
    # whether this is a compound rule (perceptual + agitation firing
    # together) for Phase 4 call-status logic rather than at the probe
    # layer here.

    # ══ dvt_symptoms — split by leg (both EMERGENCY_999) ═══════════════
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
            "in the last 24 hours, separate from the general post-op swelling?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ pe_symptoms — 2 probes (same pattern as W37/W40) ═══════════════
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

    # ══ wound_infection — 2 probes ═════════════════════════════════════
    # W38 upstream uses 'wound_infection' parent (not 'wound_dehiscence'
    # as in W37/W40). Same splitting logic: spreading-redness and
    # discharge as distinct observations.
    #
    # Escalation tiers for W38 are higher than W37/W40's wound_infection
    # equivalents: elderly hip-fracture cohort has substantially higher
    # sepsis mortality than elective arthroplasty cohorts, so spreading
    # redness is escalated to EMERGENCY_999 rather than SAME_DAY.
    "wound_infection_spreading_redness": RedFlagProbe(
        flag_code="wound_infection_spreading_redness",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.SEPSIS_SIGNS,
        nice_basis="QS48 / NG124 §1.8 / NG51",
        patient_facing_question=(
            "Has the redness around the wound spread beyond the immediate scar area in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "wound_infection_discharge": RedFlagProbe(
        flag_code="wound_infection_discharge",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG124 §1.8",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: W38 wound_infection_spreading_redness is
    # escalated to EMERGENCY_999 (vs SAME_DAY for the equivalent W37/W40
    # wound_dehiscence_discharge / W43 wound_infection_spreading_redness
    # probes). Rationale is cohort-specific: elderly hip-fracture
    # patients have higher sepsis mortality than elective arthroplasty
    # cohorts, and spreading cellulitis on this cohort warrants 999
    # rather than same-day GP review. Reviewer to confirm or moderate
    # this cohort-based escalation delta.

    # ══ falls_with_injury — 3 probes ═══════════════════════════════════
    # Elderly cohort, often on anticoagulants. Probes split by what
    # was injured and how badly:
    #   - new pain after a fall → SAME_DAY (soft tissue / minor injury)
    #   - head strike → EMERGENCY_999 (intracranial haemorrhage risk
    #     on anticoagulation)
    #   - cannot bear weight after a fall → EMERGENCY_999 (refracture
    #     or implant failure suspected)
    "falls_with_injury_new_pain": RedFlagProbe(
        flag_code="falls_with_injury_new_pain",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS16 / NG124 §1.10",
        patient_facing_question=(
            "If you've had a fall, has it left you with any new pain — in "
            "your arms, shoulders, back, or the other hip?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "falls_with_injury_head_strike": RedFlagProbe(
        flag_code="falls_with_injury_head_strike",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS16 / NG124 §1.10",
        patient_facing_question=(
            "If you've had a fall, did you hit your head, black out, or can't remember the fall itself?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "falls_with_injury_cannot_weight_bear": RedFlagProbe(
        flag_code="falls_with_injury_cannot_weight_bear",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS16 / NG124 §1.10",
        patient_facing_question=(
            "If you've had a fall, have you found you can't put weight on the operated leg at all since?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# W43 — Unicompartmental Knee Replacement
# ═══════════════════════════════════════════════════════════════════════
#
# UKR is a smaller intervention than TKR — only one compartment of
# the knee is replaced. Recovery is faster, monitoring window is
# shorter (42 days vs 60 for TKR/THR).
#
# Divergences from W40 (TKR) worth flagging for the reviewer:
#   - No infection_signs as a separate trajectory domain (absent from
#     benchmarks.py for W43 and from pathway_map.monitoring_domains).
#     Infection monitoring happens via wound_healing RQ phrasing +
#     the wound_infection red flag probe.
#   - persistent_swelling replaces knee_effusion_severe as the
#     pathway-specific red flag. 'Persistent' means swelling lasting
#     past the expected resolution window (~4 weeks) and is the
#     classic presentation of unicompartmental implant failure, late
#     haemarthrosis, or prosthetic joint infection. Three probes:
#     contralateral-knee comparison (concrete anchor), swelling-with-
#     functional-pain (behavioural anchor), swelling-with-warmth-or-
#     spreading-redness (infection overlap).
#   - No fever_above_38_5 red flag in pathway_map for W43 (vs present
#     in W37/W40). CLINICAL_REVIEW_NEEDED below — may be an oversight
#     in the upstream map; SSI surveillance per QS48 applies to all
#     surgical wounds.
#   - VTE 14-day course (same as W40 TKR, shorter than W37/W38).

W43_PLAYBOOK = PathwayPlaybook(
    opcs_code="W43",
    label="Unicompartmental Knee Replacement",
    category="surgical",
    nice_ids=["NG226", "QS48", "QS89"],
    monitoring_window_days=42,
    call_days=[1, 3, 7, 14, 21, 28, 42],
    domains=[
        "wound_healing",
        "pain_management",
        "vte_prophylaxis",
        "mobility_progress",
        "physiotherapy_compliance",
    ],
    red_flag_codes=[
        "dvt_symptoms",
        "wound_infection",
        "pe_symptoms",
        "persistent_swelling",
        "fever_above_38_5",
    ],
    validation_status=_DRAFT,
)


W43_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG226 §1.8
    _traj("W43", "wound_healing",  1, 2, 3, "Wound intact, bruising expected", "NG226"),
    _traj("W43", "wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG226"),
    _traj("W43", "wound_healing",  7, 1, 2, "Wound closing, sutures in place", "NG226"),
    _traj("W43", "wound_healing", 14, 1, 2, "Healing well", "NG226"),
    _traj("W43", "wound_healing", 21, 1, 1, "Well healed", "NG226"),
    _traj("W43", "wound_healing", 28, 0, 1, "Healed", "NG226"),
    _traj("W43", "wound_healing", 42, 0, 0, "Fully healed", "NG226"),

    # pain_management — NG226 §1.6
    _traj("W43", "pain_management",  1, 2, 3, "Moderate pain expected", "NG226"),
    _traj("W43", "pain_management",  3, 2, 3, "Pain reducing with analgesia", "NG226"),
    _traj("W43", "pain_management",  7, 1, 2, "Mild-moderate pain at activity", "NG226"),
    _traj("W43", "pain_management", 14, 1, 2, "Mild pain reducing", "NG226"),
    _traj("W43", "pain_management", 21, 1, 1, "Minimal pain", "NG226"),
    _traj("W43", "pain_management", 28, 0, 1, "Resolving", "NG226"),
    _traj("W43", "pain_management", 42, 0, 1, "Resolved or minimal", "NG226"),

    # vte_prophylaxis — NG89 §1.9 (14-day course for UKR, same as TKR)
    _traj("W43", "vte_prophylaxis",  1, 1, 2, "Anticoagulant commenced", "NG89"),
    _traj("W43", "vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("W43", "vte_prophylaxis",  7, 1, 2, "Adherent — 14-day course", "NG89"),
    _traj("W43", "vte_prophylaxis", 14, 1, 1, "Course completed", "NG89"),
    _traj("W43", "vte_prophylaxis", 21, 0, 1, "Completed", "NG89"),
    _traj("W43", "vte_prophylaxis", 28, 0, 1, "Completed", "NG89"),
    _traj("W43", "vte_prophylaxis", 42, 0, 0, "N/A", "NG89"),

    # mobility_progress — NG226 §1.10 (faster recovery than TKR)
    _traj("W43", "mobility_progress",  1, 2, 3, "Walking with crutches expected", "NG226"),
    _traj("W43", "mobility_progress",  3, 2, 2, "Short distance mobilisation", "NG226"),
    _traj("W43", "mobility_progress",  7, 1, 2, "Increasing mobility", "NG226"),
    _traj("W43", "mobility_progress", 14, 1, 2, "Good progress", "NG226"),
    _traj("W43", "mobility_progress", 21, 1, 1, "Near-normal mobility", "NG226"),
    _traj("W43", "mobility_progress", 28, 0, 1, "Normal range expected", "NG226"),
    _traj("W43", "mobility_progress", 42, 0, 1, "Normal mobility", "NG226"),

    # physiotherapy_compliance — NG226 §1.11
    _traj("W43", "physiotherapy_compliance",  1, 1, 2, "Exercises commenced", "NG226"),
    _traj("W43", "physiotherapy_compliance",  3, 1, 2, "Daily exercises ongoing", "NG226"),
    _traj("W43", "physiotherapy_compliance",  7, 1, 2, "Outpatient physio commenced", "NG226"),
    _traj("W43", "physiotherapy_compliance", 14, 1, 1, "Attending physio", "NG226"),
    _traj("W43", "physiotherapy_compliance", 21, 1, 1, "Regular physio", "NG226"),
    _traj("W43", "physiotherapy_compliance", 28, 1, 1, "Ongoing adherence", "NG226"),
    _traj("W43", "physiotherapy_compliance", 42, 0, 1, "Programme completing", "NG226"),
]


W43_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Wound RQ retains a narrative fever prompt even though W43 now has
    # a 3-probe fever_above_38_5 set. W43 has no infection_signs domain
    # (unlike W37/W40) so this RQ is the sole narrative hook for
    # systemic-infection signs; the probes provide the binary red-flag
    # checks on top.
    _rq(
        "W43",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, fluid coming from it, or a fever in the last 24 hours?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.8 / QS48",
    ),
    _rq(
        "W43",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable enough to move around and do your exercises?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG226 §1.6",
    ),
    _rq(
        "W43",
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14)],
        "NG89 §1.9",
    ),
    _rq(
        "W43",
        "mobility_progress",
        "How are you getting around — what walking aids you're using, distance you're managing, and stairs?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 42)],
        "NG226 §1.10",
    ),
    _rq(
        "W43",
        "physiotherapy_compliance",
        "How are you getting on with the physio exercises — doing them at home, and have you started outpatient sessions yet?",
        [(4, 7), (8, 14), (15, 28), (29, 42)],
        "NG226 §1.11",
    ),

    # Day 15-28: range of movement progress
    _rq(
        "W43",
        "mobility_progress",
        "How is the knee bending and straightening — any particular movements that still feel stiff or stuck?",
        [(15, 28), (29, 42)],
        "NG226 §1.10",
    ),

    # Day 29-42: programme completion
    _rq(
        "W43",
        "physiotherapy_compliance",
        "How's physio going overall — nearing the end of your sessions, or still working on specific goals?",
        [(29, 42)],
        "NG226 §1.11",
    ),
]


# ─── W43 Red Flag Probes ───────────────────────────────────────────────

W43_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ dvt_symptoms — split by leg (both EMERGENCY_999) ═══════════════
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
            "in the last 24 hours, separate from the general post-op swelling?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ wound_infection — 2 probes (same pattern as W38) ═══════════════
    "wound_infection_spreading_redness": RedFlagProbe(
        flag_code="wound_infection_spreading_redness",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG226 §1.8",
        patient_facing_question=(
            "Has the redness around the wound spread beyond the immediate scar area in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "wound_infection_discharge": RedFlagProbe(
        flag_code="wound_infection_discharge",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG226 §1.8",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ pe_symptoms — 2 probes (same pattern as W37/W38/W40) ═══════════
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

    # ══ persistent_swelling — 3 probes (all SAME_DAY) ══════════════════
    # UKR-specific. Persistent swelling past the expected ~4-week
    # resolution window is the classic presentation of unicompartmental
    # implant failure, late haemarthrosis, or prosthetic joint infection.
    # Probes use concrete anchors:
    #   - contralateral-knee comparison (patient checks both knees now)
    #   - swelling-with-functional-pain (behavioural anchor)
    #   - swelling-with-warmth-or-spreading-redness (infection overlap)
    "persistent_swelling_vs_other_knee": RedFlagProbe(
        flag_code="persistent_swelling_vs_other_knee",
        parent_flag_code="persistent_swelling",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8",
        patient_facing_question=(
            "Putting your hands around both knees right now — is the operated "
            "knee still noticeably larger than the other one?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "persistent_swelling_with_pain": RedFlagProbe(
        flag_code="persistent_swelling_with_pain",
        parent_flag_code="persistent_swelling",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "In the last 24 hours, has the swelling and pain stopped you walking, doing your exercises, or sleeping?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "persistent_swelling_with_warmth": RedFlagProbe(
        flag_code="persistent_swelling_with_warmth",
        parent_flag_code="persistent_swelling",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG226 §1.8 / QS48",
        patient_facing_question=(
            "Has the swollen knee become hot to the touch, or has redness spread beyond the immediate wound area?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ fever_above_38_5 — 3 probes: reading, symptoms, rigors ═════════
    # Ported verbatim from W37/W40 with identical thresholds and
    # escalations. QS48 SSI surveillance applies to all surgical wounds
    # including UKR.
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

    # CLINICAL_REVIEW_NEEDED: fever probe thresholds ported verbatim
    # from W40 (TKR). UKR is a smaller intervention with a lower SSI
    # baseline rate than TKR — reviewer to confirm whether the same
    # 38°C / rigors thresholds and escalations are calibrated correctly
    # for UKR, or whether the cohort permits a slightly higher trigger
    # threshold. Presence of the probe set is not in question; only
    # calibration.
    #
    # CLINICAL_REVIEW_NEEDED: persistent_swelling probes all SAME_DAY.
    # Reviewer to confirm that co-firing of persistent_swelling_with_
    # pain AND persistent_swelling_with_warmth should escalate to
    # EMERGENCY_999 at the Phase 4 call-status layer (suggests acute
    # prosthetic joint infection, which is a surgical emergency).
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "W37": W37_PLAYBOOK,
    "W38": W38_PLAYBOOK,
    "W40": W40_PLAYBOOK,
    "W43": W43_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "W37": W37_TRAJECTORIES,
    "W38": W38_TRAJECTORIES,
    "W40": W40_TRAJECTORIES,
    "W43": W43_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "W37": W37_REQUIRED_QUESTIONS,
    "W38": W38_REQUIRED_QUESTIONS,
    "W40": W40_REQUIRED_QUESTIONS,
    "W43": W43_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "W37": W37_RED_FLAG_PROBES,
    "W38": W38_RED_FLAG_PROBES,
    "W40": W40_RED_FLAG_PROBES,
    "W43": W43_RED_FLAG_PROBES,
}

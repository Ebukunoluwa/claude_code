"""Obstetric pathways — R17 (elective C-section), R18 (emergency C-section).

Phase 3 status: **R17 and R18** complete.

Content sources:
  - Trajectories ported from app/clinical_intelligence/benchmarks.py
    (which originally sourced from the voice-agent clinical_intelligence.py
    monolith). Values unchanged from the existing benchmarks table; every
    row now carries validation_status='draft_awaiting_clinical_review'.
  - Playbook metadata ported from the monolith PLAYBOOKS dict at
    healthcare-voice-agent/agent/clinical_intelligence.py.
  - Required Questions and Red Flag Probes are NET-NEW Phase 3 content
    drafted from the cited NICE sections. Every entry tagged
    draft_awaiting_clinical_review.

Domain naming: uses the benchmarks.py naming convention
(wound_healing_pfannenstiel, lochia_pattern, lmwh_adherence,
breastfeeding_support, postnatal_depression_screen, mobility_progress,
pain_management). The monolith PLAYBOOK used shorter shared-name
domains (wound_healing, vte_prophylaxis, etc.) — the more specific
names here are per PLAN.md §Q1 "cluster-specific domains" decision.

Red Flag Probes: one observation per probe. Upstream machine-readable
flag codes from monolith are wound_dehiscence, postpartum_haemorrhage,
pe_symptoms, pre_eclampsia_signs, postnatal_depression_severe,
infant_feeding_failure — each splits into multiple probes linked via
parent_flag_code per PLAN.md §4 template principle.

Primary NICE sources: NG192 (postnatal care), QS32, NG194 (maternity
services), NG89 (VTE prevention). Reviewer specialty: obstetrician
and/or community midwifery lead.
"""
from ..models import (
    DomainTrajectoryEntry,
    EscalationTier,
    PathwayPlaybook,
    RedFlagCategory,
    RedFlagProbe,
    RequiredQuestion,
)


_R17_NICE_IDS = ["NG192", "QS32", "NG194", "NG89"]
_DRAFT = "draft_awaiting_clinical_review"


# ═══════════════════════════════════════════════════════════════════════
# R17 — Elective Caesarean Section
# ═══════════════════════════════════════════════════════════════════════

R17_PLAYBOOK = PathwayPlaybook(
    opcs_code="R17",
    label="Elective Caesarean Section",
    category="obstetric",
    nice_ids=_R17_NICE_IDS,
    monitoring_window_days=42,
    call_days=[1, 3, 5, 7, 10, 14, 21, 28],
    domains=[
        "wound_healing_pfannenstiel",
        "lochia_pattern",
        "pain_management",
        "lmwh_adherence",
        "breastfeeding_support",
        "postnatal_depression_screen",
        "mobility_progress",
    ],
    red_flag_codes=[
        "wound_dehiscence",
        "postpartum_haemorrhage",
        "pe_symptoms",
        "pre_eclampsia_signs",
        "postnatal_depression_severe",
        "infant_feeding_failure",
    ],
    validation_status=_DRAFT,
)


# ─── R17 Domain Trajectories (ported from benchmarks.py) ───────────────
# Preserved exactly from the existing benchmarks table. Each row now
# carries draft_awaiting_clinical_review. CLINICAL_REVIEW_NEEDED flags
# are noted where the existing data felt uncertain during the port.

def _traj(
    domain: str,
    day: int,
    expected: int,
    upper: int,
    state: str,
    nice: str,
) -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code="R17",
        domain=domain,
        day_range_start=day,
        day_range_end=day,
        expected_score=expected,
        upper_bound_score=upper,
        expected_state=state,
        nice_source=nice,
        validation_status=_DRAFT,
    )


R17_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing_pfannenstiel — NG192 §1.5.3
    _traj("wound_healing_pfannenstiel",  1, 2, 3, "Wound dressed, bruising and swelling expected", "NG192"),
    _traj("wound_healing_pfannenstiel",  3, 2, 3, "Minor seepage acceptable, edges intact", "NG192"),
    _traj("wound_healing_pfannenstiel",  5, 1, 2, "Wound closing, check for signs of infection", "NG192"),
    _traj("wound_healing_pfannenstiel",  7, 1, 2, "Sutures/clips due for removal if not dissolvable", "NG192"),
    _traj("wound_healing_pfannenstiel", 10, 1, 2, "Wound healing well", "NG192"),
    _traj("wound_healing_pfannenstiel", 14, 0, 1, "Healed or near-healed", "NG192"),
    _traj("wound_healing_pfannenstiel", 21, 0, 1, "Well healed", "NG192"),
    _traj("wound_healing_pfannenstiel", 28, 0, 0, "Fully healed", "NG192"),

    # lochia_pattern — NG192 §1.5.8
    _traj("lochia_pattern",  1, 1, 2, "Bright red lochia expected, heavy flow normal", "NG192"),
    _traj("lochia_pattern",  3, 1, 2, "Darkening to red-brown, reducing", "NG192"),
    _traj("lochia_pattern",  5, 1, 2, "Reducing flow, pinkish-brown", "NG192"),
    _traj("lochia_pattern",  7, 1, 2, "Light flow, yellow-white discharge acceptable", "NG192"),
    _traj("lochia_pattern", 10, 1, 1, "Light or no lochia", "NG192"),
    _traj("lochia_pattern", 14, 0, 1, "Minimal discharge", "NG192"),
    _traj("lochia_pattern", 21, 0, 1, "Should have stopped", "NG192"),
    _traj("lochia_pattern", 28, 0, 0, "Resolved", "NG192"),

    # pain_management — NG192 §1.6
    _traj("pain_management",  1, 2, 3, "Moderate pain expected, regular analgesia required", "NG192"),
    _traj("pain_management",  3, 2, 3, "Pain reducing with paracetamol/ibuprofen", "NG192"),
    _traj("pain_management",  5, 2, 2, "Mild-moderate pain at activity", "NG192"),
    _traj("pain_management",  7, 1, 2, "Mild pain, reducing analgesic need", "NG192"),
    _traj("pain_management", 10, 1, 2, "Mild pain at activity", "NG192"),
    _traj("pain_management", 14, 1, 1, "Minimal pain", "NG192"),
    _traj("pain_management", 21, 0, 1, "Pain resolving", "NG192"),
    _traj("pain_management", 28, 0, 1, "Pain resolved or minimal", "NG192"),

    # lmwh_adherence — NG89 §1.3
    # CLINICAL_REVIEW_NEEDED: standard 10-day LMWH course vs 28-day for
    # high-risk. Existing trajectory assumes standard-risk elective; reviewer
    # to confirm whether this pathway should fork by risk factor.
    _traj("lmwh_adherence",  1, 1, 2, "LMWH started — daily injection adherence expected", "NG89"),
    _traj("lmwh_adherence",  3, 1, 2, "Adherent", "NG89"),
    _traj("lmwh_adherence",  5, 1, 2, "Adherent", "NG89"),
    _traj("lmwh_adherence",  7, 1, 2, "Adherent — 10-day course for elective", "NG89"),
    _traj("lmwh_adherence", 10, 0, 1, "Course completed for standard-risk", "NG89"),
    _traj("lmwh_adherence", 14, 0, 1, "Course completed or continuing if high-risk", "NG89"),
    _traj("lmwh_adherence", 21, 0, 1, "N/A unless extended course", "NG89"),
    _traj("lmwh_adherence", 28, 0, 0, "N/A", "NG89"),

    # breastfeeding_support — NG194 §1.4
    _traj("breastfeeding_support",  1, 1, 2, "Initiating feeding, skin-to-skin encouraged", "NG192"),
    _traj("breastfeeding_support",  3, 1, 2, "Milk coming in, latch assessment", "NG192"),
    _traj("breastfeeding_support",  5, 1, 2, "Establishing feeding routine", "NG192"),
    _traj("breastfeeding_support",  7, 1, 1, "Feeding established or formula supplement if needed", "NG192"),
    _traj("breastfeeding_support", 10, 1, 1, "Routine feeding", "NG192"),
    _traj("breastfeeding_support", 14, 0, 1, "Feeding well established", "NG192"),
    _traj("breastfeeding_support", 21, 0, 1, "Ongoing support available", "NG192"),
    _traj("breastfeeding_support", 28, 0, 1, "Feeding established", "NG192"),

    # postnatal_depression_screen — NG192 §1.6 / CG192
    # CLINICAL_REVIEW_NEEDED: EPDS timing — draft has "screen recommended
    # at 2 weeks" (day 14) and "screen recommended at 4 weeks" (day 28).
    # NICE guidance varies between day 10-14 formal EPDS and deferring to
    # 6-week GP check. Reviewer to set which call(s) formally administer EPDS.
    _traj("postnatal_depression_screen",  1, 1, 2, "Baby blues common days 3-5, monitor mood", "NG192"),
    _traj("postnatal_depression_screen",  3, 1, 2, "Baby blues peak, reassure, monitor", "NG192"),
    _traj("postnatal_depression_screen",  5, 1, 2, "Baby blues should begin to lift", "NG192"),
    _traj("postnatal_depression_screen",  7, 1, 2, "Mood improving expected", "NG192"),
    _traj("postnatal_depression_screen", 10, 1, 1, "Mood stabilising", "NG192"),
    _traj("postnatal_depression_screen", 14, 1, 1, "EPDS screen recommended at 2 weeks", "NG192"),
    _traj("postnatal_depression_screen", 21, 0, 1, "Mood improving", "NG192"),
    _traj("postnatal_depression_screen", 28, 0, 1, "EPDS screen recommended at 4 weeks", "NG192"),

    # mobility_progress — NG192 §1.7
    _traj("mobility_progress",  1, 2, 3, "Short walks with support encouraged", "NG192"),
    _traj("mobility_progress",  3, 2, 3, "Increasing movement, avoid heavy lifting", "NG192"),
    _traj("mobility_progress",  5, 2, 2, "Short walks indoors, stair caution", "NG192"),
    _traj("mobility_progress",  7, 1, 2, "Gentle mobilising at home", "NG192"),
    _traj("mobility_progress", 10, 1, 2, "Increasing activity", "NG192"),
    _traj("mobility_progress", 14, 1, 1, "Near-normal light activity", "NG192"),
    _traj("mobility_progress", 21, 1, 1, "Driving possible from 5-6 weeks if comfortable", "NG192"),
    _traj("mobility_progress", 28, 0, 1, "Gradual return to activity", "NG192"),
]


# ─── R17 Required Questions Manifest (net-new Phase 3 content) ─────────
# Day bands: (1,3) / (4,7) / (8,14) / (15,28) covering the R17 window.
# Multi-part phrasing permitted — each part must be independently
# scoreable from the transcript.

def _rq(
    domain: str,
    text: str,
    bands: list[tuple[int, int]],
    nice: str,
) -> RequiredQuestion:
    return RequiredQuestion(
        opcs_code="R17",
        domain=domain,
        question_text=text,
        required=True,
        day_ranges=bands,
        validation_status=_DRAFT,
    )


R17_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Day 1-3 emphasis: immediate post-discharge safety + establishing care
    _rq(
        "wound_healing_pfannenstiel",
        "How is the wound looking — any redness, swelling, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14)],
        "NG192 §1.5.3",
    ),
    _rq(
        "lochia_pattern",
        "How is your bleeding — how much blood are you losing, what colour, and are there any clots?",
        [(1, 3), (4, 7), (8, 14)],
        "NG192 §1.5.8",
    ),
    _rq(
        "pain_management",
        "How are you managing pain — are the painkillers helping enough to move around and care for the baby?",
        [(1, 3), (4, 7)],
        "NG192 §1.6",
    ),
    _rq(
        "lmwh_adherence",
        "Are you taking the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14)],
        "NG89 §1.3",
    ),
    _rq(
        "breastfeeding_support",
        "How is feeding going — breast, bottle, or both, and is the baby settling?",
        [(1, 3), (4, 7), (8, 14)],
        "NG194 §1.4",
    ),

    # Day 4-7 emphasis: function + adherence consolidation
    _rq(
        "mobility_progress",
        "How much are you able to move around — walking indoors, using stairs, lifting the baby?",
        [(4, 7), (8, 14), (15, 28)],
        "NG192 §1.7",
    ),
    _rq(
        "postnatal_depression_screen",
        "How are you feeling in yourself — beyond the tiredness, any low mood or worry that's been hard to shake?",
        [(4, 7), (8, 14), (15, 28)],
        "NG192 §1.6",
    ),

    # Day 8-14 / 15-28 emphasis: coverage check for clinician-administered EPDS
    # Corrected from draft (which had the voice agent attempt to administer
    # EPDS directly). The voice agent now asks whether the patient's own
    # care team has run a mood questionnaire — a coverage audit question,
    # not an administration question.
    _rq(
        "postnatal_depression_screen",
        "Has anyone from your care team done a mood questionnaire with you since you got home?",
        [(8, 14), (15, 28)],
        "NG192 §1.6 / CG192",
    ),
    # CLINICAL_REVIEW_NEEDED: the reviewer may want to reintroduce voice-agent
    # EPDS administration if their trust permits it. Current draft is the
    # conservative position — voice agent confirms coverage by the clinician
    # team rather than running the instrument itself.

    # Day 15-28 emphasis: psychosocial, contraception, return to normal
    _rq(
        "mobility_progress",
        "How are you doing with day-to-day activities — things like light housework, driving, or any exercise?",
        [(15, 28)],
        "NG192 §1.7",
    ),
    _rq(
        "breastfeeding_support",
        "Is feeding still going well, or any worries about the baby's weight or feeding pattern?",
        [(15, 28)],
        "NG194 §1.4",
    ),
    # CLINICAL_REVIEW_NEEDED: should contraception_and_sexual_health be an
    # R17 Required Question from day 15+ (per NG194 §1.8)? It has no entry
    # in the benchmarks trajectory set; reviewer to decide whether to add
    # a scoring domain or handle via the question only.
]


# ─── R17 Red Flag Probes (net-new Phase 3 content) ─────────────────────
# One observation per probe. Upstream codes split into suffixed variants
# with parent_flag_code preserved for dashboard aggregation.

R17_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ postpartum_haemorrhage — 3 probes, all 999 ══════════════════════
    "postpartum_haemorrhage_volume": RedFlagProbe(
        flag_code="postpartum_haemorrhage_volume",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you been soaking through a maternity pad in less than an hour?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "postpartum_haemorrhage_clots": RedFlagProbe(
        flag_code="postpartum_haemorrhage_clots",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you passed any clots that were bigger than a 50p coin?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "postpartum_haemorrhage_haemodynamic": RedFlagProbe(
        flag_code="postpartum_haemorrhage_haemodynamic",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you felt faint, dizzy, or lightheaded — especially when you stand up?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ wound_dehiscence — 2 probes ══════════════════════════════════════
    "wound_dehiscence_gaping": RedFlagProbe(
        flag_code="wound_dehiscence_gaping",
        parent_flag_code="wound_dehiscence",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG192 §1.5.3",
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
        nice_basis="NG192 §1.5.3",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
        # CLINICAL_REVIEW_NEEDED: reviewer to split further if needed —
        # pus alone (sign of infection) may merit a different tier to
        # bloody discharge (sign of reopening).
    ),

    # ══ pe_symptoms (pulmonary embolism) — 3 probes ═════════════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.3 / NG158",
        # Retroactive wording fix to align with the no-memory-comparison
        # rule established during W40 drafting. Was: "that wasn't there
        # before" — memory-comparison phrasing. Now: concrete behavioural
        # anchor (stopped what you were doing today).
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
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Any sharp chest pain — especially when you breathe in deeply?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pe_symptoms_calf_signs": RedFlagProbe(
        flag_code="pe_symptoms_calf_signs",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Any pain, swelling, redness, or warmth in one of your calves — "
            "especially tender when you press on it?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: calf DVT probe is a close cousin clinically
    # (DVT is the precursor to PE). Currently parented under pe_symptoms;
    # reviewer to decide whether it belongs there long-term or warrants
    # a dedicated dvt_signs upstream code with its own probes.

    # ══ pre_eclampsia_signs — 3 probes, all EMERGENCY_999 ═══════════════
    # Corrected from draft SAME_DAY during review. Postnatal severe
    # headache, visual disturbance, or epigastric pain is imminent
    # eclampsia per NG133 §1.5 — requires 999 escalation, not same-day.
    "pre_eclampsia_headache": RedFlagProbe(
        flag_code="pre_eclampsia_headache",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Have you had a severe headache that doesn't go away with simple painkillers?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pre_eclampsia_visual": RedFlagProbe(
        flag_code="pre_eclampsia_visual",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Any changes to your vision — blurring, flashing lights, or spots?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pre_eclampsia_epigastric": RedFlagProbe(
        flag_code="pre_eclampsia_epigastric",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Any pain in the upper right part of your tummy, just below the ribs?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ postnatal_depression_severe — 2 probes (tier-differentiated) ═══
    "postnatal_depression_passive_ideation": RedFlagProbe(
        flag_code="postnatal_depression_passive_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192 §1.9",
        patient_facing_question=(
            "Have you had any thoughts that you or your family would be better "
            "off without you?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
        # CLINICAL_REVIEW_NEEDED: reviewer to confirm SAME_DAY for passive
        # ideation vs EMERGENCY_999. Current draft differentiates from active
        # but passive ideation on a postnatal patient may warrant urgent
        # review even absent active intent.
    ),
    "postnatal_depression_active_ideation": RedFlagProbe(
        flag_code="postnatal_depression_active_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192 §1.9",
        patient_facing_question=(
            "Have you had any thoughts about harming yourself, or about ending "
            "your own life?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ infant_feeding_failure — 2 probes ═══════════════════════════════
    "infant_feeding_weight_concern": RedFlagProbe(
        flag_code="infant_feeding_weight_concern",
        parent_flag_code="infant_feeding_failure",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG194 §1.4",
        patient_facing_question=(
            "Has the midwife raised any concerns about the baby's weight — "
            "weight loss or slow weight gain?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "infant_feeding_intake": RedFlagProbe(
        flag_code="infant_feeding_intake",
        parent_flag_code="infant_feeding_failure",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG194 §1.4",
        patient_facing_question=(
            "Is the baby having at least six wet nappies a day?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# R18 — Emergency Caesarean Section
# ═══════════════════════════════════════════════════════════════════════
#
# Differs from R17 in: traumatic birth context, emotional processing +
# PTSD screening as explicit domains, longer LMWH course (28-day high-
# risk is the norm, not exception), slower mobility recovery. Shares
# most R17 structure.
#
# Decisions during port (not open flags):
#   mobility_progress included with upper_bound raised +1 on days 1, 3,
#     5, 7 vs R17 (slower emergency-surgery mobilisation). Days 10+
#     unchanged. Added to domain list; trajectory + required question
#     included below.
#   NG89 added to nice_ids vs monolith — extended LMWH is the primary
#     R18 scenario, not an edge case.

R18_PLAYBOOK = PathwayPlaybook(
    opcs_code="R18",
    label="Emergency Caesarean Section",
    category="obstetric",
    nice_ids=["NG192", "NG194", "QS32", "NG89"],
    monitoring_window_days=42,
    call_days=[1, 3, 5, 7, 10, 14, 21, 28],
    domains=[
        "wound_healing_pfannenstiel",
        "lochia_pattern",
        "pain_management",
        "lmwh_adherence",
        "mobility_progress",
        "emotional_processing_of_birth",
        "ptsd_screening",
        "postnatal_depression_screen",
        "breastfeeding_support",
    ],
    red_flag_codes=[
        "wound_dehiscence",
        "postpartum_haemorrhage",
        "pe_symptoms",
        "pre_eclampsia_signs",
        "postnatal_depression_severe",
        "ptsd_symptoms",
    ],
    validation_status=_DRAFT,
)


def _traj18(
    domain: str, day: int, expected: int, upper: int, state: str, nice: str,
) -> DomainTrajectoryEntry:
    return DomainTrajectoryEntry(
        opcs_code="R18",
        domain=domain,
        day_range_start=day,
        day_range_end=day,
        expected_score=expected,
        upper_bound_score=upper,
        expected_state=state,
        nice_source=nice,
        validation_status=_DRAFT,
    )


R18_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing_pfannenstiel — NG192 §1.5.3 (same as R17)
    _traj18("wound_healing_pfannenstiel",  1, 2, 3, "Wound dressed, bruising and swelling expected", "NG192"),
    _traj18("wound_healing_pfannenstiel",  3, 2, 3, "Minor seepage acceptable, edges intact", "NG192"),
    _traj18("wound_healing_pfannenstiel",  5, 1, 2, "Wound closing, check for signs of infection", "NG192"),
    _traj18("wound_healing_pfannenstiel",  7, 1, 2, "Sutures/clips due for removal if applicable", "NG192"),
    _traj18("wound_healing_pfannenstiel", 10, 1, 2, "Wound healing well", "NG192"),
    _traj18("wound_healing_pfannenstiel", 14, 0, 1, "Healed or near-healed", "NG192"),
    _traj18("wound_healing_pfannenstiel", 21, 0, 1, "Well healed", "NG192"),
    _traj18("wound_healing_pfannenstiel", 28, 0, 0, "Fully healed", "NG192"),

    # lochia_pattern — NG192 §1.5.8 (same as R17)
    _traj18("lochia_pattern",  1, 1, 2, "Bright red lochia expected, heavy flow normal", "NG192"),
    _traj18("lochia_pattern",  3, 1, 2, "Darkening to red-brown, reducing", "NG192"),
    _traj18("lochia_pattern",  5, 1, 2, "Reducing flow, pinkish-brown", "NG192"),
    _traj18("lochia_pattern",  7, 1, 2, "Light flow, yellow-white discharge acceptable", "NG192"),
    _traj18("lochia_pattern", 10, 1, 1, "Light or no lochia", "NG192"),
    _traj18("lochia_pattern", 14, 0, 1, "Minimal discharge", "NG192"),
    _traj18("lochia_pattern", 21, 0, 1, "Should have stopped", "NG192"),
    _traj18("lochia_pattern", 28, 0, 0, "Resolved", "NG192"),

    # pain_management — NG192 §1.6 (higher severity early vs R17)
    _traj18("pain_management",  1, 2, 3, "Moderate-severe pain expected post-emergency surgery", "NG192"),
    _traj18("pain_management",  3, 2, 3, "Pain reducing with analgesia", "NG192"),
    _traj18("pain_management",  5, 2, 2, "Mild-moderate pain", "NG192"),
    _traj18("pain_management",  7, 2, 3, "Mild pain, reducing analgesic need", "NG192"),
    _traj18("pain_management", 10, 1, 2, "Mild pain at activity", "NG192"),
    _traj18("pain_management", 14, 1, 1, "Minimal pain", "NG192"),
    _traj18("pain_management", 21, 0, 1, "Pain resolving", "NG192"),
    _traj18("pain_management", 28, 0, 1, "Pain resolved or minimal", "NG192"),

    # lmwh_adherence — NG89 §1.3 (28-day extended course for emergency)
    _traj18("lmwh_adherence",  1, 1, 2, "LMWH started — higher-risk so extended course likely", "NG89"),
    _traj18("lmwh_adherence",  3, 1, 2, "Adherent", "NG89"),
    _traj18("lmwh_adherence",  5, 1, 2, "Adherent", "NG89"),
    _traj18("lmwh_adherence",  7, 1, 2, "Adherent", "NG89"),
    _traj18("lmwh_adherence", 10, 1, 2, "Continue if high-risk extended course (28 days)", "NG89"),
    _traj18("lmwh_adherence", 14, 1, 2, "Extended course ongoing for emergency/high-risk", "NG89"),
    _traj18("lmwh_adherence", 21, 1, 2, "Adherent — completing 28-day course", "NG89"),
    _traj18("lmwh_adherence", 28, 0, 1, "Course completed", "NG89"),

    # emotional_processing_of_birth — NG192/NG194 (new vs R17)
    _traj18("emotional_processing_of_birth",  1, 2, 3, "Distress from emergency common — listening and support", "NG192"),
    _traj18("emotional_processing_of_birth",  3, 2, 3, "Processing experience, debrief encouraged", "NG192"),
    _traj18("emotional_processing_of_birth",  5, 2, 2, "Ongoing processing, check for intrusive thoughts", "NG192"),
    _traj18("emotional_processing_of_birth",  7, 2, 2, "Monitor for PTSD symptoms", "NG194"),
    _traj18("emotional_processing_of_birth", 10, 1, 2, "Gradual adjustment expected", "NG194"),
    _traj18("emotional_processing_of_birth", 14, 1, 2, "EPDS and trauma screen at 2 weeks", "NG192"),
    _traj18("emotional_processing_of_birth", 21, 1, 1, "Mood and processing improving", "NG194"),
    _traj18("emotional_processing_of_birth", 28, 1, 1, "Formal PTSD assessment if concerns persist", "NG194"),

    # ptsd_screening — NG194/NG116 (new vs R17)
    _traj18("ptsd_screening",  1, 1, 2, "Monitor for re-experiencing, avoidance", "NG194"),
    _traj18("ptsd_screening",  3, 1, 2, "Hyperarousal and flashbacks common early", "NG194"),
    _traj18("ptsd_screening",  5, 1, 2, "Monitor for persistent symptoms", "NG194"),
    _traj18("ptsd_screening",  7, 1, 2, "Symptoms beyond 1 week warrant closer review", "NG194"),
    _traj18("ptsd_screening", 10, 1, 2, "Normalise but do not dismiss symptoms", "NG194"),
    _traj18("ptsd_screening", 14, 1, 2, "Screen with validated tool if symptomatic", "NG194"),
    _traj18("ptsd_screening", 21, 1, 1, "Improving or referral pathway initiated", "NG194"),
    _traj18("ptsd_screening", 28, 0, 1, "Resolved or under specialist care", "NG194"),

    # postnatal_depression_screen — NG192 §1.6 (amplified risk vs R17)
    _traj18("postnatal_depression_screen",  1, 1, 2, "Baby blues common, amplified by emergency birth", "NG192"),
    _traj18("postnatal_depression_screen",  3, 1, 2, "Monitor mood closely given traumatic birth context", "NG192"),
    _traj18("postnatal_depression_screen",  5, 1, 2, "Baby blues should begin to lift", "NG192"),
    _traj18("postnatal_depression_screen",  7, 2, 2, "Persistent low mood warrants closer monitoring", "NG192"),
    _traj18("postnatal_depression_screen", 10, 1, 2, "Mood stabilising expected", "NG192"),
    _traj18("postnatal_depression_screen", 14, 1, 2, "EPDS screen at 2 weeks — lower threshold for concern", "NG192"),
    _traj18("postnatal_depression_screen", 21, 1, 1, "Mood improving", "NG192"),
    _traj18("postnatal_depression_screen", 28, 1, 1, "EPDS screen at 4 weeks", "NG192"),

    # breastfeeding_support — NG194 §1.4 (delayed initiation possible)
    _traj18("breastfeeding_support",  1, 1, 2, "Delayed initiation possible after emergency birth", "NG192"),
    _traj18("breastfeeding_support",  3, 1, 2, "Milk coming in, additional support may be needed", "NG192"),
    _traj18("breastfeeding_support",  5, 1, 2, "Establishing feeding routine", "NG192"),
    _traj18("breastfeeding_support",  7, 1, 1, "Feeding established or formula supplement if needed", "NG192"),
    _traj18("breastfeeding_support", 10, 1, 1, "Routine feeding", "NG192"),
    _traj18("breastfeeding_support", 14, 0, 1, "Feeding well established", "NG192"),
    _traj18("breastfeeding_support", 21, 0, 1, "Ongoing support available", "NG192"),
    _traj18("breastfeeding_support", 28, 0, 1, "Feeding established", "NG192"),

    # mobility_progress — NG192 §1.7 (ported from R17 with upper_bound +1
    # on days 1, 3, 5, 7 for slower emergency-surgery mobilisation;
    # days 10+ unchanged).
    # CLINICAL_REVIEW_NEEDED: the +1 upper_bound shift is a calibration
    # choice during port — the clinical direction (slower mobility
    # recovery for emergency C-section) is defensible; the specific
    # magnitude (+1 on specific days) needs reviewer confirmation.
    _traj18("mobility_progress",  1, 2, 4, "Short walks with support encouraged", "NG192"),
    _traj18("mobility_progress",  3, 2, 4, "Increasing movement, avoid heavy lifting", "NG192"),
    _traj18("mobility_progress",  5, 2, 3, "Short walks indoors, stair caution", "NG192"),
    _traj18("mobility_progress",  7, 1, 3, "Gentle mobilising at home", "NG192"),
    _traj18("mobility_progress", 10, 1, 2, "Increasing activity", "NG192"),
    _traj18("mobility_progress", 14, 1, 1, "Near-normal light activity", "NG192"),
    _traj18("mobility_progress", 21, 1, 1, "Driving possible from 5-6 weeks if comfortable", "NG192"),
    _traj18("mobility_progress", 28, 0, 1, "Gradual return to activity", "NG192"),
]


def _rq18(
    domain: str, text: str, bands: list[tuple[int, int]], nice: str,
) -> RequiredQuestion:
    return RequiredQuestion(
        opcs_code="R18",
        domain=domain,
        question_text=text,
        required=True,
        day_ranges=bands,
        validation_status=_DRAFT,
    )


R18_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Core shared with R17 (wound, lochia, pain, LMWH, feeding).
    # Extended to day 15-28 for wound + lochia since benchmarks has
    # day 21/28 trajectory data for both domains — Sarah probes for
    # the full monitoring window.
    _rq18(
        "wound_healing_pfannenstiel",
        "How is the wound looking — any redness, swelling, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG192 §1.5.3",
    ),
    _rq18(
        "lochia_pattern",
        "How is your bleeding — how much blood are you losing, what colour, and are there any clots?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG192 §1.5.8",
    ),
    _rq18(
        "pain_management",
        "How are you managing pain — are the painkillers helping enough to move around and care for the baby?",
        [(1, 3), (4, 7), (8, 14)],
        "NG192 §1.6",
    ),
    _rq18(
        "lmwh_adherence",
        "Are you taking the blood-thinning injections each day — and how is the injection site?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG89 §1.3",
    ),
    _rq18(
        "breastfeeding_support",
        "How is feeding going — breast, bottle, or both, and is the baby settling?",
        [(1, 3), (4, 7), (8, 14)],
        "NG194 §1.4",
    ),

    # Mobility (ported from R17 with R18-specific +1 upper on early days)
    _rq18(
        "mobility_progress",
        "How much are you able to move around — walking indoors, using stairs, lifting the baby?",
        [(4, 7), (8, 14), (15, 28)],
        "NG192 §1.7",
    ),

    # Trauma-aware opener — gentler phrasing for day 1-3 emergency context.
    # Split into two entries: early call reassures and invites sharing
    # without prompting intrusion; later calls shift to more direct
    # screening for intrusive re-experiencing.
    _rq18(
        "emotional_processing_of_birth",
        "The birth was different from what you'd planned — how are you feeling about how things went?",
        [(1, 3)],
        "NG192 §1.6 / NG194 §1.7",
    ),
    _rq18(
        "emotional_processing_of_birth",
        "The birth wasn't what you'd planned — how are you processing it? Anything that's been hard to talk about, or that keeps coming back?",
        [(4, 7), (8, 14)],
        "NG192 §1.6 / NG194 §1.7",
    ),

    # Mood screening (same wording as R17 general-mood question)
    _rq18(
        "postnatal_depression_screen",
        "How are you feeling in yourself — beyond the tiredness, any low mood or worry that's been hard to shake?",
        [(4, 7), (8, 14), (15, 28)],
        "NG192 §1.6",
    ),

    # Coverage-check for clinician-administered EPDS (same pattern as R17)
    _rq18(
        "postnatal_depression_screen",
        "Has anyone from your care team done a mood questionnaire with you since you got home?",
        [(8, 14), (15, 28)],
        "NG192 §1.6 / CG192",
    ),

    # Trauma screen coverage — equivalent to EPDS coverage check but for PTSD
    _rq18(
        "ptsd_screening",
        "Has anyone from your care team asked about flashbacks, nightmares, or intrusive thoughts about the birth?",
        [(8, 14), (15, 28)],
        "NG194 §1.7 / NG116",
    ),
    # CLINICAL_REVIEW_NEEDED: the coverage-check pattern for PTSD assumes the
    # clinician team administers a validated tool (PCL-5, TSQ, or similar).
    # Reviewer to confirm which tool the trust uses and whether the voice-agent
    # should screen directly (same conservative position as EPDS in R17).
]


R18_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ postpartum_haemorrhage — 3 probes, all 999 (same as R17) ════════
    "postpartum_haemorrhage_volume": RedFlagProbe(
        flag_code="postpartum_haemorrhage_volume",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you been soaking through a maternity pad in less than an hour?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "postpartum_haemorrhage_clots": RedFlagProbe(
        flag_code="postpartum_haemorrhage_clots",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you passed any clots that were bigger than a 50p coin?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "postpartum_haemorrhage_haemodynamic": RedFlagProbe(
        flag_code="postpartum_haemorrhage_haemodynamic",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you felt faint, dizzy, or lightheaded — especially when you stand up?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ wound_dehiscence — 2 probes (same as R17) ══════════════════════
    "wound_dehiscence_gaping": RedFlagProbe(
        flag_code="wound_dehiscence_gaping",
        parent_flag_code="wound_dehiscence",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG192 §1.5.3",
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
        nice_basis="NG192 §1.5.3",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ pe_symptoms — 3 probes incl. DVT calf (same as R17) ═════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.3 / NG158",
        # Retroactive wording fix per the no-memory-comparison rule.
        # Same wording as R17 and W40 pe_symptoms_breathing.
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
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Any sharp chest pain — especially when you breathe in deeply?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pe_symptoms_calf_signs": RedFlagProbe(
        flag_code="pe_symptoms_calf_signs",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Any pain, swelling, redness, or warmth in one of your calves — "
            "especially tender when you press on it?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ pre_eclampsia_signs — 3 probes, all 999 (same as R17) ══════════
    "pre_eclampsia_headache": RedFlagProbe(
        flag_code="pre_eclampsia_headache",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Have you had a severe headache that doesn't go away with simple painkillers?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pre_eclampsia_visual": RedFlagProbe(
        flag_code="pre_eclampsia_visual",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Any changes to your vision — blurring, flashing lights, or spots?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "pre_eclampsia_epigastric": RedFlagProbe(
        flag_code="pre_eclampsia_epigastric",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Any pain in the upper right part of your tummy, just below the ribs?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ postnatal_depression_severe — 2 probes (same as R17) ════════════
    "postnatal_depression_passive_ideation": RedFlagProbe(
        flag_code="postnatal_depression_passive_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192 §1.9",
        patient_facing_question=(
            "Have you had any thoughts that you or your family would be better "
            "off without you?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "postnatal_depression_active_ideation": RedFlagProbe(
        flag_code="postnatal_depression_active_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192 §1.9",
        patient_facing_question=(
            "Have you had any thoughts about harming yourself, or about ending "
            "your own life?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ ptsd_symptoms — 3 probes (new for R18) ══════════════════════════
    # Single-observation split per the principle. Each covers a DSM-5 /
    # ICD-11 PTSD symptom cluster (re-experiencing, avoidance,
    # hyperarousal). All SAME_DAY — requires urgent mental-health review
    # but not 999 unless paired with active suicidal ideation (covered
    # by the postnatal_depression probes above).
    "ptsd_symptoms_reexperiencing": RedFlagProbe(
        flag_code="ptsd_symptoms_reexperiencing",
        parent_flag_code="ptsd_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG116 §1.2 / NG194 §1.7",
        patient_facing_question=(
            "Have you had intrusive thoughts, flashbacks, or nightmares about the birth?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "ptsd_symptoms_avoidance": RedFlagProbe(
        flag_code="ptsd_symptoms_avoidance",
        parent_flag_code="ptsd_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG116 §1.2 / NG194 §1.7",
        patient_facing_question=(
            "Are you finding yourself avoiding reminders of the birth — "
            "places, people, or conversations that bring the experience back?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "ptsd_symptoms_hyperarousal": RedFlagProbe(
        flag_code="ptsd_symptoms_hyperarousal",
        parent_flag_code="ptsd_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG116 §1.2 / NG194 §1.7",
        patient_facing_question=(
            "Are you feeling jumpy, irritable, or having trouble sleeping since the birth?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: R18 monolith red_flags list omits
    # infant_feeding_failure (present for R17). Clinically it applies
    # equally to emergency C-section. Reviewer to confirm whether to add
    # the R17 infant_feeding probes to R18 or keep the monolith list.
}


# ─── Module-level registries (consumed by pathways/__init__.py) ────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "R17": R17_PLAYBOOK,
    "R18": R18_PLAYBOOK,
}

TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "R17": R17_TRAJECTORIES,
    "R18": R18_TRAJECTORIES,
}

REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "R17": R17_REQUIRED_QUESTIONS,
    "R18": R18_REQUIRED_QUESTIONS,
}

RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "R17": R17_RED_FLAG_PROBES,
    "R18": R18_RED_FLAG_PROBES,
}

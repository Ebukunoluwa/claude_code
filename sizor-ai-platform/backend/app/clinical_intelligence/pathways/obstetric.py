"""Obstetric pathways — R17 (elective C-section), R18 (emergency C-section).

Phase 3 status: **R17 only** in this commit. R18 is deferred to the next
commit once the R17 template has been reviewed and approved.

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
        "How is the wound site looking — any redness, swelling, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14)],
        "NG192 §1.5.3",
    ),
    _rq(
        "lochia_pattern",
        "How is your bleeding — how much are you losing, what colour, and are there any clots?",
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

    # Day 8-14 emphasis: wound fully healing, EPDS if not already done
    _rq(
        "postnatal_depression_screen",
        "A formal mood questionnaire — the Edinburgh Postnatal Depression Scale — is often done around two weeks. Can we go through it together today?",
        [(8, 14)],
        "NG192 §1.6 / CG192",
    ),
    # CLINICAL_REVIEW_NEEDED: above question assumes voice-agent administers
    # EPDS; reviewer to confirm whether the formal EPDS should be flagged for
    # clinician/midwife administration only, with voice-agent just screening.

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

    # ══ pe_symptoms (pulmonary embolism) — 2 probes ═════════════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.3 / NG158",
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
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Any sharp chest pain — especially when you breathe in deeply?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: calf DVT probe is a close cousin clinically
    # (DVT is the precursor to PE). Reviewer to decide whether calf_signs
    # belongs under pe_symptoms parent or needs its own upstream flag.

    # ══ pre_eclampsia_signs — 3 probes, all SAME_DAY ════════════════════
    "pre_eclampsia_headache": RedFlagProbe(
        flag_code="pre_eclampsia_headache",
        parent_flag_code="pre_eclampsia_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG133 §1.5 / NG192 §1.5.6",
        patient_facing_question=(
            "Have you had a severe headache that doesn't go away with simple painkillers?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
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
        follow_up_escalation=EscalationTier.SAME_DAY,
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
        follow_up_escalation=EscalationTier.SAME_DAY,
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
# Deferred to next commit — see module docstring.
# ═══════════════════════════════════════════════════════════════════════


# ─── Module-level registries (consumed by pathways/__init__.py) ────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "R17": R17_PLAYBOOK,
}

TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "R17": R17_TRAJECTORIES,
}

REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "R17": R17_REQUIRED_QUESTIONS,
}

RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "R17": R17_RED_FLAG_PROBES,
}

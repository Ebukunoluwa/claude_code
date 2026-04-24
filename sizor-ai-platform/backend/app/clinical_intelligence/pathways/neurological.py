"""Neurological pathways — S01 (stroke).

Phase 3 neurological cluster (single pathway in scope). 90-day
monitoring window, 9 call days front-loaded (recurrence risk highest
in first 30 days per NG128).

All FAST and focal-neuro probes are OBSERVATIONAL — they ask whether
the patient or someone around them has NOTICED a deficit, never asking
the patient to perform a live physical test. Rationale: elderly post-
stroke patients with genuine weakness attempting a self-test are a
falls risk, and unsupervised self-tests have high false-negative
rates. Same clinical-safety rationale applies here as in K57's stroke
arm-weakness probe.

Swallowing probes are likewise observational — ask about coughing or
choking on recent food/drink, not "please try to swallow something
now".

Wording principles (same as cardiac):
  No bare clinical jargon. Inline gloss on first use for: antiplatelet,
  anticoagulant, DOAC. Plain equivalents for dysphagia ("coughing or
  choking on food or drink"), aphasia ("slurred or harder to get
  out"), hemiparesis ("looking weaker on one side"). Concrete anchors
  and 24-hour windows throughout.

Primary NICE sources: NG128 (stroke rehabilitation in adults),
CG162 (stroke rehab — depression screening), QS2 (stroke quality
standards), NG185 (secondary prevention overlap). Reviewer specialty:
Stroke physician / neurologist.
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


# ═══════════════════════════════════════════════════════════════════════
# S01 — Ischaemic Stroke (post-discharge)
# Patient-facing wording audit: 2026-04-24 (new content, audited at draft)
# ═══════════════════════════════════════════════════════════════════════

S01_PLAYBOOK = PathwayPlaybook(
    opcs_code="S01",
    label="Stroke / Ischaemic",
    category="medical",
    nice_ids=["NG128", "CG162", "QS2", "NG185"],
    monitoring_window_days=90,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60, 90],
    domains=[
        "neurological_deficit_monitoring",
        "antiplatelet_or_anticoagulant",
        "blood_pressure_control",
        "swallowing_and_nutrition",
        "mood_and_post_stroke_depression",
        "rehabilitation_attendance",
        "falls_risk",
    ],
    red_flag_codes=[
        "new_neurological_symptoms",
        "anticoagulant_non_adherence",
        "bp_severely_uncontrolled",
        "dysphagia_aspiration",
        "falls_with_injury",
        "stroke_recurrence_signs",
        "haemorrhage",
    ],
    validation_status=_DRAFT,
)


S01_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # neurological_deficit_monitoring — NG128
    _traj("S01", "neurological_deficit_monitoring",  1, 2, 3, "Neurological deficits present", "NG128"),
    _traj("S01", "neurological_deficit_monitoring",  3, 2, 3, "Monitor for improvement or deterioration", "NG128"),
    _traj("S01", "neurological_deficit_monitoring",  7, 2, 2, "Gradual recovery expected", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 14, 1, 2, "Improving", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 21, 1, 2, "Improving", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 28, 1, 2, "Ongoing recovery", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 42, 1, 2, "Ongoing recovery", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 60, 1, 1, "Plateau or continued improvement", "NG128"),
    _traj("S01", "neurological_deficit_monitoring", 90, 1, 1, "Recovery plateau expected", "NG128"),

    # antiplatelet_or_anticoagulant — NG128
    _traj("S01", "antiplatelet_or_anticoagulant",  1, 1, 1, "Antiplatelet/anticoagulant commenced", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant",  3, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant",  7, 1, 1, "Adherent — lifelong", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 14, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 21, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 28, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 42, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 60, 1, 1, "Adherent", "NG128"),
    _traj("S01", "antiplatelet_or_anticoagulant", 90, 1, 1, "Adherent — lifelong", "NG128"),

    # blood_pressure_control — NG128
    _traj("S01", "blood_pressure_control",  1, 1, 2, "BP monitoring commenced", "NG128"),
    _traj("S01", "blood_pressure_control",  3, 1, 2, "Target <130/80", "NG128"),
    _traj("S01", "blood_pressure_control",  7, 1, 1, "BP controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 14, 1, 1, "BP controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 21, 1, 1, "Controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 28, 1, 1, "Controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 42, 1, 1, "Controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 60, 1, 1, "Controlled", "NG128"),
    _traj("S01", "blood_pressure_control", 90, 1, 1, "Controlled — lifelong target", "NG128"),

    # swallowing_and_nutrition — NG128
    _traj("S01", "swallowing_and_nutrition",  1, 2, 3, "Swallow assessment done — dysphagia risk", "NG128"),
    _traj("S01", "swallowing_and_nutrition",  3, 2, 2, "Modified diet if dysphagia", "NG128"),
    _traj("S01", "swallowing_and_nutrition",  7, 1, 2, "Improving swallow", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 14, 1, 1, "Near-normal diet expected", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 21, 1, 1, "Normal diet if swallow safe", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 28, 0, 1, "Normal diet", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 42, 0, 1, "Normal", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 60, 0, 0, "Normal", "NG128"),
    _traj("S01", "swallowing_and_nutrition", 90, 0, 0, "Normal", "NG128"),

    # mood_and_post_stroke_depression — CG162
    _traj("S01", "mood_and_post_stroke_depression",  1, 1, 2, "Depression risk elevated post-stroke", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression",  3, 1, 2, "Monitor", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression",  7, 1, 2, "Depression common weeks 1-4", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 14, 1, 2, "Screen using PHQ-2", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 21, 1, 1, "Monitor mood", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 28, 1, 1, "Mood stabilising", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 42, 1, 1, "Ongoing monitoring", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 60, 1, 1, "Ongoing", "CG162"),
    _traj("S01", "mood_and_post_stroke_depression", 90, 0, 1, "Settled", "CG162"),

    # rehabilitation_attendance — NG128
    _traj("S01", "rehabilitation_attendance",  1, 1, 2, "Rehab commenced in hospital", "NG128"),
    _traj("S01", "rehabilitation_attendance",  3, 1, 2, "Early supported discharge team", "NG128"),
    _traj("S01", "rehabilitation_attendance",  7, 1, 1, "Community rehab", "NG128"),
    _traj("S01", "rehabilitation_attendance", 14, 1, 1, "Attending rehab", "NG128"),
    _traj("S01", "rehabilitation_attendance", 21, 1, 1, "Attending", "NG128"),
    _traj("S01", "rehabilitation_attendance", 28, 1, 1, "Ongoing rehab", "NG128"),
    _traj("S01", "rehabilitation_attendance", 42, 1, 1, "Ongoing", "NG128"),
    _traj("S01", "rehabilitation_attendance", 60, 1, 1, "Ongoing", "NG128"),
    _traj("S01", "rehabilitation_attendance", 90, 0, 1, "Programme completing", "NG128"),

    # falls_risk — QS2
    _traj("S01", "falls_risk",  1, 2, 3, "High falls risk with neurological deficit", "QS2"),
    _traj("S01", "falls_risk",  3, 2, 3, "High risk", "QS2"),
    _traj("S01", "falls_risk",  7, 2, 2, "High risk — physiotherapy assessing", "QS2"),
    _traj("S01", "falls_risk", 14, 1, 2, "Reducing with rehab", "QS2"),
    _traj("S01", "falls_risk", 21, 1, 2, "Ongoing risk", "QS2"),
    _traj("S01", "falls_risk", 28, 1, 1, "Managed risk", "QS2"),
    _traj("S01", "falls_risk", 42, 1, 1, "Managed", "QS2"),
    _traj("S01", "falls_risk", 60, 1, 1, "Ongoing management", "QS2"),
    _traj("S01", "falls_risk", 90, 0, 1, "Near-baseline", "QS2"),
]


S01_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # neurological_deficit_monitoring: asks about change in the known
    # deficit (not memory-comparing general function).
    _rq(
        "S01",
        "neurological_deficit_monitoring",
        "How has the side that was affected been this week — any improvement in movement, strength, or feeling, and anything new that wasn't there at discharge?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG128 §1.4",
    ),
    # First-use inline gloss for both "antiplatelet" and "anticoagulant"
    # since S01 patients may be on either depending on aetiology.
    _rq(
        "S01",
        "antiplatelet_or_anticoagulant",
        "Are you taking the blood-thinning tablets — either an antiplatelet like aspirin or clopidogrel, or a DOAC like apixaban or rivaroxaban — each day, and any missed doses?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG128 §1.5",
    ),
    _rq(
        "S01",
        "blood_pressure_control",
        "If you're checking your blood pressure at home, what have the readings been in the last few days?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG128 §1.6",
    ),
    # Swallowing RQ observational — asks about eating and drinking.
    _rq(
        "S01",
        "swallowing_and_nutrition",
        "How are you getting on with eating and drinking — any coughing or choking on food or drink, any changes in what you can safely swallow, and how is your weight?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG128 §1.7",
    ),
    _rq(
        "S01",
        "mood_and_post_stroke_depression",
        "How's your mood been since the stroke — any low feelings, worry, or withdrawing from things you'd normally do? Has anyone from the team done a mood questionnaire with you?",
        [(4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "CG162 §1.2",
    ),
    # Coverage-check pattern for rehabilitation.
    _rq(
        "S01",
        "rehabilitation_attendance",
        "Has the stroke rehab team been in touch with you — have you started outpatient therapy yet, or do you know when it begins?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG128 §1.8",
    ),
    _rq(
        "S01",
        "falls_risk",
        "Have you had any falls or near-falls since we last spoke — even slips you caught yourself on?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "QS2",
    ),
]


# ─── S01 Red Flag Probes ───────────────────────────────────────────────

S01_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ stroke_recurrence_signs — 3 FAST probes (all observational, 999) ═
    # All three mirror the K57 post-fix observational pattern. No
    # active-participation probes — all ask whether the patient or
    # someone around them has noticed the deficit.
    "stroke_recurrence_face_drooping": RedFlagProbe(
        flag_code="stroke_recurrence_face_drooping",
        parent_flag_code="stroke_recurrence_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 §1.3",
        patient_facing_question=(
            "Has anyone noticed one side of your face looking droopy or "
            "uneven today — like one corner of your mouth not moving the "
            "same as the other?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stroke_recurrence_arm_weakness": RedFlagProbe(
        flag_code="stroke_recurrence_arm_weakness",
        parent_flag_code="stroke_recurrence_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 §1.3",
        patient_facing_question=(
            "Has anyone around you noticed your arm looking weaker on one "
            "side today — dropping things, struggling to lift a kettle, "
            "or not moving the same as the other arm?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stroke_recurrence_speech_difficulty": RedFlagProbe(
        flag_code="stroke_recurrence_speech_difficulty",
        parent_flag_code="stroke_recurrence_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 §1.3",
        patient_facing_question=(
            "Has your speech been slurred or harder to get out today, or "
            "has anyone said they're having trouble understanding you?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ new_neurological_symptoms — 2 probes (post-stroke complications) ═
    # Distinct from stroke_recurrence — these are post-stroke events
    # (seizures, thunderclap headache suggesting intracranial bleed)
    # that don't fit the FAST template. Both 999.
    "new_neurological_seizure": RedFlagProbe(
        flag_code="new_neurological_seizure",
        parent_flag_code="new_neurological_symptoms",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 §1.4",
        patient_facing_question=(
            "Has anyone around you witnessed a seizure or fit — shaking "
            "movements, loss of awareness, or an odd episode you can't "
            "remember afterwards — in the last few days?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "new_neurological_severe_headache": RedFlagProbe(
        flag_code="new_neurological_severe_headache",
        parent_flag_code="new_neurological_symptoms",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 §1.4",
        patient_facing_question=(
            "Have you had any severe headache that came on very suddenly "
            "— like a thunderclap, or the worst headache you can remember "
            "— in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ anticoagulant_non_adherence — 1 probe ═════════════════════════
    # Missed-dose probe. Bleeding events live under their own parent
    # (haemorrhage) below — mirrors K57 structure.
    "anticoagulant_non_adherence": RedFlagProbe(
        flag_code="anticoagulant_non_adherence",
        parent_flag_code="anticoagulant_non_adherence",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG128 §1.5",
        patient_facing_question=(
            "Have you missed any doses of the blood-thinning tablets in "
            "the last few days, or run out of your supply?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ haemorrhage — 4 probes (same structure as K57 DOAC bleeding) ═══
    # Added as a new parent code — upstream pathway_map.red_flags for
    # S01 does not include haemorrhage, but anticoagulation-associated
    # bleeding is a recognised adverse event for this cohort.
    "haemorrhage_prolonged_nosebleed": RedFlagProbe(
        flag_code="haemorrhage_prolonged_nosebleed",
        parent_flag_code="haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG128 §1.5",
        patient_facing_question=(
            "Have you had any nosebleeds that didn't stop after 10 minutes "
            "of pinching the nose, in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "haemorrhage_blood_in_urine_or_stool": RedFlagProbe(
        flag_code="haemorrhage_blood_in_urine_or_stool",
        parent_flag_code="haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG128 §1.5",
        patient_facing_question=(
            "Any blood when you pee, or dark or bright blood in your poo, "
            "in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "haemorrhage_unusual_bruising": RedFlagProbe(
        flag_code="haemorrhage_unusual_bruising",
        parent_flag_code="haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG128 §1.5",
        patient_facing_question=(
            "Any large bruises that have appeared without a bump or knock, "
            "or bruises that are bigger than the palm of your hand?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "haemorrhage_major_bleed": RedFlagProbe(
        flag_code="haemorrhage_major_bleed",
        parent_flag_code="haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG128 §1.5",
        patient_facing_question=(
            "Have you vomited blood, coughed up blood, or had bleeding "
            "that you couldn't stop — from any part of your body — today?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ bp_severely_uncontrolled — 1 probe (home BP conditional) ══════
    "bp_severely_uncontrolled": RedFlagProbe(
        flag_code="bp_severely_uncontrolled",
        parent_flag_code="bp_severely_uncontrolled",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG128 §1.6",
        patient_facing_question=(
            "If you've been checking your blood pressure at home — has "
            "the top number been over 180 on any reading in the last 24 "
            "hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ dysphagia_aspiration — 3 observational probes ═════════════════
    # All observational — ask about recent eating/drinking, not "please
    # swallow something now". Aspiration pneumonia is the feared
    # complication, so a chest-symptoms probe is included.
    "dysphagia_coughing_choking": RedFlagProbe(
        flag_code="dysphagia_coughing_choking",
        parent_flag_code="dysphagia_aspiration",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG128 §1.7",
        patient_facing_question=(
            "Have you been coughing or choking on food or drink in the "
            "last 24 hours, or felt that food has gone down the wrong way?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "dysphagia_wet_voice": RedFlagProbe(
        flag_code="dysphagia_wet_voice",
        parent_flag_code="dysphagia_aspiration",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG128 §1.7",
        patient_facing_question=(
            "After eating or drinking, has your voice sounded wet, gurgly, "
            "or like you need to clear your throat to speak clearly?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "dysphagia_chest_infection_signs": RedFlagProbe(
        flag_code="dysphagia_chest_infection_signs",
        parent_flag_code="dysphagia_aspiration",
        category=RedFlagCategory.SEPSIS_SIGNS,
        nice_basis="NG128 §1.7 / NG51",
        patient_facing_question=(
            "Have you had a new chesty cough, fever, or feeling hot-and-"
            "cold in the last 24 hours — especially if you've been "
            "coughing when you eat or drink?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ falls_with_injury — 3 probes (adapted from W38 pattern) ═══════
    # Post-stroke cohort has high falls risk + anticoagulation risk.
    # Same three-probe split as W38: new pain (SAME_DAY), head strike
    # (999 — intracranial haemorrhage risk), and post-fall new weakness
    # (999 — fall may have triggered new stroke, or vice versa).
    "falls_with_injury_new_pain": RedFlagProbe(
        flag_code="falls_with_injury_new_pain",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS2 / NG128",
        patient_facing_question=(
            "If you've had a fall, has it left you with any new pain — in "
            "your arms, shoulders, back, hips, or legs?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "falls_with_injury_head_strike": RedFlagProbe(
        flag_code="falls_with_injury_head_strike",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS2 / NG128",
        patient_facing_question=(
            "If you've had a fall, did you hit your head, black out, or "
            "can't remember the fall itself?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "falls_with_injury_new_weakness": RedFlagProbe(
        flag_code="falls_with_injury_new_weakness",
        parent_flag_code="falls_with_injury",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="QS2 / NG128",
        patient_facing_question=(
            "If you've had a fall, has anyone noticed you seem weaker on "
            "one side, or having more trouble moving or speaking, since "
            "the fall?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # CLINICAL_REVIEW_NEEDED: haemorrhage is added as a parent code
    # not listed in upstream pathway_map.red_flags for S01. Reviewer
    # to confirm the parent should propagate to upstream map +
    # dashboards (anticoagulation-associated bleeding is a recognised
    # adverse event for S01, same rationale as K57).
    #
    # CLINICAL_REVIEW_NEEDED: stroke_recurrence and falls_with_injury_
    # new_weakness probes overlap clinically — a post-fall new deficit
    # could be either a new stroke or missed recurrence. Reviewer to
    # confirm Phase 4 compound-rule logic should not double-count
    # escalation when both parents fire for the same underlying event.
    #
    # CLINICAL_REVIEW_NEEDED: dysphagia_chest_infection_signs probe
    # set to EMERGENCY_999 because aspiration pneumonia in a post-
    # stroke cohort has high mortality. Reviewer to confirm the tier
    # (may moderate to SAME_DAY with compound rule if patient is
    # afebrile and talking normally at time of call).
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "S01": S01_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "S01": S01_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "S01": S01_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "S01": S01_RED_FLAG_PROBES,
}

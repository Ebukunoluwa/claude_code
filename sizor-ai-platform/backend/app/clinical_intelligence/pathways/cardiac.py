"""Cardiac pathways — K40, K40_CABG, K57, K60.

Phase 3 cardiac cluster. Cohort is mixed-age with high comorbidity
load; many patients are on baseline anticoagulants, diuretics, or
antiplatelets before the index admission.

Chest-pain escalation rule applied across K40 / K40_CABG / K60:
  - Chest pain at rest (sitting still, lying down) → EMERGENCY_999
    unconditionally.
  - Chest pain on minimal exertion (standing from a chair, walking
    across a room, climbing one flight of stairs) → SAME_DAY with
    a compound-rule escalation flag for the Phase 4 call-status
    layer (if co-firing with breathlessness or syncope probes,
    escalate to 999).
  - Deliberately not conflated at the probe layer. Concrete
    behavioural anchors replace memory-comparison phrasings
    ("worse than your usual pattern").

Wording principles (same as orthopaedic/surgical):
  Plain-English, no bare clinical jargon. First-use inline gloss
  for: antiplatelet ("blood-thinning tablets"), anticoagulant /
  DOAC ("blood-thinning tablets, like apixaban or rivaroxaban"),
  palpitations ("sudden fluttering or racing heartbeat"),
  orthopnoea ("needing to prop yourself up on pillows to breathe"),
  syncope ("blacking out" / "fainting"), arrhythmia / ejection
  fraction (never appear patient-facing).

Coverage-check pattern used for clinician-administered items:
  - Cardiac rehab attendance (team-tracked, not voice-agent-scored)
  - Renal bloods in K60 (GP practice arranges)

Primary NICE sources: NG185 (ACS), CG172 (MI secondary prevention),
QS99, NG238 (cardiac rehab), NG196 (AF), QS93, TA249 (DOAC in AF),
NG106 (chronic HF), CG187, QS9. Reviewer specialty: Cardiologist
(K40, K57), Cardiothoracic surgeon (K40_CABG), HF specialist nurse +
cardiologist (K60).
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
# K40 — Myocardial Infarction / ACS
# Patient-facing wording audit: 2026-04-24 (new content, audited at draft)
# ═══════════════════════════════════════════════════════════════════════
#
# Key decisions during port:
#   - chest_pain_at_rest splits into rest (999) and minimal-exertion
#     (SAME_DAY) probes per the cluster's chest-pain escalation rule.
#     Parent flag codes diverge from the upstream pathway_map which
#     lists only "chest_pain_at_rest" — see CLINICAL_REVIEW_NEEDED
#     below for reviewer to confirm the upstream map should be
#     extended.
#   - syncope splits into actual-blackout (999) and near-miss SAME_DAY.
#     Patient-facing wording uses "blacked out" / "came close to
#     fainting" — "syncope" never appears in patient text.
#   - sustained_palpitations splits into sustained-only (SAME_DAY) and
#     palpitations-with-red-flag-symptoms (999). First-use gloss of
#     "palpitations" on the RQ.

K40_PLAYBOOK = PathwayPlaybook(
    opcs_code="K40",
    label="Myocardial Infarction / ACS",
    category="medical",
    nice_ids=["NG185", "QS99", "CG172"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "chest_pain_monitoring",
        "antiplatelet_adherence",
        "cardiac_rehab_attendance",
        "mood_and_depression",
        "activity_progression",
        "risk_factor_modification",
    ],
    red_flag_codes=[
        "chest_pain_at_rest",
        "chest_pain_on_minimal_exertion",
        "syncope",
        "sustained_palpitations",
        "breathlessness_at_rest",
        "pe_symptoms",
    ],
    validation_status=_DRAFT,
)


K40_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # chest_pain_monitoring — NG185
    _traj("K40", "chest_pain_monitoring",  1, 1, 2, "Mild chest discomfort may persist", "NG185"),
    _traj("K40", "chest_pain_monitoring",  3, 1, 1, "Chest pain should be resolving", "NG185"),
    _traj("K40", "chest_pain_monitoring",  7, 1, 1, "No cardiac chest pain expected", "NG185"),
    _traj("K40", "chest_pain_monitoring", 14, 0, 1, "Clear of chest pain", "NG185"),
    _traj("K40", "chest_pain_monitoring", 21, 0, 1, "Clear", "NG185"),
    _traj("K40", "chest_pain_monitoring", 28, 0, 0, "Clear", "NG185"),
    _traj("K40", "chest_pain_monitoring", 42, 0, 0, "Clear", "NG185"),
    _traj("K40", "chest_pain_monitoring", 60, 0, 0, "Clear", "NG185"),

    # antiplatelet_adherence — CG172 (dual therapy x 12 months, then aspirin lifelong)
    _traj("K40", "antiplatelet_adherence",  1, 1, 1, "Dual antiplatelet therapy commenced", "CG172"),
    _traj("K40", "antiplatelet_adherence",  3, 1, 1, "Adherent", "CG172"),
    _traj("K40", "antiplatelet_adherence",  7, 1, 1, "Adherent", "CG172"),
    _traj("K40", "antiplatelet_adherence", 14, 1, 1, "Adherent — 12-month dual therapy", "CG172"),
    _traj("K40", "antiplatelet_adherence", 21, 1, 1, "Adherent", "CG172"),
    _traj("K40", "antiplatelet_adherence", 28, 1, 1, "Adherent", "CG172"),
    _traj("K40", "antiplatelet_adherence", 42, 1, 1, "Adherent", "CG172"),
    _traj("K40", "antiplatelet_adherence", 60, 1, 1, "Adherent — lifelong aspirin", "CG172"),

    # cardiac_rehab_attendance — NG238
    _traj("K40", "cardiac_rehab_attendance",  1, 1, 2, "Referral made", "NG238"),
    _traj("K40", "cardiac_rehab_attendance",  3, 1, 2, "Awaiting start", "NG238"),
    _traj("K40", "cardiac_rehab_attendance",  7, 1, 1, "Programme started or imminent", "NG238"),
    _traj("K40", "cardiac_rehab_attendance", 14, 1, 1, "Attending", "NG238"),
    _traj("K40", "cardiac_rehab_attendance", 21, 1, 1, "Attending", "NG238"),
    _traj("K40", "cardiac_rehab_attendance", 28, 1, 1, "Attending", "NG238"),
    _traj("K40", "cardiac_rehab_attendance", 42, 1, 1, "Ongoing", "NG238"),
    _traj("K40", "cardiac_rehab_attendance", 60, 0, 1, "Programme completing", "NG238"),

    # mood_and_depression — CG172 §1.4 (post-MI depression screening)
    _traj("K40", "mood_and_depression",  1, 1, 2, "Post-MI depression risk elevated", "CG172"),
    _traj("K40", "mood_and_depression",  3, 1, 2, "Monitor — depression peaks weeks 2-4", "CG172"),
    _traj("K40", "mood_and_depression",  7, 1, 2, "Screen for depression", "CG172"),
    _traj("K40", "mood_and_depression", 14, 1, 1, "Mood improving expected", "CG172"),
    _traj("K40", "mood_and_depression", 21, 1, 1, "Mood stabilising", "CG172"),
    _traj("K40", "mood_and_depression", 28, 1, 1, "Stable mood", "CG172"),
    _traj("K40", "mood_and_depression", 42, 1, 1, "Improving mood", "CG172"),
    _traj("K40", "mood_and_depression", 60, 0, 1, "Near-baseline mood", "CG172"),

    # activity_progression — NG185
    _traj("K40", "activity_progression",  1, 2, 3, "Rest — light activity only", "NG185"),
    _traj("K40", "activity_progression",  3, 2, 2, "Light activity increasing", "NG185"),
    _traj("K40", "activity_progression",  7, 1, 2, "Walking short distances", "NG185"),
    _traj("K40", "activity_progression", 14, 1, 1, "Increasing activity", "NG185"),
    _traj("K40", "activity_progression", 21, 1, 1, "Moderate activity tolerated", "NG185"),
    _traj("K40", "activity_progression", 28, 1, 1, "Good activity levels", "NG185"),
    _traj("K40", "activity_progression", 42, 0, 1, "Near-normal activity", "NG185"),
    _traj("K40", "activity_progression", 60, 0, 0, "Normal activity for patient", "NG185"),

    # risk_factor_modification — NG185
    _traj("K40", "risk_factor_modification",  1, 1, 2, "Education given — smoking/diet/BP/cholesterol", "NG185"),
    _traj("K40", "risk_factor_modification",  3, 1, 2, "Behaviour change support", "NG185"),
    _traj("K40", "risk_factor_modification",  7, 1, 1, "Lifestyle changes in progress", "NG185"),
    _traj("K40", "risk_factor_modification", 14, 1, 1, "Changes established", "NG185"),
    _traj("K40", "risk_factor_modification", 21, 1, 1, "Ongoing", "NG185"),
    _traj("K40", "risk_factor_modification", 28, 1, 1, "Ongoing", "NG185"),
    _traj("K40", "risk_factor_modification", 42, 1, 1, "Ongoing", "NG185"),
    _traj("K40", "risk_factor_modification", 60, 1, 1, "Sustained changes", "NG185"),
]


K40_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    _rq(
        "K40",
        "chest_pain_monitoring",
        "Any chest pain or discomfort in the last 24 hours — when did it come on, how long did it last, and what stopped it?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG185 §1.3",
    ),
    # First-use gloss of "antiplatelet" as plain-language tablet description.
    _rq(
        "K40",
        "antiplatelet_adherence",
        "Are you taking your heart tablets — the aspirin and the other blood-thinning one — each day, and any side effects like stomach upset or bruising?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "CG172 §1.7",
    ),
    # Coverage-check for cardiac rehab: voice agent is not administering,
    # the cardiac rehab team tracks attendance. Asks whether contact has
    # happened and whether the patient has started.
    _rq(
        "K40",
        "cardiac_rehab_attendance",
        "Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG238 §1.1",
    ),
    _rq(
        "K40",
        "mood_and_depression",
        "How's your mood been since the heart attack — any low feelings, worry, or trouble getting motivated to do the things you normally would?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "CG172 §1.4",
    ),
    _rq(
        "K40",
        "activity_progression",
        "How are you getting on with activity — walking, stairs, and any heavier tasks you've been back to?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG185 §1.5",
    ),
    _rq(
        "K40",
        "risk_factor_modification",
        "How are you getting on with the lifestyle changes the team talked about — smoking, diet, and exercise?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG185 §1.6",
    ),
]


# ─── K40 Red Flag Probes ───────────────────────────────────────────────

K40_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ chest_pain — 2 probes with separate parent codes ═══════════════
    # Rest pain is 999, minimal-exertion pain is SAME_DAY. Not conflated.
    # Concrete behavioural anchors replace memory-comparison.
    "chest_pain_at_rest": RedFlagProbe(
        flag_code="chest_pain_at_rest",
        parent_flag_code="chest_pain_at_rest",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG185 §1.3 / CG172",
        patient_facing_question=(
            "Have you had chest pain that came on at rest — while sitting "
            "still, lying down, or not doing anything?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "chest_pain_on_minimal_exertion": RedFlagProbe(
        flag_code="chest_pain_on_minimal_exertion",
        parent_flag_code="chest_pain_on_minimal_exertion",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG185 §1.3 / CG172",
        patient_facing_question=(
            "Have you had chest pain come on with a small effort today — "
            "like standing up from a chair, walking across a room, or "
            "climbing one flight of stairs?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: upstream pathway_map.red_flags for K40 lists
    # only "chest_pain_at_rest". Added "chest_pain_on_minimal_exertion"
    # as a separate parent for the SAME_DAY probe. Reviewer to confirm
    # whether this new parent code should propagate to the upstream map
    # + dashboards, or whether the two probes should share a single
    # parent "chest_pain" with the tier delta resolved at Phase 4.
    #
    # CLINICAL_REVIEW_NEEDED: compound rule for Phase 4 call-status
    # layer — chest_pain_on_minimal_exertion + any breathlessness or
    # syncope probe firing together suggests crescendo angina / re-
    # infarction and should escalate to EMERGENCY_999.

    # ══ syncope — 2 probes (blackout vs near-miss) ═════════════════════
    # Patient-facing wording avoids the word "syncope" — uses "blacked
    # out" / "very nearly fainted" as plain equivalents.
    "syncope_blackout": RedFlagProbe(
        flag_code="syncope_blackout",
        parent_flag_code="syncope",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Have you actually blacked out or fainted — lost consciousness "
            "even for a few seconds — in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "syncope_near_miss": RedFlagProbe(
        flag_code="syncope_near_miss",
        parent_flag_code="syncope",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Have you felt like you were about to pass out — needing to "
            "sit or lie down quickly — but didn't actually faint?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ sustained_palpitations — 2 probes ═════════════════════════════
    # First-use patient-facing gloss of "palpitations" as plain
    # description, then subsequent uses can be shorter.
    "palpitations_sustained": RedFlagProbe(
        flag_code="palpitations_sustained",
        parent_flag_code="sustained_palpitations",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Have you had any sudden fluttering or racing heartbeat — "
            "palpitations — that lasted more than about half an hour, or "
            "that kept coming back today?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "palpitations_with_red_flag_symptoms": RedFlagProbe(
        flag_code="palpitations_with_red_flag_symptoms",
        parent_flag_code="sustained_palpitations",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "When the fluttering or racing happened, did you also get "
            "chest pain, breathlessness, or feel like you might pass out?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ breathlessness_at_rest — 1 probe (unambiguous) ═════════════════
    "breathlessness_at_rest": RedFlagProbe(
        flag_code="breathlessness_at_rest",
        parent_flag_code="breathlessness_at_rest",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Have you been breathless at rest — needing to work hard to "
            "breathe even while sitting still?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ pe_symptoms — 2 probes (same as orthopaedic pattern) ═══════════
    # Sharp pleuritic chest pain (PE) is clinically distinct from
    # central crushing chest pain (cardiac ischaemia); probe wording
    # uses "sharp" + "when you breathe in deeply" to separate the
    # phenotype from chest_pain_at_rest.
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.3 / NG158",
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
}


# ═══════════════════════════════════════════════════════════════════════
# K40_CABG — Coronary Artery Bypass Graft
# Patient-facing wording audit: 2026-04-24 (new content, audited at draft)
# ═══════════════════════════════════════════════════════════════════════
#
# Key divergences from K40:
#   - 7 domains (sternal + leg wounds, chest_pain_recurrence, anti-
#     platelet_adherence, cardiac_rehab_attendance, mood_and_depression,
#     mobility_and_fatigue). 90-day monitoring window.
#   - Sternal precautions RQ is a TEMPLATE DEVIATION compound question
#     (same pattern as W37 hip precautions — sternal precautions are
#     taught pre-op as a bundled behavioural rule set, asked as a
#     bundle post-op).
#   - sternal_wound_breakdown splits into clicking (SAME_DAY —
#     movement instability without visible gap), discharge (SAME_DAY),
#     and separation (999 — visible gap indicates emergency).
#   - cardiac_arrest_signs is by definition observed by others, not
#     self-reported. Uses coverage-check framing — "has anyone noticed
#     you collapse or be unresponsive" — at EMERGENCY_999.

K40_CABG_PLAYBOOK = PathwayPlaybook(
    opcs_code="K40_CABG",
    label="Coronary Artery Bypass Graft",
    category="surgical",
    nice_ids=["NG185", "CG172", "QS99", "NG238"],
    monitoring_window_days=90,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60, 90],
    domains=[
        "sternal_wound_healing",
        "leg_wound_healing",
        "chest_pain_recurrence",
        "antiplatelet_adherence",
        "cardiac_rehab_attendance",
        "mood_and_depression",
        "mobility_and_fatigue",
    ],
    red_flag_codes=[
        "chest_pain_at_rest",
        "chest_pain_on_minimal_exertion",
        "sternal_wound_breakdown",
        "pe_symptoms",
        "cardiac_arrest_signs",
        "sustained_palpitations",
    ],
    validation_status=_DRAFT,
)


K40_CABG_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # sternal_wound_healing — NG185
    _traj("K40_CABG", "sternal_wound_healing",  1, 2, 3, "Wound intact, pain expected", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing",  3, 2, 3, "Healing — monitor for clicking or discharge", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing",  7, 1, 2, "Healing, sutures/clips in", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 14, 1, 2, "Healing well", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 21, 1, 1, "Well healed", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 28, 0, 1, "Healed", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 42, 0, 1, "Healed", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 60, 0, 0, "Fully healed", "NG185"),
    _traj("K40_CABG", "sternal_wound_healing", 90, 0, 0, "Fully healed", "NG185"),

    # leg_wound_healing — NG185
    _traj("K40_CABG", "leg_wound_healing",  1, 2, 3, "Donor site bruising/swelling expected", "NG185"),
    _traj("K40_CABG", "leg_wound_healing",  3, 2, 3, "Settling", "NG185"),
    _traj("K40_CABG", "leg_wound_healing",  7, 1, 2, "Healing", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 14, 1, 1, "Well healed", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 21, 0, 1, "Healed", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 28, 0, 1, "Healed", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 42, 0, 0, "Healed", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 60, 0, 0, "Healed", "NG185"),
    _traj("K40_CABG", "leg_wound_healing", 90, 0, 0, "Healed", "NG185"),

    # chest_pain_recurrence — CG172
    _traj("K40_CABG", "chest_pain_recurrence",  1, 2, 3, "Musculoskeletal chest pain expected", "NG185"),
    _traj("K40_CABG", "chest_pain_recurrence",  3, 2, 2, "Reducing sternal pain", "NG185"),
    _traj("K40_CABG", "chest_pain_recurrence",  7, 1, 2, "Mild musculoskeletal pain only", "NG185"),
    _traj("K40_CABG", "chest_pain_recurrence", 14, 1, 2, "Minimal pain", "NG185"),
    _traj("K40_CABG", "chest_pain_recurrence", 21, 1, 1, "Resolving", "CG172"),
    _traj("K40_CABG", "chest_pain_recurrence", 28, 0, 1, "Resolved", "CG172"),
    _traj("K40_CABG", "chest_pain_recurrence", 42, 0, 1, "Resolved", "CG172"),
    _traj("K40_CABG", "chest_pain_recurrence", 60, 0, 0, "Resolved", "CG172"),
    _traj("K40_CABG", "chest_pain_recurrence", 90, 0, 0, "Resolved", "CG172"),

    # antiplatelet_adherence — CG172
    _traj("K40_CABG", "antiplatelet_adherence",  1, 1, 1, "Aspirin commenced", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence",  3, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence",  7, 1, 1, "Adherent — lifelong", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 14, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 21, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 28, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 42, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 60, 1, 1, "Adherent", "CG172"),
    _traj("K40_CABG", "antiplatelet_adherence", 90, 1, 1, "Adherent — lifelong", "CG172"),

    # cardiac_rehab_attendance — NG238
    _traj("K40_CABG", "cardiac_rehab_attendance",  1, 1, 2, "Referral made", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance",  3, 1, 2, "Awaiting start", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance",  7, 1, 1, "Programme started or imminent", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 14, 1, 1, "Attending", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 21, 1, 1, "Attending", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 28, 1, 1, "Attending", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 42, 1, 1, "Ongoing", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 60, 1, 1, "Ongoing", "NG238"),
    _traj("K40_CABG", "cardiac_rehab_attendance", 90, 0, 1, "Programme completing", "NG238"),

    # mood_and_depression — CG172 (depression peak weeks 1-4 post-CABG)
    _traj("K40_CABG", "mood_and_depression",  1, 1, 2, "Low mood common post-CABG", "CG172"),
    _traj("K40_CABG", "mood_and_depression",  3, 1, 2, "Monitor for depression", "CG172"),
    _traj("K40_CABG", "mood_and_depression",  7, 1, 2, "Depression risk peak week 1-4", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 14, 1, 2, "Screen for depression", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 21, 1, 1, "Improving mood expected", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 28, 1, 1, "Mood stabilising", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 42, 1, 1, "Mood improving", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 60, 0, 1, "Near-baseline mood", "CG172"),
    _traj("K40_CABG", "mood_and_depression", 90, 0, 1, "Near-baseline mood", "CG172"),

    # mobility_and_fatigue — NG185
    _traj("K40_CABG", "mobility_and_fatigue",  1, 2, 3, "Marked fatigue expected", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue",  3, 2, 3, "Fatigue high", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue",  7, 2, 2, "Gradually improving", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 14, 1, 2, "Improving", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 21, 1, 2, "Walking short distances", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 28, 1, 1, "Increasing activity", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 42, 1, 1, "Good activity levels", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 60, 0, 1, "Near-normal activity", "NG185"),
    _traj("K40_CABG", "mobility_and_fatigue", 90, 0, 1, "Near-normal activity", "NG185"),
]


K40_CABG_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    _rq(
        "K40_CABG",
        "sternal_wound_healing",
        "How is the scar on your chest looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG185 / QS48",
    ),
    _rq(
        "K40_CABG",
        "leg_wound_healing",
        "How is the scar on your leg looking — the place where they took the vein — any redness, swelling, or fluid from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG185 / QS48",
    ),
    # Chest pain recurrence RQ distinguishes musculoskeletal/sternal
    # clicking from cardiac-pattern pain. The latter triggers the
    # red-flag probes.
    _rq(
        "K40_CABG",
        "chest_pain_recurrence",
        "Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG185 §1.3",
    ),
    # TEMPLATE DEVIATION — compound phrasing by design. Sternal
    # precautions are taught pre-op as a bundled behavioural rule set
    # (no lifting over 5lb, no pushing/pulling heavy doors, not
    # reaching both arms out at once, no driving for ~6 weeks) and
    # reinforced post-op as a bundle. Splitting into four separate
    # RQs (one per precaution) would fragment a single clinical
    # concept the patient already holds as one thing. Same reasoning
    # and conscious exception status as W37 hip precautions.
    _rq(
        "K40_CABG",
        "sternal_wound_healing",
        "Are you keeping to the sternal precautions — not lifting anything over about 5 pounds, not pushing or pulling heavy doors, not reaching both arms out at once, and not driving yet?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG185 §1.5",
    ),
    _rq(
        "K40_CABG",
        "antiplatelet_adherence",
        "Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "CG172 §1.7",
    ),
    _rq(
        "K40_CABG",
        "cardiac_rehab_attendance",
        "Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG238 §1.1",
    ),
    _rq(
        "K40_CABG",
        "mood_and_depression",
        "How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "CG172 §1.4",
    ),
    _rq(
        "K40_CABG",
        "mobility_and_fatigue",
        "How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG185 §1.5",
    ),
]


# ─── K40_CABG Red Flag Probes ──────────────────────────────────────────

K40_CABG_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ chest_pain — 2 probes (same split as K40) ══════════════════════
    # Post-CABG chest pain differentiation: musculoskeletal sternal
    # pain is expected and not red-flagged. Red-flag pattern is central,
    # crushing, radiating, or at-rest. Wording focuses on the pattern
    # signals rather than severity.
    "chest_pain_at_rest": RedFlagProbe(
        flag_code="chest_pain_at_rest",
        parent_flag_code="chest_pain_at_rest",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG185 §1.3 / CG172",
        patient_facing_question=(
            "Have you had chest pain that came on at rest — while sitting "
            "still, lying down, or not doing anything — and felt tight, "
            "crushing, or central rather than a sharp or sternal ache?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "chest_pain_on_minimal_exertion": RedFlagProbe(
        flag_code="chest_pain_on_minimal_exertion",
        parent_flag_code="chest_pain_on_minimal_exertion",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG185 §1.3 / CG172",
        patient_facing_question=(
            "Have you had chest pain come on with a small effort today — "
            "like standing up from a chair, walking across a room, or "
            "climbing one flight of stairs — and felt tight or crushing "
            "rather than a sternal ache?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ sternal_wound_breakdown — 3 probes ═════════════════════════════
    # Sternal non-union / dehiscence: three distinct clinical findings
    # with graded escalation:
    #   - clicking / grinding (sternal instability, no visible break)
    #     → SAME_DAY
    #   - discharge → SAME_DAY
    #   - visible separation (breast bone coming apart) → EMERGENCY_999
    "sternal_wound_clicking": RedFlagProbe(
        flag_code="sternal_wound_clicking",
        parent_flag_code="sternal_wound_breakdown",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 §1.5",
        patient_facing_question=(
            "Can you feel any clicking, grinding, or moving feeling in "
            "your breast bone when you cough, take a deep breath, or "
            "turn in bed?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "sternal_wound_discharge": RedFlagProbe(
        flag_code="sternal_wound_discharge",
        parent_flag_code="sternal_wound_breakdown",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 §1.5 / QS48",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the chest scar?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "sternal_wound_separation": RedFlagProbe(
        flag_code="sternal_wound_separation",
        parent_flag_code="sternal_wound_breakdown",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 §1.5",
        patient_facing_question=(
            "Has the scar on your chest opened up — with a visible gap "
            "between the edges, or can you see the breast bone underneath?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ pe_symptoms — 2 probes ═════════════════════════════════════════
    "pe_symptoms_breathing": RedFlagProbe(
        flag_code="pe_symptoms_breathing",
        parent_flag_code="pe_symptoms",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG89 §1.3 / NG158",
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
            "Any sharp chest pain on one side — especially when you breathe in deeply?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ cardiac_arrest_signs — 1 probe (coverage-check, carer-observed) ═
    # Cardiac arrest is by definition observed by others, not self-
    # reported. Probe uses carer-observed framing. If the answer is
    # yes, the event already happened — patient is answering after
    # recovery or the family is answering on behalf.
    "cardiac_arrest_witnessed_collapse": RedFlagProbe(
        flag_code="cardiac_arrest_witnessed_collapse",
        parent_flag_code="cardiac_arrest_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Has anyone around you — family, carer, or neighbour — found "
            "you collapsed and unresponsive in the last few days, or had "
            "to call for emergency help for you?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ sustained_palpitations — 2 probes (same pattern as K40) ════════
    "palpitations_sustained": RedFlagProbe(
        flag_code="palpitations_sustained",
        parent_flag_code="sustained_palpitations",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "Have you had any sudden fluttering or racing heartbeat — "
            "palpitations — that lasted more than about half an hour, or "
            "that kept coming back today?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "palpitations_with_red_flag_symptoms": RedFlagProbe(
        flag_code="palpitations_with_red_flag_symptoms",
        parent_flag_code="sustained_palpitations",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG185 / CG172",
        patient_facing_question=(
            "When the fluttering or racing happened, did you also get "
            "chest pain, breathlessness, or feel like you might pass out?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # CLINICAL_REVIEW_NEEDED: K40_CABG inherits K40's new parent code
    # "chest_pain_on_minimal_exertion". Same upstream-map propagation
    # decision applies — reviewer to confirm once for the whole cardiac
    # cluster rather than per-pathway.
    #
    # CLINICAL_REVIEW_NEEDED: cardiac_arrest_witnessed_collapse uses
    # coverage-check framing because the patient cannot self-report
    # loss of consciousness with no return of pulse. Reviewer to
    # confirm: should this also gate behind an explicit "is anyone
    # with you?" intake flag at the voice-agent layer rather than
    # rely on whoever answers the call?
}


# ═══════════════════════════════════════════════════════════════════════
# K57 — Atrial Fibrillation
# Patient-facing wording audit: 2026-04-24 (new content, audited at draft)
# ═══════════════════════════════════════════════════════════════════════
#
# Key divergences:
#   - AF-specific anticoagulation is typically a DOAC (apixaban,
#     rivaroxaban, edoxaban, dabigatran). First-use RQ gloss of "DOAC"
#     uses plain language ("blood-thinning tablet, like apixaban or
#     rivaroxaban"). Bare "anticoagulant" / "DOAC" avoided in probes.
#   - Stroke signs (FAST: Face, Arm, Speech, Time) split into 3
#     separate probes — each is a single observation, all 999.
#   - Haemorrhage from anticoagulation splits into four probes by
#     severity and site:
#     - nosebleed lasting 10+ minutes → SAME_DAY
#     - blood in urine or stool → SAME_DAY
#     - unusual bruising → SAME_DAY
#     - major bleeding event (vomiting blood / uncontrolled bleed /
#       visible large blood loss) → EMERGENCY_999

K57_PLAYBOOK = PathwayPlaybook(
    opcs_code="K57",
    label="Atrial Fibrillation",
    category="medical",
    nice_ids=["NG196", "QS93", "TA249"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "rate_control_monitoring",
        "anticoagulation_adherence",
        "symptom_monitoring",
        "bleeding_signs",
        "mood_and_anxiety",
    ],
    red_flag_codes=[
        "palpitations_severe",
        "stroke_signs",
        "haemorrhage",
        "syncope",
        "breathlessness_acute",
    ],
    validation_status=_DRAFT,
)


K57_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # rate_control_monitoring — NG196 §1.6 (target <110bpm at rest)
    _traj("K57", "rate_control_monitoring",  1, 1, 2, "Rate control assessment — target <110bpm at rest", "NG196"),
    _traj("K57", "rate_control_monitoring",  3, 1, 1, "Rate controlled", "NG196"),
    _traj("K57", "rate_control_monitoring",  7, 1, 1, "Rate controlled", "NG196"),
    _traj("K57", "rate_control_monitoring", 14, 1, 1, "Stable rate control", "NG196"),
    _traj("K57", "rate_control_monitoring", 21, 1, 1, "Stable", "NG196"),
    _traj("K57", "rate_control_monitoring", 28, 1, 1, "Stable", "NG196"),
    _traj("K57", "rate_control_monitoring", 42, 1, 1, "Stable", "NG196"),
    _traj("K57", "rate_control_monitoring", 60, 1, 1, "Stable", "NG196"),

    # anticoagulation_adherence — NG196 §1.5 (lifelong if CHA2DS2-VASc ≥2)
    _traj("K57", "anticoagulation_adherence",  1, 1, 1, "Anticoagulant commenced", "NG196"),
    _traj("K57", "anticoagulation_adherence",  3, 1, 1, "Adherent", "NG196"),
    _traj("K57", "anticoagulation_adherence",  7, 1, 1, "Adherent", "NG196"),
    _traj("K57", "anticoagulation_adherence", 14, 1, 1, "Adherent", "NG196"),
    _traj("K57", "anticoagulation_adherence", 21, 1, 1, "Adherent — lifelong if CHA2DS2-VASc ≥2", "NG196"),
    _traj("K57", "anticoagulation_adherence", 28, 1, 1, "Adherent", "NG196"),
    _traj("K57", "anticoagulation_adherence", 42, 1, 1, "Adherent", "NG196"),
    _traj("K57", "anticoagulation_adherence", 60, 1, 1, "Adherent — lifelong", "NG196"),

    # symptom_monitoring — NG196 §1.6
    _traj("K57", "symptom_monitoring",  1, 1, 2, "Palpitations/breathlessness may persist", "NG196"),
    _traj("K57", "symptom_monitoring",  3, 1, 1, "Symptoms settling with rate control", "NG196"),
    _traj("K57", "symptom_monitoring",  7, 1, 1, "Symptoms settled", "NG196"),
    _traj("K57", "symptom_monitoring", 14, 1, 1, "Stable", "NG196"),
    _traj("K57", "symptom_monitoring", 21, 1, 1, "Stable", "NG196"),
    _traj("K57", "symptom_monitoring", 28, 1, 1, "Stable", "NG196"),
    _traj("K57", "symptom_monitoring", 42, 1, 1, "Stable", "NG196"),
    _traj("K57", "symptom_monitoring", 60, 1, 1, "Stable", "NG196"),

    # bleeding_signs — NG196 §1.5 (DOAC-related bleeding surveillance)
    _traj("K57", "bleeding_signs",  1, 1, 1, "Monitor for anticoagulant-related bleeding", "NG196"),
    _traj("K57", "bleeding_signs",  3, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs",  7, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs", 14, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs", 21, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs", 28, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs", 42, 1, 1, "No bleeding expected", "NG196"),
    _traj("K57", "bleeding_signs", 60, 1, 1, "Monitoring ongoing", "NG196"),

    # mood_and_anxiety — NG196 §1.7
    _traj("K57", "mood_and_anxiety",  1, 1, 2, "Anxiety with AF diagnosis common", "NG196"),
    _traj("K57", "mood_and_anxiety",  3, 1, 2, "Monitor for anxiety", "NG196"),
    _traj("K57", "mood_and_anxiety",  7, 1, 1, "Mood settling", "NG196"),
    _traj("K57", "mood_and_anxiety", 14, 1, 1, "Stable mood", "NG196"),
    _traj("K57", "mood_and_anxiety", 21, 1, 1, "Stable", "NG196"),
    _traj("K57", "mood_and_anxiety", 28, 1, 1, "Stable", "NG196"),
    _traj("K57", "mood_and_anxiety", 42, 1, 1, "Stable", "NG196"),
    _traj("K57", "mood_and_anxiety", 60, 0, 1, "Near-baseline", "NG196"),
]


K57_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # First-use gloss for "palpitations" on the symptom_monitoring RQ
    # (asked earlier in the call than rate_control), plus plain
    # "heartbeat" in rate_control_monitoring for naturalness.
    _rq(
        "K57",
        "rate_control_monitoring",
        "How's your heartbeat feeling day-to-day — slower and more regular, or still fluttering or racing at times?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG196 §1.6",
    ),
    # First-use inline gloss for "DOAC" as plain tablet description.
    _rq(
        "K57",
        "anticoagulation_adherence",
        "Are you taking the blood-thinning tablets — a DOAC, like apixaban or rivaroxaban — each day, and have you missed any doses?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG196 §1.5",
    ),
    # First-use gloss for "palpitations" on symptom_monitoring.
    _rq(
        "K57",
        "symptom_monitoring",
        "Any new dizziness, breathlessness, chest discomfort, or sudden fluttering or racing heartbeat — palpitations — in the last 24 hours?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG196 §1.6",
    ),
    _rq(
        "K57",
        "bleeding_signs",
        "Any unusual bruising, nosebleeds, blood when you pee or in your poo, or gums bleeding when you brush your teeth?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG196 §1.5",
    ),
    _rq(
        "K57",
        "mood_and_anxiety",
        "How's your mood and any worry about the diagnosis — keeping up with daily things, sleeping OK?",
        [(4, 7), (8, 14), (15, 28), (29, 60)],
        "NG196 §1.7",
    ),
]


# ─── K57 Red Flag Probes ───────────────────────────────────────────────

K57_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ palpitations_severe — 2 probes (same pattern as K40) ═══════════
    "palpitations_sustained": RedFlagProbe(
        flag_code="palpitations_sustained",
        parent_flag_code="palpitations_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG196 §1.6",
        patient_facing_question=(
            "Have you had any sudden fluttering or racing heartbeat — "
            "palpitations — that lasted more than about half an hour, or "
            "that kept coming back today?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "palpitations_with_red_flag_symptoms": RedFlagProbe(
        flag_code="palpitations_with_red_flag_symptoms",
        parent_flag_code="palpitations_severe",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG196 §1.6",
        patient_facing_question=(
            "When the fluttering or racing happened, did you also get "
            "chest pain, breathlessness, or feel like you might pass out?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ stroke_signs — 3 FAST probes (all 999) ═════════════════════════
    # Face / Arm / Speech split. Each is a single observation. Time is
    # captured implicitly by the call timing. Coverage-check framing
    # for face/speech where the patient may not notice their own deficit
    # — asks whether anyone near them has commented.
    "stroke_signs_face_drooping": RedFlagProbe(
        flag_code="stroke_signs_face_drooping",
        parent_flag_code="stroke_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 / NG196",
        patient_facing_question=(
            "Has anyone noticed one side of your face looking droopy or "
            "uneven today — like one corner of your mouth not moving the "
            "same as the other?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stroke_signs_arm_weakness": RedFlagProbe(
        flag_code="stroke_signs_arm_weakness",
        parent_flag_code="stroke_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 / NG196",
        patient_facing_question=(
            "If you hold both arms out straight in front of you right now, "
            "does one drop down or feel weaker than the other?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stroke_signs_speech_difficulty": RedFlagProbe(
        flag_code="stroke_signs_speech_difficulty",
        parent_flag_code="stroke_signs",
        category=RedFlagCategory.NEW_FOCAL_NEURO,
        nice_basis="NG128 / NG196",
        patient_facing_question=(
            "Has your speech been slurred or harder to get out today, or "
            "has anyone said they're having trouble understanding you?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ haemorrhage — 4 probes by severity and site ═══════════════════
    # DOAC-associated bleeding. Three SAME_DAY probes for minor/moderate
    # bleeding sites; one EMERGENCY_999 for major events. Concrete
    # anchors throughout (10-minute bleed duration, visible blood loss).
    "haemorrhage_prolonged_nosebleed": RedFlagProbe(
        flag_code="haemorrhage_prolonged_nosebleed",
        parent_flag_code="haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG196 §1.5",
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
        nice_basis="NG196 §1.5",
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
        nice_basis="NG196 §1.5",
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
        nice_basis="NG196 §1.5",
        patient_facing_question=(
            "Have you vomited blood, coughed up blood, or had bleeding "
            "that you couldn't stop — from any part of your body — today?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ syncope — 2 probes (same pattern as K40) ═══════════════════════
    "syncope_blackout": RedFlagProbe(
        flag_code="syncope_blackout",
        parent_flag_code="syncope",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG196",
        patient_facing_question=(
            "Have you actually blacked out or fainted — lost consciousness "
            "even for a few seconds — in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "syncope_near_miss": RedFlagProbe(
        flag_code="syncope_near_miss",
        parent_flag_code="syncope",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG196",
        patient_facing_question=(
            "Have you felt like you were about to pass out — needing to "
            "sit or lie down quickly — but didn't actually faint?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ breathlessness_acute — 1 probe ═════════════════════════════════
    "breathlessness_acute": RedFlagProbe(
        flag_code="breathlessness_acute",
        parent_flag_code="breathlessness_acute",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG196",
        patient_facing_question=(
            "Have you had sudden severe breathlessness today — needing to "
            "work hard to breathe even while sitting still?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # CLINICAL_REVIEW_NEEDED: stroke_signs probes use coverage-check
    # framing for face-drooping and speech-difficulty because the
    # patient often cannot self-detect these deficits. Arm-weakness
    # probe asks the patient to do a live check (both arms out). Is
    # this active-participation probe safe via voice-agent phrasing,
    # or does it require a different conversational handoff?
}


# ═══════════════════════════════════════════════════════════════════════
# K60 — Heart Failure (Chronic HF / Post-Decompensation Discharge)
# Patient-facing wording audit: 2026-04-24 (new content, audited at draft)
# ═══════════════════════════════════════════════════════════════════════
#
# NICE NG106 post-discharge monitoring. 90-day window, 9 call days
# front-loaded because readmission risk is highest in first 30 days.
#
# Key decisions:
#   - NG106 red-flag set covers the classic decompensation triad:
#     2kg in 2 days weight gain, new or increased orthopnoea (glossed
#     as "needing to prop yourself up on pillows to breathe"), new
#     ankle swelling. All SAME_DAY. Plus breathlessness at rest and
#     chest pain which inherit the 999 / SAME_DAY split from K40.
#   - cardiac_rehab_referral uses coverage-check pattern (referral
#     tracked by team, not voice agent).
#   - renal_function domain uses symptom-proxy probes (less pee,
#     more tired) not blood results — the voice agent has no lab
#     access. RQ asks about symptoms; the GP team arranges bloods.
#   - Fluid restriction RQ is a behavioural-adherence check, not a
#     red flag — K60 patients are on daily 1.5-2L fluid caps.

K60_PLAYBOOK = PathwayPlaybook(
    opcs_code="K60",
    label="Heart Failure",
    category="medical",
    nice_ids=["CG187", "NG106", "QS9"],
    monitoring_window_days=90,
    call_days=[1, 3, 7, 14, 21, 30, 42, 60, 90],
    domains=[
        "daily_weight",
        "breathlessness_nyha",
        "ankle_swelling",
        "diuretic_adherence",
        "fluid_restriction",
        "renal_function",
        "blood_pressure",
        "cardiac_rehab_referral",
    ],
    red_flag_codes=[
        "breathlessness_at_rest",
        "weight_gain_2kg_2days",
        "oxygen_saturation_below_92",
        "chest_pain_at_rest",
        "chest_pain_on_minimal_exertion",
        "acute_confusion",
        "uncontrolled_oedema",
        "bp_crisis_above_180",
        "anuric_or_oliguria",
    ],
    validation_status=_DRAFT,
)


K60_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # daily_weight — NG106 (established habit; red-flag is 2kg in 2 days)
    _traj("K60", "daily_weight",  1, 1, 2, "Daily weight monitoring established, minor fluctuation expected", "NG106"),
    _traj("K60", "daily_weight",  3, 1, 1, "Weight stable or reducing with diuretics", "NG106"),
    _traj("K60", "daily_weight",  7, 1, 1, "Weight stable", "NG106"),
    _traj("K60", "daily_weight", 14, 1, 1, "Stable weight", "NG106"),
    _traj("K60", "daily_weight", 21, 1, 1, "Stable — daily weighing habit established", "NG106"),
    _traj("K60", "daily_weight", 30, 1, 1, "Stable", "NG106"),
    _traj("K60", "daily_weight", 42, 1, 1, "Stable — lifelong monitoring", "NG106"),
    _traj("K60", "daily_weight", 60, 1, 1, "Stable — monitoring ongoing", "NG106"),
    _traj("K60", "daily_weight", 90, 1, 1, "Stable — lifelong", "NG106"),

    # breathlessness_nyha — CG187 (NYHA functional class)
    _traj("K60", "breathlessness_nyha",  1, 2, 3, "NYHA III expected at discharge — breathlessness on mild exertion", "CG187"),
    _traj("K60", "breathlessness_nyha",  3, 2, 2, "NYHA II-III — breathlessness reducing", "CG187"),
    _traj("K60", "breathlessness_nyha",  7, 1, 2, "NYHA II — breathlessness on moderate exertion only", "CG187"),
    _traj("K60", "breathlessness_nyha", 14, 1, 1, "NYHA I-II — breathlessness only on significant exertion", "CG187"),
    _traj("K60", "breathlessness_nyha", 21, 1, 1, "NYHA I-II — stable", "CG187"),
    _traj("K60", "breathlessness_nyha", 30, 1, 1, "NYHA I-II — stable", "CG187"),
    _traj("K60", "breathlessness_nyha", 42, 0, 1, "NYHA I — near-baseline", "CG187"),
    _traj("K60", "breathlessness_nyha", 60, 0, 1, "NYHA I — baseline functional class", "CG187"),
    _traj("K60", "breathlessness_nyha", 90, 0, 1, "NYHA I — baseline", "CG187"),

    # ankle_swelling — NG106
    _traj("K60", "ankle_swelling",  1, 2, 3, "Ankle/peripheral oedema expected at discharge", "NG106"),
    _traj("K60", "ankle_swelling",  3, 1, 2, "Oedema reducing with diuretic therapy", "NG106"),
    _traj("K60", "ankle_swelling",  7, 1, 2, "Reducing oedema — should be improving", "NG106"),
    _traj("K60", "ankle_swelling", 14, 1, 1, "Minimal residual ankle swelling", "NG106"),
    _traj("K60", "ankle_swelling", 21, 1, 1, "Stable — minimal or no oedema", "NG106"),
    _traj("K60", "ankle_swelling", 30, 0, 1, "Resolved or trace", "NG106"),
    _traj("K60", "ankle_swelling", 42, 0, 1, "Resolved", "NG106"),
    _traj("K60", "ankle_swelling", 60, 0, 0, "Resolved", "NG106"),
    _traj("K60", "ankle_swelling", 90, 0, 0, "Resolved", "NG106"),

    # diuretic_adherence — NG106
    _traj("K60", "diuretic_adherence",  1, 1, 1, "All diuretic doses taken as prescribed", "NG106"),
    _traj("K60", "diuretic_adherence",  3, 1, 1, "Adherent", "NG106"),
    _traj("K60", "diuretic_adherence",  7, 1, 1, "Adherent — titration may have occurred", "NG106"),
    _traj("K60", "diuretic_adherence", 14, 1, 1, "Adherent", "NG106"),
    _traj("K60", "diuretic_adherence", 21, 1, 1, "Adherent", "NG106"),
    _traj("K60", "diuretic_adherence", 30, 1, 1, "Adherent — any self-adjustment discussed with team", "NG106"),
    _traj("K60", "diuretic_adherence", 42, 1, 1, "Adherent — lifelong", "NG106"),
    _traj("K60", "diuretic_adherence", 60, 1, 1, "Adherent — lifelong", "NG106"),
    _traj("K60", "diuretic_adherence", 90, 1, 1, "Adherent — lifelong", "NG106"),

    # fluid_restriction — NG106 (1.5-2L/day cap)
    _traj("K60", "fluid_restriction",  1, 1, 2, "Fluid restriction 1.5-2L/day advised — establishing habit", "NG106"),
    _traj("K60", "fluid_restriction",  3, 1, 1, "Fluid restriction established", "NG106"),
    _traj("K60", "fluid_restriction",  7, 1, 1, "Adherent to fluid restriction", "NG106"),
    _traj("K60", "fluid_restriction", 14, 1, 1, "Adherent", "NG106"),
    _traj("K60", "fluid_restriction", 21, 1, 1, "Adherent", "NG106"),
    _traj("K60", "fluid_restriction", 30, 1, 1, "Adherent", "NG106"),
    _traj("K60", "fluid_restriction", 42, 1, 1, "Adherent — lifelong habit", "NG106"),
    _traj("K60", "fluid_restriction", 60, 1, 1, "Adherent", "NG106"),
    _traj("K60", "fluid_restriction", 90, 1, 1, "Adherent", "NG106"),

    # renal_function — NG106 (symptom proxy)
    _traj("K60", "renal_function",  1, 1, 2, "Mild fatigue acceptable — diuretics may reduce urine output transiently", "NG106"),
    _traj("K60", "renal_function",  3, 1, 1, "Renal function stabilising", "NG106"),
    _traj("K60", "renal_function",  7, 1, 1, "Normal urine output restored", "NG106"),
    _traj("K60", "renal_function", 14, 0, 1, "Stable renal function", "NG106"),
    _traj("K60", "renal_function", 21, 0, 1, "Stable", "NG106"),
    _traj("K60", "renal_function", 30, 0, 1, "Stable", "NG106"),
    _traj("K60", "renal_function", 42, 0, 1, "Stable", "NG106"),
    _traj("K60", "renal_function", 60, 0, 0, "Stable — ongoing monitoring via bloods", "NG106"),
    _traj("K60", "renal_function", 90, 0, 0, "Stable", "NG106"),

    # blood_pressure — CG187 (target <130/80)
    _traj("K60", "blood_pressure",  1, 1, 2, "BP may be labile post-discharge — target <130/80", "CG187"),
    _traj("K60", "blood_pressure",  3, 1, 2, "BP stabilising on optimised therapy", "CG187"),
    _traj("K60", "blood_pressure",  7, 1, 1, "BP approaching target range", "CG187"),
    _traj("K60", "blood_pressure", 14, 1, 1, "BP at or near target", "CG187"),
    _traj("K60", "blood_pressure", 21, 1, 1, "BP controlled", "CG187"),
    _traj("K60", "blood_pressure", 30, 1, 1, "BP controlled — target <130/80", "CG187"),
    _traj("K60", "blood_pressure", 42, 0, 1, "BP stable at target", "CG187"),
    _traj("K60", "blood_pressure", 60, 0, 1, "BP stable", "CG187"),
    _traj("K60", "blood_pressure", 90, 0, 1, "BP stable", "CG187"),

    # cardiac_rehab_referral — NG106
    _traj("K60", "cardiac_rehab_referral",  1, 1, 2, "Cardiac rehab referral should be initiated at discharge", "NG106"),
    _traj("K60", "cardiac_rehab_referral",  3, 1, 1, "Referral in place — appointment expected", "NG106"),
    _traj("K60", "cardiac_rehab_referral",  7, 1, 1, "Referred — awaiting first session", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 14, 1, 1, "Rehab commenced or scheduled", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 21, 1, 1, "Attending", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 30, 0, 1, "Attending regularly", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 42, 0, 1, "Progressing well", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 60, 0, 0, "Rehab programme completed or ongoing", "NG106"),
    _traj("K60", "cardiac_rehab_referral", 90, 0, 0, "Completed or ongoing", "NG106"),
]


K60_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    # Daily weight is the single most important HF self-monitoring
    # behaviour. NG106 sets 2kg in 2 days as the decompensation trigger.
    _rq(
        "K60",
        "daily_weight",
        "Have you been weighing yourself each morning — and what's your weight been today compared to your usual? Any gain of more than a couple of pounds in the last day or two?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG106 §1.4",
    ),
    # First-use gloss for "orthopnoea" as plain-language description.
    _rq(
        "K60",
        "breathlessness_nyha",
        "How's your breathing today — can you walk around the house, and are you able to lie flat in bed or do you need to prop yourself up on pillows to breathe?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "CG187 §1.2",
    ),
    _rq(
        "K60",
        "ankle_swelling",
        "Any new or worsening swelling in your ankles, legs, or tummy — any that have come on in the last 24 hours?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG106 §1.4",
    ),
    _rq(
        "K60",
        "diuretic_adherence",
        "Are you managing the water tablets each day — and any dizziness, lightheadedness, or cramping that might go with them?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG106 §1.5",
    ),
    _rq(
        "K60",
        "fluid_restriction",
        "How are you getting on with the daily fluid limit the team set — are you staying under your target each day?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG106 §1.5",
    ),
    # Renal-function RQ asks about symptomatic proxies (less pee, more
    # tired) rather than blood results. Voice agent has no lab access;
    # the GP team arranges bloods.
    _rq(
        "K60",
        "renal_function",
        "How often are you peeing in a day compared to before you were admitted — much less, about the same, or more? Any feeling more tired or muddled than the last call?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG106 §1.6",
    ),
    _rq(
        "K60",
        "blood_pressure",
        "If you're checking your blood pressure at home, what have the readings been in the last few days?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "CG187 §1.3",
    ),
    # Coverage-check pattern for cardiac rehab.
    _rq(
        "K60",
        "cardiac_rehab_referral",
        "Has the cardiac rehab team been in touch with you yet — have you started any sessions, or do you know when they'll begin?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60), (61, 90)],
        "NG106 §1.7",
    ),
]


# ─── K60 Red Flag Probes ───────────────────────────────────────────────

K60_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ breathlessness_at_rest — 2 probes (rest + orthopnoea) ══════════
    # Orthopnoea (needing to prop up to breathe) is a specific HF
    # decompensation sign distinct from breathlessness at rest, so
    # split into two probes. Both 999 — NG106 classifies both as
    # emergency escalation for decompensating HF.
    "breathlessness_at_rest": RedFlagProbe(
        flag_code="breathlessness_at_rest",
        parent_flag_code="breathlessness_at_rest",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG106 §1.4 / CG187",
        patient_facing_question=(
            "Have you been breathless at rest — needing to work hard to "
            "breathe even while sitting still?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "breathlessness_orthopnoea_new": RedFlagProbe(
        flag_code="breathlessness_orthopnoea_new",
        parent_flag_code="breathlessness_at_rest",
        category=RedFlagCategory.ACUTE_SOB,
        nice_basis="NG106 §1.4 / CG187",
        patient_facing_question=(
            "Have you needed to prop yourself up on more pillows than usual "
            "to breathe at night, or have you woken up suddenly gasping "
            "for air, in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ weight_gain_2kg_2days — 1 probe (NG106 decompensation trigger) ═
    # Concrete threshold — 2kg (~4.5lb) in 2 days, no memory comparison.
    "weight_gain_2kg_2days": RedFlagProbe(
        flag_code="weight_gain_2kg_2days",
        parent_flag_code="weight_gain_2kg_2days",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.4",
        patient_facing_question=(
            "Have you gained more than about 4 pounds — or 2 kilos — in "
            "the last two days on your morning weighing?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ oxygen_saturation_below_92 — 1 probe (conditional on oximeter) ═
    # NG106 alert threshold for HF is <92 (vs <88 for COPD in J44).
    # Conditional on home equipment — follows the J44 pattern.
    "oxygen_saturation_below_92": RedFlagProbe(
        flag_code="oxygen_saturation_below_92",
        parent_flag_code="oxygen_saturation_below_92",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.4",
        patient_facing_question=(
            "If you have a pulse oximeter at home — that's the little "
            "finger clip that reads your blood oxygen — has the reading "
            "been below 92?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ chest_pain — 2 probes (inherited K40 pattern, adapted) ═════════
    # K60 cohort may have ischaemic HF aetiology; chest pain at rest in
    # this cohort can signal acute coronary syndrome or acute
    # decompensation. Rest-pain 999, minimal-exertion SAME_DAY.
    "chest_pain_at_rest": RedFlagProbe(
        flag_code="chest_pain_at_rest",
        parent_flag_code="chest_pain_at_rest",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG106 / NG185",
        patient_facing_question=(
            "Have you had chest pain that came on at rest — while sitting "
            "still, lying down, or not doing anything?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "chest_pain_on_minimal_exertion": RedFlagProbe(
        flag_code="chest_pain_on_minimal_exertion",
        parent_flag_code="chest_pain_on_minimal_exertion",
        category=RedFlagCategory.CHEST_PAIN,
        nice_basis="NG106 / NG185",
        patient_facing_question=(
            "Have you had chest pain come on with a small effort today — "
            "like standing up from a chair or walking across a room?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ acute_confusion — 1 probe (coverage-check) ═════════════════════
    # Acute confusion in HF can signal hypoperfusion, hyponatraemia, or
    # acute-on-chronic kidney injury from diuresis. Coverage-check
    # framing because patient may not self-detect. SAME_DAY escalation.
    "acute_confusion_new": RedFlagProbe(
        flag_code="acute_confusion_new",
        parent_flag_code="acute_confusion",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.6",
        patient_facing_question=(
            "Has anyone around you noticed you've become more muddled, "
            "confused, or less sharp than usual in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ uncontrolled_oedema — 2 probes ═════════════════════════════════
    # Sudden worsening of oedema despite diuretic adherence is a
    # decompensation sign. New-site oedema (tummy / face) is distinct
    # from ankle-to-leg progression.
    "oedema_sudden_worsening": RedFlagProbe(
        flag_code="oedema_sudden_worsening",
        parent_flag_code="uncontrolled_oedema",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.4",
        patient_facing_question=(
            "Has the swelling in your legs or ankles suddenly got much "
            "worse in the last 24 hours, even though you've been taking "
            "the water tablets?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "oedema_new_site": RedFlagProbe(
        flag_code="oedema_new_site",
        parent_flag_code="uncontrolled_oedema",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.4",
        patient_facing_question=(
            "Is there any new swelling in your tummy or around your "
            "middle, or is your face or hands looking puffy in the last "
            "24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ bp_crisis_above_180 — 1 probe (conditional on home BP monitor) ═
    "bp_crisis_above_180": RedFlagProbe(
        flag_code="bp_crisis_above_180",
        parent_flag_code="bp_crisis_above_180",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="CG187 §1.3 / NG136",
        patient_facing_question=(
            "If you've been checking your blood pressure at home — has "
            "the top number been over 180 on any reading in the last 24 "
            "hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ anuric_or_oliguria — 1 probe (symptom-proxy) ═══════════════════
    # Asks about urine output directly. "Anuric / oliguria" never
    # patient-facing.
    "anuric_or_oliguria": RedFlagProbe(
        flag_code="anuric_or_oliguria",
        parent_flag_code="anuric_or_oliguria",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG106 §1.6",
        patient_facing_question=(
            "Have you not peed at all for more than 12 hours, or been "
            "peeing much less than you normally do despite drinking fluids?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # CLINICAL_REVIEW_NEEDED: K60 chest_pain probes use the same
    # parent codes as K40 / K40_CABG (chest_pain_at_rest + chest_pain_
    # on_minimal_exertion). Reviewer to confirm whether K60-specific
    # compound rule should exist at Phase 4 — chest pain + breathless-
    # ness at rest + weight gain + new oedema is the acute-on-chronic
    # decompensation picture and warrants EMERGENCY_999.
    #
    # CLINICAL_REVIEW_NEEDED: anuric_or_oliguria probe uses 12-hour
    # anuria threshold. Reviewer to confirm this is the correct voice-
    # agent threshold (some NG106 local protocols use 8 hours).
    #
    # CLINICAL_REVIEW_NEEDED: bp_crisis_above_180 probe conditional on
    # home BP monitor. Reviewer to confirm whether the voice agent
    # should offer an in-clinic BP check path for patients without a
    # home monitor (rather than no probe at all).
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "K40": K40_PLAYBOOK,
    "K40_CABG": K40_CABG_PLAYBOOK,
    "K57": K57_PLAYBOOK,
    "K60": K60_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "K40": K40_TRAJECTORIES,
    "K40_CABG": K40_CABG_TRAJECTORIES,
    "K57": K57_TRAJECTORIES,
    "K60": K60_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "K40": K40_REQUIRED_QUESTIONS,
    "K40_CABG": K40_CABG_REQUIRED_QUESTIONS,
    "K57": K57_REQUIRED_QUESTIONS,
    "K60": K60_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "K40": K40_RED_FLAG_PROBES,
    "K40_CABG": K40_CABG_RED_FLAG_PROBES,
    "K57": K57_RED_FLAG_PROBES,
    "K60": K60_RED_FLAG_PROBES,
}

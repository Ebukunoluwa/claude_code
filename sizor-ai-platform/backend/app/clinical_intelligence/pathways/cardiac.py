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


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "K40": K40_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "K40": K40_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "K40": K40_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "K40": K40_RED_FLAG_PROBES,
}

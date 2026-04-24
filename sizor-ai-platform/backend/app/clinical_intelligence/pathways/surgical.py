"""Surgical pathways — H01, H04.

Phase 3 surgical cluster. Following the orthopaedic template but with
surgical-specific divergences:

  - H01 (appendectomy) and H04 (colectomy) are abdominal operations,
    so dvt_symptoms probes do not split by operated/non-operated leg
    as the orthopaedic cluster does; instead a single bilateral-check
    probe is used.
  - abscess (H01) and anastomotic_leak_signs (H04) are net-new parent
    flag codes for this cluster. Abscess is typically SAME_DAY,
    anastomotic leak is EMERGENCY_999 across all three constituent
    probes — it is a surgical emergency with high mortality if missed.
  - bowel_obstruction appears in both. Split into three probes:
    vomiting, absent flatus/stool, distension-with-colic. All
    SAME_DAY individually; co-firing of all three is the classic
    triad that should escalate at the Phase 4 call-status layer.
  - stoma_complications (H04) applies conditionally — not all H04
    patients have a stoma. Probes are written so they return a
    not-applicable signal naturally if no stoma is present.

Wording principles applied throughout (same as orthopaedic):
  No patient-memory-comparison phrasings. Use concrete anchors:
  spreading redness, 24-hour change windows, absolute thresholds,
  behavioural anchors, or coverage-check phrasings where the
  patient cannot reliably self-observe.

Primary NICE sources: NG61 (suspected acute appendicitis),
NG147 (perioperative care), NG89 (VTE), QS48 (SSI), NG51 (sepsis).
Reviewer specialty: General surgeon (H01), Colorectal surgeon (H04).
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
# H01 — Appendectomy
# ═══════════════════════════════════════════════════════════════════════

H01_PLAYBOOK = PathwayPlaybook(
    opcs_code="H01",
    label="Appendectomy",
    category="surgical",
    nice_ids=["NG61", "QS48"],
    monitoring_window_days=28,
    call_days=[1, 3, 7, 14, 21, 28],
    domains=[
        "wound_healing",
        "pain_management",
        "bowel_function",
        "infection_signs",
        "return_to_activity",
    ],
    red_flag_codes=[
        "wound_infection",
        "abscess",
        "bowel_obstruction",
        "fever_above_38_5",
    ],
    validation_status=_DRAFT,
)


H01_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG61
    _traj("H01", "wound_healing",  1, 2, 3, "Wound intact", "NG61"),
    _traj("H01", "wound_healing",  3, 2, 3, "Healing, minor seepage acceptable", "NG61"),
    _traj("H01", "wound_healing",  7, 1, 2, "Healing well", "NG61"),
    _traj("H01", "wound_healing", 14, 1, 1, "Well healed", "NG61"),
    _traj("H01", "wound_healing", 21, 0, 1, "Healed", "NG61"),
    _traj("H01", "wound_healing", 28, 0, 0, "Fully healed", "NG61"),

    # pain_management — NG61
    _traj("H01", "pain_management",  1, 2, 3, "Post-op pain expected", "NG61"),
    _traj("H01", "pain_management",  3, 2, 2, "Reducing with analgesia", "NG61"),
    _traj("H01", "pain_management",  7, 1, 2, "Mild pain", "NG61"),
    _traj("H01", "pain_management", 14, 1, 1, "Minimal pain", "NG61"),
    _traj("H01", "pain_management", 21, 0, 1, "Resolving", "NG61"),
    _traj("H01", "pain_management", 28, 0, 0, "Resolved", "NG61"),

    # bowel_function — NG61
    _traj("H01", "bowel_function",  1, 2, 3, "Flatus present, bowels settling", "NG61"),
    _traj("H01", "bowel_function",  3, 1, 2, "Bowels open", "NG61"),
    _traj("H01", "bowel_function",  7, 1, 1, "Normal function", "NG61"),
    _traj("H01", "bowel_function", 14, 0, 1, "Normal", "NG61"),
    _traj("H01", "bowel_function", 21, 0, 1, "Normal", "NG61"),
    _traj("H01", "bowel_function", 28, 0, 0, "Normal", "NG61"),

    # infection_signs — QS48
    _traj("H01", "infection_signs",  1, 1, 2, "Normal inflammation", "NG61"),
    _traj("H01", "infection_signs",  3, 1, 2, "Monitor for redness/discharge", "NG61"),
    _traj("H01", "infection_signs",  7, 1, 2, "Settling", "NG61"),
    _traj("H01", "infection_signs", 14, 0, 1, "No signs expected", "NG61"),
    _traj("H01", "infection_signs", 21, 0, 1, "No signs expected", "NG61"),
    _traj("H01", "infection_signs", 28, 0, 0, "Clear", "NG61"),

    # return_to_activity — NG61
    _traj("H01", "return_to_activity",  1, 2, 3, "Rest — light activity only", "NG61"),
    _traj("H01", "return_to_activity",  3, 2, 2, "Light activity", "NG61"),
    _traj("H01", "return_to_activity",  7, 1, 2, "Increasing activity", "NG61"),
    _traj("H01", "return_to_activity", 14, 1, 1, "Most activities resumed", "NG61"),
    _traj("H01", "return_to_activity", 21, 0, 1, "Full activity expected", "NG61"),
    _traj("H01", "return_to_activity", 28, 0, 0, "Fully active", "NG61"),
]


H01_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    _rq(
        "H01",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG61 / QS48",
    ),
    _rq(
        "H01",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable, and has the pain been settling rather than getting worse day-on-day?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG61",
    ),
    _rq(
        "H01",
        "bowel_function",
        "Have you been pooing normally, and farting without difficulty — any new diarrhoea, constipation, or urgency?",
        [(1, 3), (4, 7), (8, 14)],
        "NG61",
    ),
    _rq(
        "H01",
        "infection_signs",
        "Any heat or redness around the wound that has spread further than the scar area, a fever in the last 24 hours, or feeling generally unwell?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "QS48",
    ),
    _rq(
        "H01",
        "return_to_activity",
        "How's your day-to-day activity — back to light tasks, managing stairs, and have you been advised on when to return to work or heavy lifting?",
        [(4, 7), (8, 14), (15, 28)],
        "NG61",
    ),
]


# ─── H01 Red Flag Probes ───────────────────────────────────────────────

H01_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ wound_infection — 2 probes ═════════════════════════════════════
    # Standard elective-surgery wound infection pattern. Both SAME_DAY
    # (H01 cohort is typically young adult, not the elevated-sepsis-
    # risk cohort of W38).
    "wound_infection_spreading_redness": RedFlagProbe(
        flag_code="wound_infection_spreading_redness",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG61",
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
        nice_basis="QS48 / NG61",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ abscess — 3 probes (all SAME_DAY) ══════════════════════════════
    # Post-appendectomy abscess (pelvic or paracolic) classically
    # presents with the "failure to thrive" pattern — initial
    # improvement followed by deterioration at days 5-10. Three probes:
    #   - deep localised pain (not the wound itself)
    #   - fever returning after initial improvement
    #   - bowel/bladder urgency suggesting pelvic collection
    "abscess_deep_pain": RedFlagProbe(
        flag_code="abscess_deep_pain",
        parent_flag_code="abscess",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG61 / QS48",
        patient_facing_question=(
            "Any new pain deeper inside your tummy or pelvis — lower or "
            "further in than the scar area itself?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "abscess_fever_returning": RedFlagProbe(
        flag_code="abscess_fever_returning",
        parent_flag_code="abscess",
        category=RedFlagCategory.SEPSIS_SIGNS,
        nice_basis="NG61 / QS48",
        patient_facing_question=(
            "Did you start to feel better for a few days and now you're "
            "feeling feverish or unwell again in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "abscess_bowel_bladder_urgency": RedFlagProbe(
        flag_code="abscess_bowel_bladder_urgency",
        parent_flag_code="abscess",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG61 / QS48",
        patient_facing_question=(
            "Any new urgency to poo, passing mucus from your bum, or a "
            "feeling of pressure or fullness low down?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: abscess probes set to SAME_DAY individually.
    # Compound rule for Phase 4 call-status layer — two+ abscess probes
    # firing with any fever probe firing should escalate to
    # EMERGENCY_999 (suspected septic pelvic/paracolic collection).

    # ══ bowel_obstruction — 3 probes ═══════════════════════════════════
    # Classic triad: vomiting, absolute constipation (no flatus or stool),
    # distension with colicky pain. Individual probes SAME_DAY; co-firing
    # of all three is the diagnostic triad and should escalate at the
    # Phase 4 call-status layer.
    "bowel_obstruction_vomiting": RedFlagProbe(
        flag_code="bowel_obstruction_vomiting",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG61",
        patient_facing_question=(
            "Have you been vomiting and unable to keep fluids down in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "bowel_obstruction_no_wind_or_stool": RedFlagProbe(
        flag_code="bowel_obstruction_no_wind_or_stool",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG61",
        patient_facing_question=(
            "Have you not farted or pooed for more than 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "bowel_obstruction_distension_colic": RedFlagProbe(
        flag_code="bowel_obstruction_distension_colic",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG61",
        patient_facing_question=(
            "Does your tummy feel swollen and tight, with waves of cramping pain?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: bowel_obstruction probes all SAME_DAY
    # individually. Co-firing of vomiting + no_wind_or_stool +
    # distension_colic is the classic diagnostic triad and should
    # escalate to EMERGENCY_999 at the Phase 4 call-status layer —
    # a fully obstructed bowel is a surgical emergency.

    # ══ fever_above_38_5 — 3 probes ════════════════════════════════════
    # Ported verbatim from W37/W40/W43 with identical thresholds and
    # escalations.
    "fever_above_38_5_reading": RedFlagProbe(
        flag_code="fever_above_38_5_reading",
        parent_flag_code="fever_above_38_5",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG61",
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
        nice_basis="QS48 / NG61",
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
}


# ═══════════════════════════════════════════════════════════════════════
# H04 — Colectomy / Bowel Surgery
# ═══════════════════════════════════════════════════════════════════════
#
# Larger abdominal operation than H01. Longer monitoring window (60
# days) and a richer domain set: bowel_function_recovery, stoma_care,
# diet_and_nutrition, vte_prophylaxis (28-day LMWH course per NG89
# for abdominal surgery with cancer or IBD indication).
#
# Divergences from H01:
#   - anastomotic_leak_signs is the signature H04 red flag. All three
#     probes EMERGENCY_999 — anastomotic leak is a surgical emergency
#     with high mortality if missed. Typically presents days 3-5
#     post-op with fever + pain + systemic deterioration.
#   - stoma_complications applies conditionally (not all H04 patients
#     have a stoma). Probes are written to return a natural "not
#     applicable" signal if no stoma is present.
#   - dvt_symptoms is a single-probe "either leg" check (abdominal
#     surgery has no operated vs non-operated leg distinction, unlike
#     the orthopaedic cluster's split).
#   - fever is covered by the anastomotic_leak_fever probe + the
#     infection-framed RQ; no separate fever_above_38_5 probe set in
#     the upstream pathway_map for H04.

H04_PLAYBOOK = PathwayPlaybook(
    opcs_code="H04",
    label="Colectomy / Bowel Surgery",
    category="surgical",
    nice_ids=["NG147", "QS48", "NG89"],
    monitoring_window_days=60,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60],
    domains=[
        "wound_healing",
        "bowel_function_recovery",
        "stoma_care",
        "pain_management",
        "diet_and_nutrition",
        "vte_prophylaxis",
    ],
    red_flag_codes=[
        "anastomotic_leak_signs",
        "bowel_obstruction",
        "wound_infection",
        "dvt_symptoms",
        "stoma_complications",
    ],
    validation_status=_DRAFT,
)


H04_TRAJECTORIES: list[DomainTrajectoryEntry] = [
    # wound_healing — NG147
    _traj("H04", "wound_healing",  1, 2, 3, "Wound intact", "NG147"),
    _traj("H04", "wound_healing",  3, 2, 3, "Minor seepage acceptable", "NG147"),
    _traj("H04", "wound_healing",  7, 1, 2, "Healing", "NG147"),
    _traj("H04", "wound_healing", 14, 1, 2, "Healing well", "NG147"),
    _traj("H04", "wound_healing", 21, 1, 1, "Well healed", "NG147"),
    _traj("H04", "wound_healing", 28, 0, 1, "Healed", "NG147"),
    _traj("H04", "wound_healing", 42, 0, 1, "Healed", "NG147"),
    _traj("H04", "wound_healing", 60, 0, 0, "Fully healed", "NG147"),

    # bowel_function_recovery — NG147
    _traj("H04", "bowel_function_recovery",  1, 2, 3, "Flatus expected — bowels not yet open", "NG147"),
    _traj("H04", "bowel_function_recovery",  3, 2, 3, "First bowel movement expected", "NG147"),
    _traj("H04", "bowel_function_recovery",  7, 1, 2, "Bowels functioning, loose stool normal", "NG147"),
    _traj("H04", "bowel_function_recovery", 14, 1, 2, "Improving regularity", "NG147"),
    _traj("H04", "bowel_function_recovery", 21, 1, 1, "Near-normal function", "NG147"),
    _traj("H04", "bowel_function_recovery", 28, 1, 1, "Normal function", "NG147"),
    _traj("H04", "bowel_function_recovery", 42, 0, 1, "Normal", "NG147"),
    _traj("H04", "bowel_function_recovery", 60, 0, 0, "Normal", "NG147"),

    # stoma_care — NG147 (conditional on stoma presence)
    _traj("H04", "stoma_care",  1, 2, 3, "Stoma established, nurse input", "NG147"),
    _traj("H04", "stoma_care",  3, 2, 3, "Patient learning stoma care", "NG147"),
    _traj("H04", "stoma_care",  7, 1, 2, "Managing stoma", "NG147"),
    _traj("H04", "stoma_care", 14, 1, 2, "Independent stoma care", "NG147"),
    _traj("H04", "stoma_care", 21, 1, 1, "Confident with stoma care", "NG147"),
    _traj("H04", "stoma_care", 28, 1, 1, "Independent", "NG147"),
    _traj("H04", "stoma_care", 42, 0, 1, "Established routine", "NG147"),
    _traj("H04", "stoma_care", 60, 0, 1, "Established routine", "NG147"),

    # pain_management — NG147
    _traj("H04", "pain_management",  1, 2, 3, "Post-op pain expected", "NG147"),
    _traj("H04", "pain_management",  3, 2, 3, "Reducing with analgesia", "NG147"),
    _traj("H04", "pain_management",  7, 2, 2, "Mild-moderate pain", "NG147"),
    _traj("H04", "pain_management", 14, 1, 2, "Reducing pain", "NG147"),
    _traj("H04", "pain_management", 21, 1, 1, "Minimal pain", "NG147"),
    _traj("H04", "pain_management", 28, 0, 1, "Resolving", "NG147"),
    _traj("H04", "pain_management", 42, 0, 1, "Resolved", "NG147"),
    _traj("H04", "pain_management", 60, 0, 0, "Resolved", "NG147"),

    # diet_and_nutrition — NG147
    _traj("H04", "diet_and_nutrition",  1, 2, 3, "Sips/light diet only", "NG147"),
    _traj("H04", "diet_and_nutrition",  3, 2, 2, "Progressing diet", "NG147"),
    _traj("H04", "diet_and_nutrition",  7, 1, 2, "Eating well", "NG147"),
    _traj("H04", "diet_and_nutrition", 14, 1, 1, "Normal diet", "NG147"),
    _traj("H04", "diet_and_nutrition", 21, 1, 1, "Normal diet", "NG147"),
    _traj("H04", "diet_and_nutrition", 28, 0, 1, "Normal diet", "NG147"),
    _traj("H04", "diet_and_nutrition", 42, 0, 1, "Normal diet", "NG147"),
    _traj("H04", "diet_and_nutrition", 60, 0, 0, "Normal diet", "NG147"),

    # vte_prophylaxis — NG89 §1.3 (28-day course for major abdominal surgery)
    _traj("H04", "vte_prophylaxis",  1, 1, 2, "LMWH commenced", "NG89"),
    _traj("H04", "vte_prophylaxis",  3, 1, 2, "Adherent", "NG89"),
    _traj("H04", "vte_prophylaxis",  7, 1, 2, "Adherent", "NG89"),
    _traj("H04", "vte_prophylaxis", 14, 1, 2, "Adherent", "NG89"),
    _traj("H04", "vte_prophylaxis", 21, 1, 2, "Adherent", "NG89"),
    _traj("H04", "vte_prophylaxis", 28, 1, 1, "28-day course completed", "NG89"),
    _traj("H04", "vte_prophylaxis", 42, 0, 1, "Completed", "NG89"),
    _traj("H04", "vte_prophylaxis", 60, 0, 0, "N/A", "NG89"),
]


H04_REQUIRED_QUESTIONS: list[RequiredQuestion] = [
    _rq(
        "H04",
        "wound_healing",
        "How is the wound looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG147 / QS48",
    ),
    _rq(
        "H04",
        "bowel_function_recovery",
        "Have you been farting and pooing, and how is the poo — watery, formed, any blood?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG147",
    ),
    # Stoma RQ phrased with "stoma bag" so a non-stoma patient can
    # simply answer "I don't have a stoma bag" and the voice agent
    # can move on without scoring.
    _rq(
        "H04",
        "stoma_care",
        "If you have a stoma bag — how are you managing the bag changes, how does the skin around it look, and are you getting the amount you'd expect?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG147",
    ),
    _rq(
        "H04",
        "pain_management",
        "How is the pain — are the painkillers keeping things manageable, and has the pain been settling rather than getting worse day-on-day?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG147",
    ),
    _rq(
        "H04",
        "diet_and_nutrition",
        "How is your eating and drinking — keeping food down, and any change in your weight since you came home?",
        [(1, 3), (4, 7), (8, 14), (15, 28), (29, 60)],
        "NG147",
    ),
    _rq(
        "H04",
        "vte_prophylaxis",
        "Are you managing the blood-thinning injections each day, and how is the injection site?",
        [(1, 3), (4, 7), (8, 14), (15, 28)],
        "NG89 §1.3",
    ),

    # Day 29-60: recovery milestones
    _rq(
        "H04",
        "bowel_function_recovery",
        "How is your bowel function settling into a pattern — regular, predictable, or still unpredictable?",
        [(29, 60)],
        "NG147",
    ),
]


# ─── H04 Red Flag Probes ───────────────────────────────────────────────

H04_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {

    # ══ anastomotic_leak_signs — 3 probes (all EMERGENCY_999) ══════════
    # Anastomotic leak is the signature H04 surgical emergency. Mortality
    # is high if missed. Classic presentation is days 3-5 post-op with
    # a combination of: severe/worsening abdominal pain, new fever with
    # tachycardia, and the "failure to thrive" feeling (patient was
    # recovering, now deteriorating). All three probes are 999 because
    # even individual signs warrant immediate surgical assessment.
    "anastomotic_leak_severe_pain": RedFlagProbe(
        flag_code="anastomotic_leak_severe_pain",
        parent_flag_code="anastomotic_leak_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147 §1.6 / QS48",
        patient_facing_question=(
            "Has the tummy pain become severe in the last 24 hours — the "
            "kind of pain that stops you moving, or pain spreading across "
            "the whole tummy?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "anastomotic_leak_new_fever": RedFlagProbe(
        flag_code="anastomotic_leak_new_fever",
        parent_flag_code="anastomotic_leak_signs",
        category=RedFlagCategory.SEPSIS_SIGNS,
        nice_basis="NG147 §1.6 / NG51 §1.1",
        patient_facing_question=(
            "Have you had a new fever or felt very hot-and-cold in the last "
            "24 hours — especially after starting to feel better earlier?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "anastomotic_leak_failure_to_thrive": RedFlagProbe(
        flag_code="anastomotic_leak_failure_to_thrive",
        parent_flag_code="anastomotic_leak_signs",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147 §1.6",
        patient_facing_question=(
            "Had you been getting better day-by-day, but now in the last "
            "24 hours you feel much worse or suddenly very unwell?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ bowel_obstruction — 3 probes (same pattern as H01) ═════════════
    "bowel_obstruction_vomiting": RedFlagProbe(
        flag_code="bowel_obstruction_vomiting",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147",
        patient_facing_question=(
            "Have you been vomiting and unable to keep fluids down in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "bowel_obstruction_no_wind_or_stool": RedFlagProbe(
        flag_code="bowel_obstruction_no_wind_or_stool",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147",
        patient_facing_question=(
            "Have you not farted or pooed for more than 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    "bowel_obstruction_distension_colic": RedFlagProbe(
        flag_code="bowel_obstruction_distension_colic",
        parent_flag_code="bowel_obstruction",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147",
        patient_facing_question=(
            "Does your tummy feel swollen and tight, with waves of cramping pain?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: bowel_obstruction probes all SAME_DAY
    # individually. Co-firing of vomiting + no_wind_or_stool +
    # distension_colic is the classic diagnostic triad and should
    # escalate to EMERGENCY_999 at the Phase 4 call-status layer.

    # ══ wound_infection — 2 probes ═════════════════════════════════════
    "wound_infection_spreading_redness": RedFlagProbe(
        flag_code="wound_infection_spreading_redness",
        parent_flag_code="wound_infection",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="QS48 / NG147",
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
        nice_basis="QS48 / NG147",
        patient_facing_question=(
            "Is there any pus or bloody fluid coming from the wound?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),

    # ══ dvt_symptoms — single probe (abdominal surgery, no leg split) ══
    # Unlike orthopaedic pathways, H04 has no operated vs non-operated
    # leg distinction. Single bilateral-check probe; patient prompted
    # to examine both calves.
    "dvt_symptoms_either_leg": RedFlagProbe(
        flag_code="dvt_symptoms_either_leg",
        parent_flag_code="dvt_symptoms",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG89 §1.3 / NG158",
        patient_facing_question=(
            "Looking at both calves — any new pain, swelling, warmth, or "
            "tenderness in either one in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),

    # ══ stoma_complications — 3 probes (conditional on stoma) ══════════
    # Applies only if patient has a stoma (not all H04 procedures). Probe
    # wording allows a non-stoma patient to answer "N/A" naturally. Three
    # probes cover the priority complications:
    #   - no output for >24h (obstruction / ileus) — 999
    #   - active bleeding from the stoma — 999
    #   - severe skin breakdown or stoma retraction — SAME_DAY
    "stoma_complications_no_output": RedFlagProbe(
        flag_code="stoma_complications_no_output",
        parent_flag_code="stoma_complications",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147 §1.8",
        patient_facing_question=(
            "If you have a stoma bag — has the bag been empty for more "
            "than 24 hours, or has it suddenly stopped filling?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stoma_complications_bleeding": RedFlagProbe(
        flag_code="stoma_complications_bleeding",
        parent_flag_code="stoma_complications",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG147 §1.8",
        patient_facing_question=(
            "If you have a stoma bag — is there fresh blood coming from "
            "the opening itself, more than a small streak?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status=_DRAFT,
    ),
    "stoma_complications_skin_or_appearance": RedFlagProbe(
        flag_code="stoma_complications_skin_or_appearance",
        parent_flag_code="stoma_complications",
        category=RedFlagCategory.PATHWAY_SPECIFIC,
        nice_basis="NG147 §1.8",
        patient_facing_question=(
            "If you have a stoma bag — has the skin around it become raw, "
            "broken, or bleeding, or has the opening itself changed shape, "
            "sunk further in, or come further out in the last 24 hours?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status=_DRAFT,
    ),
    # CLINICAL_REVIEW_NEEDED: stoma_complications probes are
    # conditional on stoma presence. Current draft relies on
    # patient-facing "if you have a stoma" prefixing to let non-stoma
    # patients answer N/A naturally. Reviewer to confirm whether the
    # voice agent layer should explicitly gate these probes behind a
    # pathway-intake "do you have a stoma?" flag rather than relying
    # on the prefix, which may produce ambiguous scoring if the
    # patient doesn't explicitly negate.
    #
    # CLINICAL_REVIEW_NEEDED: H04 upstream pathway_map does not list a
    # separate fever_above_38_5 red flag (unlike W37/W40/W43/H01).
    # Fever coverage here happens via anastomotic_leak_new_fever (999)
    # + the infection-framed wound_healing RQ. Reviewer to confirm
    # whether this is sufficient, or whether the standard 3-probe
    # fever set should be added (would duplicate anastomotic_leak_new
    # _fever signal but would catch non-anastomotic sources).
}


# ─── Module-level registries ───────────────────────────────────────────

PATHWAYS: dict[str, PathwayPlaybook] = {
    "H01": H01_PLAYBOOK,
    "H04": H04_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "H01": H01_TRAJECTORIES,
    "H04": H04_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "H01": H01_REQUIRED_QUESTIONS,
    "H04": H04_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "H01": H01_RED_FLAG_PROBES,
    "H04": H04_RED_FLAG_PROBES,
}

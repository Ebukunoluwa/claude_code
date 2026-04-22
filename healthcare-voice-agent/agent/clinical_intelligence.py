"""
clinical_intelligence.py — Sizor Clinical Intelligence Module
==============================================================
Self-contained module. No external dependencies beyond Python stdlib.

Encodes NICE-grounded benchmark data for all active Sizor pathways and provides
scoring, trajectory, and call-prompt generation functions.

Pathways covered
----------------
  W37  Total Hip Replacement          (NG226 / TA455 / QS48 / QS89 / NG89)
  W38  Hip Fracture / Hemiarthroplasty (NG124 / NG226 / QS16 / QS89)
  W40  Total Knee Replacement         (NG226 / TA304 / QS48 / QS89)
  W43  Unicompartmental Knee Replacement (NG226 / QS48 / QS89)
  K40_CABG  Coronary Artery Bypass Graft (NG185 / CG172 / QS99 / NG238)
  K40  Myocardial Infarction / ACS    (NG185 / QS99 / CG172)
  K57  Atrial Fibrillation            (NG196 / QS93 / TA249)
  K60  Heart Failure                  (CG187 / NG106 / QS9)
  R17  Elective Caesarean Section     (NG192 / QS32 / NG194 / NG89)
  R18  Emergency Caesarean Section    (NG192 / NG194 / QS32)
  J44  COPD Exacerbation              (NG115 / QS10)
  S01  Stroke / Ischaemic             (NG128 / CG162 / QS2 / NG185)
  H04  Colectomy / Bowel Surgery      (NG147 / QS48 / NG89)
  H01  Appendectomy                   (NG61 / QS48)
  Z03_MH  Acute Psychiatric Admission (CG136 / NG10 / QS80)

Domain trajectory tuple format (stored in DOMAIN_TRAJECTORIES):
  (expected_score, upper_bound, label, nice_source)

Status thresholds (score 0-4):
  0          → "resolved"
  ≤ expected → "expected"
  > expected, ≤ upper_bound → "monitor"
  > upper_bound, < 4        → "expedite"
  == 4                      → "escalate"
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# PLAYBOOKS
# One entry per pathway code. Contains metadata and NICE domain definitions.
# ═══════════════════════════════════════════════════════════════════════════

PLAYBOOKS: dict[str, dict] = {

    "W37": {
        "label": "Total Hip Replacement",
        "category": "surgical",
        "nice_ids": ["NG226", "TA455", "QS48", "QS89", "NG89"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "wound_healing", "pain_management", "vte_prophylaxis",
            "mobility_progress", "infection_signs", "physiotherapy_compliance",
        ],
        "red_flags": [
            "wound_dehiscence", "dvt_symptoms", "hip_dislocation",
            "fever_above_38_5", "pe_symptoms",
        ],
    },

    "W38": {
        "label": "Hip Fracture / Hemiarthroplasty",
        "category": "surgical",
        "nice_ids": ["NG124", "NG226", "QS16", "QS89"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "wound_healing", "pain_management", "delirium_cognitive_screen",
            "falls_risk", "vte_prophylaxis", "mobility_and_rehabilitation",
        ],
        "red_flags": [
            "delirium_acute", "dvt_symptoms", "pe_symptoms",
            "wound_infection", "falls_with_injury",
        ],
    },

    "W40": {
        "label": "Total Knee Replacement",
        "category": "surgical",
        "nice_ids": ["NG226", "TA304", "QS48", "QS89"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "wound_healing", "pain_management", "vte_prophylaxis",
            "mobility_progress", "infection_signs", "physiotherapy_compliance",
        ],
        "red_flags": [
            "wound_dehiscence", "dvt_symptoms", "fever_above_38_5",
            "pe_symptoms", "knee_effusion_severe",
        ],
    },

    "W43": {
        "label": "Unicompartmental Knee Replacement",
        "category": "surgical",
        "nice_ids": ["NG226", "QS48", "QS89"],
        "monitoring_window_days": 42,
        "call_days": [1, 3, 7, 14, 21, 28, 42],
        "domains": [
            "wound_healing", "pain_management", "vte_prophylaxis",
            "mobility_progress", "physiotherapy_compliance",
        ],
        "red_flags": [
            "dvt_symptoms", "wound_infection", "pe_symptoms", "persistent_swelling",
        ],
    },

    "K40_CABG": {
        "label": "Coronary Artery Bypass Graft",
        "category": "surgical",
        "nice_ids": ["NG185", "CG172", "QS99", "NG238"],
        "monitoring_window_days": 90,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60, 90],
        "domains": [
            "sternal_wound_healing", "leg_wound_healing", "chest_pain_recurrence",
            "antiplatelet_adherence", "cardiac_rehab_attendance",
            "mood_and_depression", "mobility_and_fatigue",
        ],
        "red_flags": [
            "chest_pain_at_rest", "sternal_wound_breakdown", "pe_symptoms",
            "cardiac_arrest_signs", "sustained_palpitations",
        ],
    },

    "K40": {
        "label": "Myocardial Infarction / ACS",
        "category": "medical",
        "nice_ids": ["NG185", "QS99", "CG172"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "chest_pain_monitoring", "antiplatelet_adherence",
            "cardiac_rehab_attendance", "mood_and_depression",
            "activity_progression", "risk_factor_modification",
        ],
        "red_flags": [
            "chest_pain_at_rest", "syncope", "sustained_palpitations",
            "breathlessness_at_rest", "pe_symptoms",
        ],
    },

    "K57": {
        "label": "Atrial Fibrillation",
        "category": "medical",
        "nice_ids": ["NG196", "QS93", "TA249"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "rate_control_monitoring", "anticoagulation_adherence",
            "symptom_monitoring", "bleeding_signs", "mood_and_anxiety",
        ],
        "red_flags": [
            "palpitations_severe", "stroke_signs", "haemorrhage",
            "syncope", "breathlessness_acute",
        ],
    },

    "K60": {
        "label": "Heart Failure",
        "category": "medical",
        "nice_ids": ["CG187", "NG106", "QS9"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "breathlessness", "oedema_monitoring", "medication_adherence",
            "weight_monitoring", "activity_tolerance", "mood_and_anxiety",
        ],
        "red_flags": [
            "breathlessness_at_rest", "weight_gain_2kg_2days",
            "oxygen_saturation_below_92", "chest_pain",
            "acute_confusion", "uncontrolled_oedema",
        ],
    },

    "R17": {
        "label": "Elective Caesarean Section",
        "category": "obstetric",
        "nice_ids": ["NG192", "QS32", "NG194", "NG89"],
        "monitoring_window_days": 42,
        "call_days": [1, 3, 5, 7, 10, 14, 21, 28],
        "domains": [
            "wound_healing", "pain_management", "lochia_monitoring",
            "vte_prophylaxis", "postnatal_mood", "mobility", "infant_feeding",
        ],
        "red_flags": [
            "wound_dehiscence", "postpartum_haemorrhage", "pe_symptoms",
            "pre_eclampsia_signs", "postnatal_depression_severe", "infant_feeding_failure",
        ],
    },

    "R18": {
        "label": "Emergency Caesarean Section",
        "category": "obstetric",
        "nice_ids": ["NG192", "NG194", "QS32"],
        "monitoring_window_days": 42,
        "call_days": [1, 3, 5, 7, 10, 14, 21, 28],
        "domains": [
            "wound_healing", "pain_management", "lochia_monitoring",
            "vte_prophylaxis", "postnatal_mood", "mobility",
            "infant_feeding", "emotional_recovery",
        ],
        "red_flags": [
            "wound_dehiscence", "postpartum_haemorrhage", "pe_symptoms",
            "pre_eclampsia_signs", "postnatal_depression_severe", "ptsd_symptoms",
        ],
    },

    "J44": {
        "label": "COPD Exacerbation",
        "category": "respiratory",
        "nice_ids": ["NG115", "QS10"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "breathlessness_score", "inhaler_adherence_and_technique",
            "steroid_and_antibiotic_course", "oxygen_saturation",
            "smoking_cessation", "pulmonary_rehab_referral",
        ],
        "red_flags": [
            "oxygen_saturation_below_88", "acute_severe_breathlessness",
            "cyanosis", "acute_confusion", "unable_to_complete_sentences",
        ],
    },

    "S01": {
        "label": "Stroke / Ischaemic",
        "category": "medical",
        "nice_ids": ["NG128", "CG162", "QS2", "NG185"],
        "monitoring_window_days": 90,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60, 90],
        "domains": [
            "neurological_deficit_monitoring", "antiplatelet_or_anticoagulant",
            "blood_pressure_control", "swallowing_and_nutrition",
            "mood_and_post_stroke_depression", "rehabilitation_attendance", "falls_risk",
        ],
        "red_flags": [
            "new_neurological_symptoms", "anticoagulant_non_adherence",
            "bp_severely_uncontrolled", "dysphagia_aspiration",
            "falls_with_injury", "stroke_recurrence_signs",
        ],
    },

    "H04": {
        "label": "Colectomy / Bowel Surgery",
        "category": "surgical",
        "nice_ids": ["NG147", "QS48", "NG89"],
        "monitoring_window_days": 60,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60],
        "domains": [
            "wound_healing", "bowel_function_recovery", "stoma_care",
            "pain_management", "diet_and_nutrition", "vte_prophylaxis",
        ],
        "red_flags": [
            "anastomotic_leak_signs", "bowel_obstruction",
            "wound_infection", "dvt_symptoms", "stoma_complications",
        ],
    },

    "H01": {
        "label": "Appendectomy",
        "category": "surgical",
        "nice_ids": ["NG61", "QS48"],
        "monitoring_window_days": 28,
        "call_days": [1, 3, 7, 14, 21, 28],
        "domains": [
            "wound_healing", "pain_management", "bowel_function",
            "infection_signs", "return_to_activity",
        ],
        "red_flags": [
            "wound_infection", "abscess", "bowel_obstruction", "fever_above_38_5",
        ],
    },

    "Z03_MH": {
        "label": "Acute Psychiatric Admission",
        "category": "mental_health",
        "nice_ids": ["CG136", "NG10", "QS80"],
        "monitoring_window_days": 90,
        "call_days": [1, 3, 7, 14, 21, 28, 42, 60, 90],
        "domains": [
            "medication_concordance", "mood_and_mental_state", "safety_and_safeguarding",
            "community_team_engagement", "crisis_plan_awareness",
            "social_support_and_daily_living", "substance_use_screen",
        ],
        "red_flags": [
            "suicidal_ideation_active", "medication_stopped_abruptly",
            "psychotic_relapse", "risk_to_others", "safeguarding_concern",
            "missing_from_contact",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# DOMAIN TRAJECTORIES
# Format per entry: (expected_score, upper_bound, label, nice_source)
# All scores on 0–4 scale.
# ═══════════════════════════════════════════════════════════════════════════

DOMAIN_TRAJECTORIES: dict[str, dict[str, dict[int, tuple]]] = {

    "W37": {
        "wound_healing": {
            1: (2, 3, "Wound intact, bruising expected", "NG226"),
            3: (2, 3, "Minor seepage acceptable", "NG226"),
            7: (1, 2, "Wound closing, sutures/clips in place", "NG226"),
            14: (1, 2, "Wound healing well", "NG226"),
            21: (1, 1, "Well healed", "NG226"),
            28: (0, 1, "Healed", "NG226"),
            42: (0, 1, "Healed", "NG226"),
            60: (0, 0, "Fully healed", "NG226"),
        },
        "pain_management": {
            1:  (2, 3, "Moderate pain expected", "NG226"),
            3:  (2, 3, "Pain reducing with analgesia", "NG226"),
            7:  (2, 2, "Mild-moderate pain at activity", "NG226"),
            14: (1, 2, "Mild pain reducing", "NG226"),
            21: (1, 2, "Mild pain", "NG226"),
            28: (1, 1, "Minimal pain", "NG226"),
            42: (0, 1, "Pain resolving", "NG226"),
            60: (0, 1, "Pain resolved or minimal", "NG226"),
        },
        "vte_prophylaxis": {
            1:  (1, 2, "LMWH/anticoagulant taken", "NG89"),
            3:  (1, 2, "Adherent", "NG89"),
            7:  (1, 2, "Adherent — 28-day course", "NG89"),
            14: (1, 2, "Adherent", "NG89"),
            21: (1, 2, "Adherent", "NG89"),
            28: (1, 1, "Course completed", "NG89"),
            42: (0, 1, "Course completed", "NG89"),
            60: (0, 0, "N/A", "NG89"),
        },
        "mobility_progress": {
            1:  (2, 3, "Walking with frame expected", "NG226"),
            3:  (2, 3, "Mobilising short distances", "NG226"),
            7:  (2, 2, "Walking with aid", "NG226"),
            14: (1, 2, "Improving mobility", "NG226"),
            21: (1, 2, "Walking further", "NG226"),
            28: (1, 1, "Good progress", "NG226"),
            42: (1, 1, "Near-normal mobility", "NG226"),
            60: (0, 1, "Normal mobility expected", "NG226"),
        },
        "infection_signs": {
            1:  (1, 2, "Normal post-op inflammation", "NG226"),
            3:  (1, 2, "Monitor for increasing redness/heat", "NG226"),
            7:  (1, 2, "Should be settling", "NG226"),
            14: (0, 1, "No signs expected", "NG226"),
            21: (0, 1, "No signs expected", "NG226"),
            28: (0, 1, "No signs expected", "NG226"),
            42: (0, 0, "Resolved", "NG226"),
            60: (0, 0, "Resolved", "NG226"),
        },
        "physiotherapy_compliance": {
            1:  (1, 2, "Exercises commenced", "NG226"),
            3:  (1, 2, "Daily exercises in progress", "NG226"),
            7:  (1, 2, "Exercise programme ongoing", "NG226"),
            14: (1, 1, "Attending/doing physio", "NG226"),
            21: (1, 1, "Regular physio", "NG226"),
            28: (1, 1, "Ongoing adherence", "NG226"),
            42: (1, 1, "Ongoing adherence", "NG226"),
            60: (0, 1, "Programme completing", "NG226"),
        },
    },

    "W40": {
        "wound_healing": {
            1:  (2, 3, "Wound intact, bruising and swelling expected", "NG226"),
            3:  (2, 3, "Minor seepage acceptable", "NG226"),
            7:  (1, 2, "Wound closing well", "NG226"),
            14: (1, 2, "Healing well", "NG226"),
            21: (1, 1, "Well healed", "NG226"),
            28: (0, 1, "Healed", "NG226"),
            42: (0, 1, "Healed", "NG226"),
            60: (0, 0, "Fully healed", "NG226"),
        },
        "pain_management": {
            1:  (2, 3, "Moderate pain expected post-op", "NG226"),
            3:  (2, 3, "Pain reducing with analgesia", "NG226"),
            7:  (2, 2, "Mild-moderate pain at activity", "NG226"),
            14: (1, 2, "Mild pain reducing", "NG226"),
            21: (1, 2, "Mild pain", "NG226"),
            28: (1, 1, "Minimal pain", "NG226"),
            42: (0, 1, "Pain resolving", "NG226"),
            60: (0, 1, "Pain resolved or minimal", "NG226"),
        },
        "vte_prophylaxis": {
            1:  (1, 2, "LMWH/anticoagulant commenced", "NG89"),
            3:  (1, 2, "Adherent", "NG89"),
            7:  (1, 2, "Adherent — 14-day course for knee", "NG89"),
            14: (1, 1, "Course completed at day 14 for TKR", "NG89"),
            21: (0, 1, "Completed", "NG89"),
            28: (0, 1, "Completed", "NG89"),
            42: (0, 0, "N/A", "NG89"),
            60: (0, 0, "N/A", "NG89"),
        },
        "mobility_progress": {
            1:  (2, 3, "Walking with frame expected", "NG226"),
            3:  (2, 3, "Mobilising short distances", "NG226"),
            7:  (2, 2, "Walking with crutches/stick", "NG226"),
            14: (1, 2, "Improving mobility", "NG226"),
            21: (1, 2, "Increasing range of movement", "NG226"),
            28: (1, 1, "Good progress, reduced aid", "NG226"),
            42: (1, 1, "Near-normal mobility", "NG226"),
            60: (0, 1, "Normal mobility expected", "NG226"),
        },
        "infection_signs": {
            1:  (1, 2, "Normal post-op inflammation", "NG226"),
            3:  (1, 2, "Monitor for increasing redness/heat/swelling", "NG226"),
            7:  (1, 2, "Should be settling", "NG226"),
            14: (0, 1, "No signs expected", "NG226"),
            21: (0, 1, "No signs expected", "NG226"),
            28: (0, 1, "No signs expected", "NG226"),
            42: (0, 0, "Resolved", "NG226"),
            60: (0, 0, "Resolved", "NG226"),
        },
        "physiotherapy_compliance": {
            1:  (1, 2, "Exercises commenced, CPM if prescribed", "NG226"),
            3:  (1, 2, "Daily exercises ongoing", "NG226"),
            7:  (1, 2, "Outpatient physio commenced", "NG226"),
            14: (1, 1, "Attending/doing physio regularly", "NG226"),
            21: (1, 1, "Regular physio", "NG226"),
            28: (1, 1, "Ongoing adherence", "NG226"),
            42: (1, 1, "Ongoing adherence", "NG226"),
            60: (0, 1, "Programme completing", "NG226"),
        },
    },

    "W43": {
        "wound_healing": {
            1:  (2, 3, "Wound intact, bruising expected", "NG226"),
            3:  (2, 3, "Minor seepage acceptable", "NG226"),
            7:  (1, 2, "Wound closing, sutures in place", "NG226"),
            14: (1, 2, "Healing well", "NG226"),
            21: (1, 1, "Well healed", "NG226"),
            28: (0, 1, "Healed", "NG226"),
            42: (0, 0, "Fully healed", "NG226"),
        },
        "pain_management": {
            1:  (2, 3, "Moderate pain expected", "NG226"),
            3:  (2, 3, "Pain reducing with analgesia", "NG226"),
            7:  (1, 2, "Mild-moderate pain at activity", "NG226"),
            14: (1, 2, "Mild pain reducing", "NG226"),
            21: (1, 1, "Minimal pain", "NG226"),
            28: (0, 1, "Resolving", "NG226"),
            42: (0, 1, "Resolved or minimal", "NG226"),
        },
        "vte_prophylaxis": {
            1:  (1, 2, "Anticoagulant commenced", "NG89"),
            3:  (1, 2, "Adherent", "NG89"),
            7:  (1, 2, "Adherent — 14-day course", "NG89"),
            14: (1, 1, "Course completed", "NG89"),
            21: (0, 1, "Completed", "NG89"),
            28: (0, 1, "Completed", "NG89"),
            42: (0, 0, "N/A", "NG89"),
        },
        "mobility_progress": {
            1:  (2, 3, "Walking with crutches expected", "NG226"),
            3:  (2, 2, "Short distance mobilisation", "NG226"),
            7:  (1, 2, "Increasing mobility", "NG226"),
            14: (1, 2, "Good progress", "NG226"),
            21: (1, 1, "Near-normal mobility", "NG226"),
            28: (0, 1, "Normal range expected", "NG226"),
            42: (0, 1, "Normal mobility", "NG226"),
        },
        "physiotherapy_compliance": {
            1:  (1, 2, "Exercises commenced", "NG226"),
            3:  (1, 2, "Daily exercises ongoing", "NG226"),
            7:  (1, 2, "Outpatient physio commenced", "NG226"),
            14: (1, 1, "Attending physio", "NG226"),
            21: (1, 1, "Regular physio", "NG226"),
            28: (1, 1, "Ongoing adherence", "NG226"),
            42: (0, 1, "Programme completing", "NG226"),
        },
    },

    "K40": {
        "chest_pain_monitoring": {
            1:  (2, 3, "Musculoskeletal/wound pain expected, not cardiac", "NG185"),
            3:  (1, 2, "Reducing — no angina expected", "NG185"),
            7:  (1, 2, "Should be settling", "NG185"),
            14: (1, 1, "Minimal chest pain expected", "CG172"),
            21: (0, 1, "No chest pain expected", "CG172"),
            28: (0, 1, "Resolved", "CG172"),
            42: (0, 1, "Resolved", "CG172"),
            60: (0, 0, "Resolved", "CG172"),
        },
        "antiplatelet_adherence": {
            1:  (1, 1, "Dual antiplatelet therapy commenced", "CG172"),
            3:  (1, 1, "Adherent — dual antiplatelet", "CG172"),
            7:  (1, 1, "Adherent — do not miss doses", "CG172"),
            14: (1, 1, "Adherent", "CG172"),
            21: (1, 1, "Adherent", "CG172"),
            28: (1, 1, "Adherent", "CG172"),
            42: (1, 1, "Adherent — lifelong aspirin", "CG172"),
            60: (1, 1, "Adherent", "CG172"),
        },
        "cardiac_rehab_attendance": {
            1:  (1, 2, "Referral made or pending", "NG185"),
            3:  (1, 2, "Awaiting programme start", "NG185"),
            7:  (1, 1, "Programme starting", "NG185"),
            14: (1, 1, "Attending", "NG185"),
            21: (1, 1, "Attending — phase 2", "NG185"),
            28: (1, 1, "Ongoing", "NG185"),
            42: (1, 1, "Ongoing", "NG185"),
            60: (0, 1, "Programme completing", "NG185"),
        },
        "mood_and_depression": {
            1:  (1, 2, "Low mood common post-MI — screen", "CG172"),
            3:  (1, 2, "Monitor for depression", "CG172"),
            7:  (1, 2, "Depression peak risk week 1-4", "CG172"),
            14: (1, 2, "PHQ-2 screen", "CG172"),
            21: (1, 1, "Improving mood expected", "CG172"),
            28: (1, 1, "Stabilising", "CG172"),
            42: (1, 1, "Improving", "CG172"),
            60: (0, 1, "Near-baseline", "CG172"),
        },
        "activity_progression": {
            1:  (2, 3, "Rest — light activity only", "NG185"),
            3:  (2, 2, "Short walks only", "NG185"),
            7:  (1, 2, "Gradual activity increase", "NG185"),
            14: (1, 2, "Walking 5-10 mins", "NG185"),
            21: (1, 1, "Walking regularly", "NG185"),
            28: (1, 1, "Increasing activity per rehab plan", "NG185"),
            42: (1, 1, "Good activity levels", "NG185"),
            60: (0, 1, "Near-normal activity", "NG185"),
        },
        "risk_factor_modification": {
            1:  (1, 2, "Smoking cessation initiated if applicable", "NG185"),
            3:  (1, 2, "Diet and lifestyle advice given", "NG185"),
            7:  (1, 1, "Engaging with lifestyle changes", "NG185"),
            14: (1, 1, "Adherent to lifestyle plan", "NG185"),
            21: (1, 1, "Ongoing adherence", "NG185"),
            28: (1, 1, "Ongoing", "NG185"),
            42: (1, 1, "Ongoing", "NG185"),
            60: (0, 1, "Established habits", "NG185"),
        },
    },

    "K60": {
        "breathlessness": {
            1:  (2, 3, "Breathlessness improving from admission — still present", "CG187"),
            3:  (2, 3, "Should be reducing", "CG187"),
            7:  (1, 2, "Mild breathlessness on exertion only", "CG187"),
            14: (1, 2, "Improving — able to walk around home", "CG187"),
            21: (1, 1, "Mild breathlessness on activity", "NG106"),
            28: (1, 1, "Manageable", "NG106"),
            42: (0, 1, "Near baseline", "NG106"),
            60: (0, 1, "Baseline level", "NG106"),
        },
        "oedema_monitoring": {
            1:  (2, 3, "Residual oedema expected at discharge", "CG187"),
            3:  (2, 3, "Resolving", "CG187"),
            7:  (1, 2, "Reducing oedema", "CG187"),
            14: (1, 2, "Minimal oedema", "CG187"),
            21: (1, 1, "Resolved or minimal", "NG106"),
            28: (0, 1, "Resolved", "NG106"),
            42: (0, 1, "Resolved", "NG106"),
            60: (0, 0, "Resolved", "NG106"),
        },
        "medication_adherence": {
            1:  (1, 1, "All HF medications taken", "CG187"),
            3:  (1, 1, "Adherent", "CG187"),
            7:  (1, 1, "Adherent — do not stop diuretics", "CG187"),
            14: (1, 1, "Adherent", "NG106"),
            21: (1, 1, "Adherent", "NG106"),
            28: (1, 1, "Adherent", "NG106"),
            42: (1, 1, "Adherent", "NG106"),
            60: (1, 1, "Adherent", "NG106"),
        },
        "weight_monitoring": {
            1:  (1, 2, "Daily weighing commenced", "CG187"),
            3:  (1, 2, "Weighing daily", "CG187"),
            7:  (1, 1, "Stable weight", "CG187"),
            14: (1, 1, "Stable", "NG106"),
            21: (1, 1, "Stable", "NG106"),
            28: (1, 1, "Stable", "NG106"),
            42: (1, 1, "Stable", "NG106"),
            60: (1, 1, "Stable", "NG106"),
        },
        "activity_tolerance": {
            1:  (2, 3, "Limited activity — rest at home", "CG187"),
            3:  (2, 3, "Light activity only", "CG187"),
            7:  (2, 2, "Short walks — increasing gradually", "CG187"),
            14: (1, 2, "Walking short distances", "NG106"),
            21: (1, 1, "Increasing activity with HF rehab", "NG106"),
            28: (1, 1, "Managed activity", "NG106"),
            42: (1, 1, "Good activity levels", "NG106"),
            60: (0, 1, "Near-baseline activity", "NG106"),
        },
        "mood_and_anxiety": {
            1:  (1, 2, "Anxiety/low mood common — screen", "CG187"),
            3:  (1, 2, "Monitor", "CG187"),
            7:  (1, 2, "Ongoing screen", "CG187"),
            14: (1, 2, "PHQ-2 screen", "NG106"),
            21: (1, 1, "Improving", "NG106"),
            28: (1, 1, "Stable", "NG106"),
            42: (0, 1, "Near-baseline", "NG106"),
            60: (0, 1, "Near-baseline", "NG106"),
        },
    },

    "R17": {
        "wound_healing": {
            1:  (2, 3, "Wound intact, bruising expected", "NG192"),
            3:  (2, 3, "Healing — clips/sutures in place", "NG192"),
            5:  (1, 2, "Healing well", "NG192"),
            7:  (1, 2, "Healing well", "NG192"),
            10: (1, 2, "Healing", "NG192"),
            14: (1, 1, "Well healed", "NG192"),
            21: (0, 1, "Healed", "NG192"),
            28: (0, 1, "Healed", "NG192"),
        },
        "pain_management": {
            1:  (2, 3, "Post-op pain expected", "NG192"),
            3:  (2, 3, "Reducing with analgesia", "NG192"),
            5:  (2, 2, "Mild-moderate pain", "NG192"),
            7:  (1, 2, "Mild pain", "NG192"),
            10: (1, 2, "Reducing", "NG192"),
            14: (1, 1, "Minimal pain", "NG192"),
            21: (0, 1, "Resolving", "NG192"),
            28: (0, 1, "Resolved", "NG192"),
        },
        "lochia_monitoring": {
            1:  (2, 3, "Red lochia expected — heavy initially", "NG192"),
            3:  (2, 2, "Reducing — pink/brown expected", "NG192"),
            5:  (1, 2, "Pink/brown, reducing", "NG192"),
            7:  (1, 2, "Light pink/brown", "NG192"),
            10: (1, 1, "Light spotting", "NG192"),
            14: (0, 1, "Resolving", "NG192"),
            21: (0, 1, "Minimal or resolved", "NG192"),
            28: (0, 0, "Resolved", "NG192"),
        },
        "vte_prophylaxis": {
            1:  (1, 2, "LMWH commenced", "NG89"),
            3:  (1, 2, "Adherent", "NG89"),
            5:  (1, 2, "Adherent", "NG89"),
            7:  (1, 2, "Adherent", "NG89"),
            10: (1, 1, "Course completing", "NG89"),
            14: (0, 1, "10-day course completed", "NG89"),
            21: (0, 1, "Completed", "NG89"),
            28: (0, 0, "N/A", "NG89"),
        },
        "postnatal_mood": {
            1:  (1, 2, "Baby blues days 3-5 expected", "NG192"),
            3:  (1, 2, "Monitor — baby blues peak", "NG192"),
            5:  (1, 2, "Baby blues should resolve", "NG194"),
            7:  (1, 2, "Mood should be improving", "NG194"),
            10: (1, 1, "Improving", "NG194"),
            14: (1, 1, "Screen for PND", "NG194"),
            21: (1, 1, "Ongoing screen", "NG194"),
            28: (0, 1, "Near-baseline", "NG194"),
        },
        "mobility": {
            1:  (2, 3, "Walking short distances — support needed", "NG192"),
            3:  (2, 2, "Mobilising with care", "NG192"),
            5:  (1, 2, "Increasing mobility", "NG192"),
            7:  (1, 2, "Walking normally", "NG192"),
            10: (1, 1, "Good mobility", "NG192"),
            14: (1, 1, "Normal mobility", "NG192"),
            21: (0, 1, "Full mobility", "NG192"),
            28: (0, 1, "Fully mobile", "NG192"),
        },
        "infant_feeding": {
            1:  (1, 2, "Feeding established or being established", "NG192"),
            3:  (1, 2, "Feeding progressing", "NG192"),
            5:  (1, 1, "Feeding well", "NG192"),
            7:  (1, 1, "Feeding well", "NG192"),
            10: (1, 1, "Established feeding", "NG192"),
            14: (0, 1, "Well established", "NG192"),
            21: (0, 1, "Well established", "NG192"),
            28: (0, 1, "Well established", "NG192"),
        },
    },

    "R18": {
        # Same as R17 but adds emotional_recovery domain
        "wound_healing": {
            1:  (2, 3, "Wound intact, bruising expected", "NG192"),
            3:  (2, 3, "Healing — clips/sutures in place", "NG192"),
            5:  (1, 2, "Healing well", "NG192"),
            7:  (1, 2, "Healing well", "NG192"),
            10: (1, 2, "Healing", "NG192"),
            14: (1, 1, "Well healed", "NG192"),
            21: (0, 1, "Healed", "NG192"),
            28: (0, 1, "Healed", "NG192"),
        },
        "pain_management": {
            1:  (2, 3, "Post-op pain expected", "NG192"),
            3:  (2, 3, "Reducing with analgesia", "NG192"),
            5:  (2, 2, "Mild-moderate pain", "NG192"),
            7:  (1, 2, "Mild pain", "NG192"),
            10: (1, 2, "Reducing", "NG192"),
            14: (1, 1, "Minimal pain", "NG192"),
            21: (0, 1, "Resolving", "NG192"),
            28: (0, 1, "Resolved", "NG192"),
        },
        "lochia_monitoring": {
            1:  (2, 3, "Red lochia expected — heavy initially", "NG192"),
            3:  (2, 2, "Reducing — pink/brown expected", "NG192"),
            5:  (1, 2, "Pink/brown, reducing", "NG192"),
            7:  (1, 2, "Light pink/brown", "NG192"),
            10: (1, 1, "Light spotting", "NG192"),
            14: (0, 1, "Resolving", "NG192"),
            21: (0, 1, "Minimal or resolved", "NG192"),
            28: (0, 0, "Resolved", "NG192"),
        },
        "vte_prophylaxis": {
            1:  (1, 2, "LMWH commenced", "NG89"),
            3:  (1, 2, "Adherent", "NG89"),
            5:  (1, 2, "Adherent", "NG89"),
            7:  (1, 2, "Adherent", "NG89"),
            10: (1, 1, "Course completing", "NG89"),
            14: (0, 1, "10-day course completed", "NG89"),
            21: (0, 1, "Completed", "NG89"),
            28: (0, 0, "N/A", "NG89"),
        },
        "postnatal_mood": {
            1:  (2, 3, "Emotional distress common after emergency CS", "NG194"),
            3:  (2, 3, "Monitor closely — higher PND risk", "NG194"),
            5:  (1, 2, "Baby blues resolving", "NG194"),
            7:  (1, 2, "Mood should be improving", "NG194"),
            10: (1, 2, "Improving", "NG194"),
            14: (1, 1, "Screen for PND — Edinburgh scale", "NG194"),
            21: (1, 1, "Ongoing screen", "NG194"),
            28: (0, 1, "Near-baseline", "NG194"),
        },
        "mobility": {
            1:  (2, 3, "Walking short distances — support needed", "NG192"),
            3:  (2, 2, "Mobilising with care", "NG192"),
            5:  (1, 2, "Increasing mobility", "NG192"),
            7:  (1, 2, "Walking normally", "NG192"),
            10: (1, 1, "Good mobility", "NG192"),
            14: (1, 1, "Normal mobility", "NG192"),
            21: (0, 1, "Full mobility", "NG192"),
            28: (0, 1, "Fully mobile", "NG192"),
        },
        "infant_feeding": {
            1:  (1, 2, "Feeding being established — may need extra support", "NG192"),
            3:  (1, 2, "Feeding progressing", "NG192"),
            5:  (1, 1, "Feeding well", "NG192"),
            7:  (1, 1, "Feeding well", "NG192"),
            10: (1, 1, "Established feeding", "NG192"),
            14: (0, 1, "Well established", "NG192"),
            21: (0, 1, "Well established", "NG192"),
            28: (0, 1, "Well established", "NG192"),
        },
        "emotional_recovery": {
            1:  (2, 3, "Shock/distress after emergency delivery expected", "NG192"),
            3:  (2, 3, "Open emotional check — process birth experience", "NG192"),
            5:  (2, 2, "Allow time to process — listen actively", "NG194"),
            7:  (1, 2, "Slowly processing birth experience", "NG194"),
            10: (1, 2, "Improving emotional state", "NG194"),
            14: (1, 1, "Screen for PTSD symptoms", "NG194"),
            21: (1, 1, "Ongoing support", "NG194"),
            28: (0, 1, "Near-baseline", "NG194"),
        },
    },

    "J44": {
        "breathlessness_score": {
            1:  (2, 3, "Breathlessness reducing from admission level", "NG115"),
            3:  (2, 3, "Improving", "NG115"),
            7:  (1, 2, "Mild breathlessness on exertion", "NG115"),
            14: (1, 2, "Near baseline for this patient", "NG115"),
            21: (1, 1, "At baseline", "NG115"),
            28: (1, 1, "Baseline", "NG115"),
            42: (0, 1, "Stable", "NG115"),
            60: (0, 1, "Stable", "NG115"),
        },
        "inhaler_adherence_and_technique": {
            1:  (1, 2, "Inhalers prescribed — adherent", "NG115"),
            3:  (1, 2, "Adherent and using correct technique", "NG115"),
            7:  (1, 1, "Adherent", "NG115"),
            14: (1, 1, "Adherent", "NG115"),
            21: (1, 1, "Adherent", "NG115"),
            28: (1, 1, "Adherent", "NG115"),
            42: (1, 1, "Adherent", "NG115"),
            60: (1, 1, "Adherent", "NG115"),
        },
        "steroid_and_antibiotic_course": {
            1:  (1, 1, "Completing prescribed course", "NG115"),
            3:  (1, 1, "Course ongoing", "NG115"),
            7:  (0, 1, "Course completing or completed", "NG115"),
            14: (0, 0, "Course completed", "NG115"),
            21: (0, 0, "Completed", "NG115"),
            28: (0, 0, "Completed", "NG115"),
            42: (0, 0, "N/A", "NG115"),
            60: (0, 0, "N/A", "NG115"),
        },
        "oxygen_saturation": {
            1:  (1, 2, "SpO2 ≥92% on air at discharge", "NG115"),
            3:  (1, 2, "SpO2 ≥92% target", "NG115"),
            7:  (1, 1, "SpO2 ≥92% stable", "NG115"),
            14: (1, 1, "Stable", "NG115"),
            21: (1, 1, "Stable", "NG115"),
            28: (1, 1, "Stable", "NG115"),
            42: (0, 1, "At baseline", "NG115"),
            60: (0, 1, "At baseline", "NG115"),
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# DOMAIN NAME NORMALISER
# Maps human-readable / alias names → canonical snake_case domain keys
# ═══════════════════════════════════════════════════════════════════════════

_DOMAIN_ALIASES: dict[str, str] = {
    # pain
    "pain": "pain_management",
    "pain score": "pain_management",
    "pain level": "pain_management",
    "pain management": "pain_management",
    "chest pain": "chest_pain_monitoring",
    "chest pain monitoring": "chest_pain_monitoring",
    # wound
    "wound": "wound_healing",
    "wound healing": "wound_healing",
    "wound care": "wound_healing",
    "sternal wound": "sternal_wound_healing",
    "leg wound": "leg_wound_healing",
    # mobility
    "mobility": "mobility_progress",
    "mobility progress": "mobility_progress",
    "mobility and rehabilitation": "mobility_and_rehabilitation",
    "walking": "mobility_progress",
    "fatigue": "mobility_and_fatigue",
    "mobility and fatigue": "mobility_and_fatigue",
    # mood
    "mood": "mood_and_depression",
    "depression": "mood_and_depression",
    "mood and depression": "mood_and_depression",
    "mood and anxiety": "mood_and_anxiety",
    "anxiety": "mood_and_anxiety",
    "postnatal mood": "postnatal_mood",
    "emotional recovery": "emotional_recovery",
    # infection
    "infection": "infection_signs",
    "infection signs": "infection_signs",
    # physio
    "physio": "physiotherapy_compliance",
    "physiotherapy": "physiotherapy_compliance",
    "physiotherapy compliance": "physiotherapy_compliance",
    "exercises": "physiotherapy_compliance",
    # vte
    "vte": "vte_prophylaxis",
    "vte prophylaxis": "vte_prophylaxis",
    "anticoagulant": "vte_prophylaxis",
    "anticoagulation": "anticoagulation_adherence",
    "anticoagulation adherence": "anticoagulation_adherence",
    "antiplatelet": "antiplatelet_adherence",
    "antiplatelet adherence": "antiplatelet_adherence",
    # meds
    "medication": "medication_adherence",
    "medication adherence": "medication_adherence",
    "medications": "medication_adherence",
    "medication concordance": "medication_concordance",
    # breathlessness
    "breathlessness": "breathlessness",
    "breathing": "breathlessness",
    "breathlessness score": "breathlessness_score",
    "oxygen": "oxygen_saturation",
    "oxygen saturation": "oxygen_saturation",
    # cardiac rehab
    "cardiac rehab": "cardiac_rehab_attendance",
    "cardiac rehabilitation": "cardiac_rehab_attendance",
    "cardiac rehab attendance": "cardiac_rehab_attendance",
    # activity
    "activity": "activity_tolerance",
    "activity tolerance": "activity_tolerance",
    "activity progression": "activity_progression",
    "return to activity": "return_to_activity",
    # obstetric
    "lochia": "lochia_monitoring",
    "lochia monitoring": "lochia_monitoring",
    "bleeding": "lochia_monitoring",
    "infant feeding": "infant_feeding",
    "feeding": "infant_feeding",
    "breastfeeding": "infant_feeding",
    # heart failure
    "oedema": "oedema_monitoring",
    "oedema monitoring": "oedema_monitoring",
    "swelling": "oedema_monitoring",
    "weight": "weight_monitoring",
    "weight monitoring": "weight_monitoring",
    # bowel
    "bowel": "bowel_function_recovery",
    "bowel function": "bowel_function_recovery",
    "bowel function recovery": "bowel_function_recovery",
    "stoma": "stoma_care",
    "stoma care": "stoma_care",
    # cognition
    "delirium": "delirium_cognitive_screen",
    "cognitive": "delirium_cognitive_screen",
    "delirium cognitive screen": "delirium_cognitive_screen",
    # falls
    "falls": "falls_risk",
    "falls risk": "falls_risk",
    # diet
    "diet": "diet_and_nutrition",
    "nutrition": "diet_and_nutrition",
    "appetite": "diet_and_nutrition",
    # risk factors
    "risk factors": "risk_factor_modification",
    "lifestyle": "risk_factor_modification",
    "smoking": "risk_factor_modification",
    # neurological
    "neurological": "neurological_deficit_monitoring",
    "neuro": "neurological_deficit_monitoring",
    # bp
    "blood pressure": "blood_pressure_control",
    "bp": "blood_pressure_control",
    # rehab / stroke
    "rehabilitation": "rehabilitation_attendance",
    # safety
    "safety": "safety_and_safeguarding",
    "safeguarding": "safety_and_safeguarding",
    # mental health
    "crisis plan": "crisis_plan_awareness",
    "medication concordance": "medication_concordance",
    "social support": "social_support_and_daily_living",
    "substance use": "substance_use_screen",
    "mental state": "mood_and_mental_state",
}


def _normalise_domain(name: str) -> str:
    """Normalise a human-readable domain name to its canonical snake_case key."""
    return _DOMAIN_ALIASES.get(name.lower().strip(), name.lower().strip().replace(" ", "_"))


def _closest_day(day_map: dict[int, tuple], day: int) -> int:
    """Return the closest available day key for a given day number."""
    return min(day_map.keys(), key=lambda d: abs(d - day))


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def get_playbook(pathway: str) -> dict | None:
    """
    Return the full playbook metadata for a pathway code.

    Returns None if the pathway is not recognised.
    """
    return PLAYBOOKS.get(pathway)


def get_domain_trajectory(pathway: str, domain: str, day: int) -> dict | None:
    """
    Return NICE trajectory data for a domain at a given day post-discharge.

    Returns a dict:
      {
        "nice_range":  [0, upper_bound],   # acceptable score range 0–4
        "expected":    int,                # ideal expected score at this day
        "upper_bound": int,                # maximum acceptable score
        "direction":   "improving" | "stable" | "worsening",
        "red_flag":    bool,               # True if domain links to a pathway red flag
        "label":       str,                # NICE expected state description
        "nice_source": str,                # e.g. "NG226"
        "day_used":    int,                # closest benchmark day
      }
    Returns None if pathway or domain not found.
    """
    domain = _normalise_domain(domain)
    traj = DOMAIN_TRAJECTORIES.get(pathway, {}).get(domain)
    if not traj:
        return None

    closest = _closest_day(traj, day)
    exp, upper, label, nice_src = traj[closest]

    # Infer direction from trajectory
    sorted_days = sorted(traj.keys())
    idx = sorted_days.index(closest)
    next_idx = min(idx + 1, len(sorted_days) - 1)
    next_exp = traj[sorted_days[next_idx]][0]

    if next_exp < exp:
        direction = "improving"
    elif next_exp > exp:
        direction = "worsening"
    else:
        direction = "stable"

    # Check if domain is linked to a pathway red flag
    pw = PLAYBOOKS.get(pathway, {})
    red_flags = pw.get("red_flags", [])
    domain_rf = any(domain in rf or rf in domain for rf in red_flags)

    return {
        "nice_range":  [0, upper],
        "expected":    exp,
        "upper_bound": upper,
        "direction":   direction,
        "red_flag":    domain_rf,
        "label":       label,
        "nice_source": nice_src,
        "day_used":    closest,
    }


def score_patient_domain(pathway: str, domain: str, day: int, actual_score: float) -> str:
    """
    Score a patient's domain against NICE benchmarks.

    actual_score must be on a 0–4 scale.

    Returns one of:
      "resolved"  — score is 0
      "expected"  — score ≤ NICE expected at this day
      "monitor"   — score above expected but within acceptable upper bound
      "expedite"  — score above upper bound (needs clinical review today)
      "escalate"  — score is 4 (emergency)
    """
    if actual_score == 4:
        return "escalate"
    if actual_score == 0:
        return "resolved"

    traj_info = get_domain_trajectory(pathway, domain, day)
    if not traj_info:
        # Unknown domain — apply simple threshold
        if actual_score >= 3:
            return "expedite"
        if actual_score >= 2:
            return "monitor"
        return "expected"

    exp = traj_info["expected"]
    upper = traj_info["upper_bound"]

    if actual_score <= exp:
        return "expected"
    if actual_score <= upper:
        return "monitor"
    return "expedite"


# ── Priority ordering ──────────────────────────────────────────────────────

_STATUS_RANK = {
    "escalate": 0,
    "expedite": 1,
    "monitor":  2,
    "expected": 3,
    "resolved": 4,
    None:       5,
}


def _domain_priority_key(pathway: str, domain: str, day: int, score: float | None) -> tuple:
    """Return (status_rank, -score) for sorting domains highest-concern first."""
    if score is None:
        return (5, 0)
    status = score_patient_domain(pathway, domain, day, score)
    return (_STATUS_RANK.get(status, 5), -score)


# ═══════════════════════════════════════════════════════════════════════════
# CALL PROMPT BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_call_prompt(
    patient_name: str,
    age: int | None,
    pathway: str,
    condition: str,
    day_post_discharge: int,
    scores_dict: dict[str, dict[int, float]],
) -> str:
    """
    Build a fully personalised system prompt for the Sizor voice agent.

    Parameters
    ----------
    patient_name        : str   — e.g. "Margaret Thompson"
    age                 : int   — patient age in years (None if unknown)
    pathway             : str   — OPCS code e.g. "W40", "K60", "R18"
    condition           : str   — human-readable condition e.g. "Total knee replacement"
    day_post_discharge  : int   — current call day
    scores_dict         : dict  — per-domain score history
                                  {domain_name: {day: score, ...}, ...}
                                  Scores must be on the 0–4 scale.
                                  If any score > 4, all are assumed 0–10 and
                                  normalised to 0–4 automatically.

    Returns
    -------
    str — complete system prompt ready to inject into the LLM
    """
    pw = PLAYBOOKS.get(pathway)
    if not pw:
        # Graceful fallback for unknown pathway
        return _generic_prompt(patient_name, age, condition, day_post_discharge)

    pathway_label = pw["label"]
    domains: list[str] = pw["domains"]
    red_flags: list[str] = pw["red_flags"]
    nice_ids: list[str] = pw["nice_ids"]

    # ── Normalise scores_dict keys to canonical domain names ─────────────
    normalised_scores: dict[str, dict[int, float]] = {}
    for raw_key, day_map in scores_dict.items():
        canon = _normalise_domain(raw_key)
        normalised_scores[canon] = day_map

    # ── Auto-detect scale: if any score > 4 treat as 0-10, normalise ─────
    all_values = [v for dm in normalised_scores.values() for v in dm.values()]
    if any(v > 4 for v in all_values if v is not None):
        normalised_scores = {
            domain: {day: round(s * 0.4, 1) for day, s in dm.items()}
            for domain, dm in normalised_scores.items()
        }

    # ── Get latest score per domain ───────────────────────────────────────
    def _latest(domain: str) -> float | None:
        dm = normalised_scores.get(domain, {})
        if not dm:
            return None
        return dm[max(dm.keys())]

    def _latest_day(domain: str) -> int | None:
        dm = normalised_scores.get(domain, {})
        if not dm:
            return None
        return max(dm.keys())

    # ── Sort domains by priority (flagged first) ───────────────────────────
    ordered_domains = sorted(
        domains,
        key=lambda d: _domain_priority_key(pathway, d, day_post_discharge, _latest(d)),
    )

    # ── Build priority callout (domains above NICE upper bound) ───────────
    priority_domains = [
        d for d in ordered_domains
        if _latest(d) is not None
        and score_patient_domain(pathway, d, day_post_discharge, _latest(d))
        in ("expedite", "escalate")
    ]

    # ── Build prompt sections ──────────────────────────────────────────────
    age_str = f", {age} years old" if age else ""
    nice_str = " / ".join(nice_ids)

    # Header
    lines = [
        f"You are Sarah, an NHS automated post-discharge check-in agent calling on behalf of the NHS.",
        f"You are professional, calm, empathetic, and speak in clear British English.",
        "",
        "PATIENT DETAILS:",
        f"  - Patient name       : {patient_name}{age_str}",
        f"  - Condition          : {condition}",
        f"  - Pathway            : {pathway_label} ({pathway})",
        f"  - Day post-discharge : Day {day_post_discharge}",
        f"  - NICE guidelines    : {nice_str}",
        "",
        "═" * 64,
        "CALL SCRIPT — follow each phase in order",
        "═" * 64,
        "",
        "PHASE 1 — IDENTITY VERIFICATION (MANDATORY)",
        "─" * 44,
        f'1. Greet the patient: "Good [morning/afternoon], this is Sarah calling from the NHS post-discharge care line. Could I please speak with {patient_name}?"',
        "2. Ask for their full name.",
        "   - Accept any response that includes their first name OR last name (not case-sensitive).",
        '3. Ask them to confirm their NHS number: "Could you please tell me your NHS number?"',
        "   - Do NOT read the NHS number aloud.",
        "   - Be tolerant of pauses, grouping, or slight speech recognition noise.",
        '   - If it matches, say: "Thank you, I\'ve been able to verify your identity."',
        '   - If it does NOT match, say: "No problem at all — not to worry. Could I ask for your date of birth instead?"',
        "4. DATE OF BIRTH FALLBACK: verify using date of birth if NHS number failed.",
        "   - If DOB matches, confirm identity. If DOB also fails, continue the call anyway.",
        "   - Do NOT end the call just because verification failed.",
        "",
        "PHASE 2 — CONSENT & RECORDING NOTICE",
        "─" * 38,
        '"This call may be recorded for quality and clinical purposes. Do you consent to continue?"',
        "If they decline, thank them and end the call politely.",
        "",
    ]

    # Clinical assessment header
    lines += [
        "═" * 64,
        f"CLINICAL CALL SCRIPT — {pathway_label.upper()} — DAY {day_post_discharge} POST-DISCHARGE",
        "═" * 64,
        "",
        f"IMPORTANT: The patient is on Day {day_post_discharge} post-discharge.",
        f"Always say 'Day {day_post_discharge}' when referencing time.",
        "Never say 'a few days ago', '2 weeks', or any other vague timeframe.",
        "",
        "SCORING: All domains use a 0–4 scale (0 = no problem, 4 = emergency).",
        "RULE: Score 3 on any domain → say escalation phrase and flag for clinical review today.",
        "RULE: Score 4 on any domain → say escalation phrase, gently signpost 999/A&E, continue call.",
        "",
    ]

    # Red flags block
    if red_flags:
        lines.append("PATHWAY RED FLAGS — any of the following ALWAYS triggers score 4 response:")
        for rf in red_flags:
            lines.append(f"  • {rf.replace('_', ' ')}")
        lines.append("")

    # Priority callout
    if priority_domains:
        lines.append("⚠  PRIORITY DOMAINS — scored ABOVE NICE expected range on previous call(s):")
        for d in priority_domains:
            score = _latest(d)
            last_day = _latest_day(d)
            traj = get_domain_trajectory(pathway, d, last_day or day_post_discharge)
            upper = traj["upper_bound"] if traj else "?"
            label = traj["label"] if traj else ""
            lines.append(
                f"   • {d.replace('_', ' ').title()}: scored {score}/4 on Day {last_day} "
                f"(NICE upper bound: {upper}/4 — \"{label}\")"
            )
        lines.append("   → Ask these domains first. Probe deeply if the score has not improved.")
        lines.append("   → Open with a specific reference: \"Last time you mentioned [issue] — how has that been since?\"")
        lines.append("")

    # Per-domain questions
    lines.append("PHASE 3 — CLINICAL ASSESSMENT")
    lines.append("─" * 64)

    for i, domain in enumerate(ordered_domains, 1):
        domain_label = domain.replace("_", " ").title()
        score = _latest(domain)
        last_day = _latest_day(domain)
        status = score_patient_domain(pathway, domain, day_post_discharge, score) if score is not None else None
        traj = get_domain_trajectory(pathway, domain, day_post_discharge)

        # Domain header with status flag
        status_flag = ""
        if status == "escalate":
            status_flag = "  🔴 ESCALATE"
        elif status == "expedite":
            status_flag = "  ⚠ EXPEDITE"
        elif status == "monitor":
            status_flag = "  🟡 MONITOR"
        elif status == "expected":
            status_flag = "  ✓ on track"

        lines.append(f"\nDomain {i}: {domain_label}{status_flag}")

        # Inline NICE benchmark + previous score context
        if traj:
            exp = traj["expected"]
            upper = traj["upper_bound"]
            nice_label = traj["label"]
            nice_src = traj["nice_source"]
            lines.append(
                f"  NICE ({nice_src}) — Day {day_post_discharge}: expected ≤{upper}/4 — \"{nice_label}\""
            )

        if score is not None and last_day is not None:
            trend_note = ""
            if status in ("expedite", "escalate"):
                trend_note = " — ABOVE EXPECTED, probe specifically"
            elif status == "monitor":
                trend_note = " — above expected, ask if improving"
            elif status in ("expected", "resolved"):
                trend_note = " — on track"
            lines.append(f"  Previous score (Day {last_day}): {score}/4{trend_note}")

            # Score trajectory (last 3 readings)
            dm = normalised_scores.get(domain, {})
            if len(dm) > 1:
                hist = sorted(dm.items())[-3:]
                hist_str = " → ".join(f"Day {d}: {s}/4" for d, s in hist)
                lines.append(f"  Score history: {hist_str}")

        # Question and scoring guide
        lines.append(f'  Question: Ask about {domain_label.lower()} — probe on 0–4 scale.')
        lines.append("  Scoring guide:")
        lines.append("    0/4 — No problem / resolved")
        lines.append("    1/4 — Mild, within expected range for this stage of recovery")
        lines.append("    2/4 — Above expected, monitor — say: \"I'll make sure your care team keeps an eye on that.\"")
        lines.append('    3/4 — Significant concern — say: "I\'m going to make sure your care team contacts you today."')
        lines.append('    4/4 — Emergency — say: "Please call 999 or go to A&E — I am alerting your care team now."')

    lines += [
        "",
        "═" * 64,
        "PHASE 4 — MEDICATION & ADHERENCE",
        "─" * 64,
        '"Are you taking all your prescribed medications exactly as directed?"',
        "  If no → probe: which medications and why? Flag as AMBER or RED depending on criticality.",
        "",
        "PHASE 5 — MENTAL HEALTH SCREEN (PHQ-2)",
        "─" * 64,
        '  Q: "Over the past two weeks, have you been feeling down, depressed, or hopeless?"',
        '  Q: "Over the past two weeks, have you had little interest or pleasure in doing things you usually enjoy?"',
        "",
        "PHASE 6 — OPEN-ENDED CHECK",
        "─" * 64,
        '  "Is there anything else you\'d like to mention, or any concerns about your recovery we haven\'t covered?"',
        "",
        "PHASE 7 — CLOSE",
        "─" * 64,
        "  - Confirm next appointment or advise patient to contact GP surgery to schedule one.",
        '  - "Thank you for speaking with me today. Please call NHS 111 if you have any urgent concerns. Take care. Goodbye."',
        "",
        "═" * 64,
        "URGENCY ESCALATION RULES (apply at all times, across all phases)",
        "═" * 64,
        "",
        "RED — If the patient reports any of the following, acknowledge warmly, gently signpost",
        "999/NHS 111, then CONTINUE the call. Do NOT end the call. Do NOT alarm them.",
        "Do NOT say 'that sounds concerning' or 'that's worrying'.",
        "  • Chest pain or tightness at rest",
        "  • Severe difficulty breathing",
        "  • Pain score 8+/10 (unbearable)",
        "  • Active heavy bleeding",
        "  • Thoughts of self-harm or suicide",
        "  • Any pathway red flag listed above",
        "",
        "HOW TO RESPOND (warm, not alarming):",
        '  Acknowledge: "Oh I\'m really sorry to hear that, that must be really hard for you."',
        '  Then gently: "I just want to make sure you know — if things feel like they\'re getting worse',
        "  or you're worried at any point, please don't hesitate to ring NHS 111 or 999, they're always there to help.\"",
        "  Then continue the remaining check-in questions as normal.",
        "  The call will be flagged automatically for clinical review.",
        "",
        "AMBER — Continue the call but note concern. Do NOT use alarming language.",
        "  • Fever above 38°C",
        "  • Pain score 5–7/10",
        "  • Not taking critical medications",
        "  • Significant unexplained swelling or discharge",
        '  Say: "I\'m sorry to hear that — I\'ll make sure your care team takes a look at that for you today."',
        "",
        "═" * 64,
        "GENERAL GUIDANCE",
        "═" * 64,
        "- Keep responses concise — this is a phone call, not a chat.",
        "- Ask one question at a time. Wait for the answer before continuing.",
        "- Never diagnose or offer medical advice — signpost only (NHS 111, GP, 999).",
        "- If the patient is distressed, acknowledge their feelings before moving on.",
        "- Maintain GDPR compliance: do not repeat NHS numbers aloud more than once.",
        "- Reference previous scores naturally, e.g. \"Last time you mentioned your pain was quite high — how is it today?\"",
        "- Do not read out benchmark numbers or clinical jargon to the patient.",
    ]

    return "\n".join(lines)


def _generic_prompt(
    patient_name: str,
    age: int | None,
    condition: str,
    day_post_discharge: int,
) -> str:
    """Fallback prompt when pathway is not in PLAYBOOKS."""
    age_str = f", {age} years old" if age else ""
    phase = "early" if day_post_discharge <= 3 else ("mid" if day_post_discharge <= 14 else "late")
    return f"""You are Sarah, an NHS automated post-discharge check-in agent.
You are professional, calm, empathetic, and speak in clear British English.

PATIENT DETAILS:
  - Patient name       : {patient_name}{age_str}
  - Condition          : {condition}
  - Day post-discharge : Day {day_post_discharge} ({phase} recovery phase)

Follow the standard NHS post-discharge check-in script.
Ask about pain, mobility, wound healing, medications, mood, and appetite.
Use a 0–10 scale for pain and a general wellbeing scale for other domains.
Escalate to 999/NHS 111 for red flag symptoms. Do not end the call on verification failure.
"""

// frontend/src/data/pathwayMap.js
// Auto-generated from clinical/pathway_map.py
// Do not edit manually — run scripts/export_pathway_map.py to regenerate

export const OPCS_TO_NICE_MAP = {

  // ── SURGICAL ─────────────────────────────────────────────

  "W37": {
    label: "Total hip replacement",
    category: "Surgical",
    nice_ids: ["NG226", "TA455", "QS48", "QS89", "NG89"],
    pathway_slug: "hip-replacement",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "wound_healing", "pain_management", "vte_prophylaxis",
      "mobility_progress", "infection_signs", "physiotherapy_compliance"
    ],
    red_flags: [
      "dvt_signs", "pe_symptoms", "wound_infection",
      "fever_above_38", "severe_pain", "inability_to_weight_bear"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "W38": {
    label: "Hip fracture / hemiarthroplasty",
    category: "Surgical",
    nice_ids: ["NG124", "NG226", "QS16", "QS89", "NG89"],
    pathway_slug: "hip-fracture",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "wound_healing", "pain_management", "delirium_cognitive_screen",
      "falls_risk", "vte_prophylaxis", "mobility_and_rehabilitation"
    ],
    red_flags: [
      "acute_confusion", "dvt_signs", "wound_infection",
      "falls", "fever_above_38"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "W40": {
    label: "Total knee replacement",
    category: "Surgical",
    nice_ids: ["NG226", "TA304", "QS48", "QS89", "NG89"],
    pathway_slug: "knee-replacement",
    monitoring_window_days: 30,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "wound_healing", "pain_management", "vte_prophylaxis",
      "swelling_monitoring", "infection_signs",
      "physiotherapy_compliance", "mobility_progress"
    ],
    red_flags: [
      "dvt_signs", "pe_symptoms", "wound_dehiscence_or_infection",
      "fever_above_38", "severe_uncontrolled_pain",
      "inability_to_weight_bear"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "W43": {
    label: "Unicompartmental knee replacement",
    category: "Surgical",
    nice_ids: ["NG226", "QS48", "QS89"],
    pathway_slug: "knee-replacement",
    monitoring_window_days: 30,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "wound_inspection", "pain_level", "knee_flexion_extension",
      "vte_prophylaxis", "physiotherapy", "return_to_light_activity"
    ],
    red_flags: [
      "dvt_or_pe_symptoms", "wound_infection",
      "acute_locking_or_giving_way", "fever_within_7_days"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "K40_CABG": {
    label: "Coronary artery bypass graft (CABG)",
    category: "Surgical",
    nice_ids: ["NG185", "CG172", "QS99", "NG238"],
    pathway_slug: "cabg",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "sternal_wound_healing", "leg_wound_healing",
      "chest_pain_recurrence", "antiplatelet_adherence",
      "cardiac_rehab_attendance", "mood_and_depression",
      "mobility_and_fatigue"
    ],
    red_flags: [
      "recurrent_chest_pain", "sternal_wound_infection",
      "sudden_breathlessness", "antiplatelet_non_adherence",
      "depression_signs", "fever_above_38"
    ],
    auto_risk_flags: [],
  },

  "H04": {
    label: "Colectomy / bowel surgery",
    category: "Surgical",
    nice_ids: ["NG147", "QS48", "NG89"],
    pathway_slug: "colorectal-surgery",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "wound_healing", "bowel_function_recovery", "stoma_care",
      "pain_management", "diet_and_nutrition", "vte_prophylaxis"
    ],
    red_flags: [
      "wound_dehiscence", "anastomotic_leak_signs",
      "dvt_pe_symptoms", "fever_above_38", "no_bowel_movement_by_day_5"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "H01": {
    label: "Appendectomy",
    category: "Surgical",
    nice_ids: ["NG61", "QS48"],
    pathway_slug: "appendectomy",
    monitoring_window_days: 28,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "wound_healing", "pain_management",
      "bowel_function", "infection_signs", "return_to_activity"
    ],
    red_flags: [
      "wound_infection", "fever_above_38",
      "worsening_abdominal_pain", "no_bowel_movement_by_day_4"
    ],
    auto_risk_flags: [],
  },

  "J18_CHOLE": {
    label: "Cholecystectomy (gallbladder removal)",
    category: "Surgical",
    nice_ids: ["NG188", "QS48"],
    pathway_slug: "cholecystectomy",
    monitoring_window_days: 28,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "wound_healing", "pain_management",
      "diet_and_digestion", "jaundice_monitoring"
    ],
    red_flags: [
      "jaundice", "severe_abdominal_pain",
      "wound_infection", "fever_above_38"
    ],
    auto_risk_flags: [],
  },

  "Q07": {
    label: "Hysterectomy",
    category: "Surgical",
    nice_ids: ["NG121", "NG192", "QS48", "NG89"],
    pathway_slug: "hysterectomy",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "wound_healing", "vaginal_bleeding", "urinary_function",
      "vte_prophylaxis", "pain_management", "menopausal_symptoms"
    ],
    red_flags: [
      "heavy_vaginal_bleeding", "wound_infection",
      "dvt_pe_symptoms", "urinary_retention", "fever_above_38"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "M61": {
    label: "Radical prostatectomy",
    category: "Surgical",
    nice_ids: ["NG131", "QS48", "QS89"],
    pathway_slug: "prostatectomy",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "wound_healing", "urinary_continence", "catheter_care",
      "pain_management", "vte_prophylaxis"
    ],
    red_flags: [
      "urinary_retention", "wound_infection",
      "dvt_pe_symptoms", "fever_above_38", "haematuria"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "R17": {
    label: "Elective caesarean section",
    category: "Surgical",
    nice_ids: ["NG192", "QS32", "NG194", "NG89"],
    pathway_slug: "caesarean-birth",
    monitoring_window_days: 28,
    call_days: [1, 3, 5, 7, 10, 14, 21, 28],
    monitoring_domains: [
      "wound_healing_pfannenstiel", "lochia_pattern",
      "pain_management", "lmwh_adherence", "breastfeeding_support",
      "urinary_function", "mobility_progress",
      "postnatal_depression_screen", "infant_feeding_and_weight"
    ],
    red_flags: [
      "heavy_bleeding_or_clots", "wound_infection_or_dehiscence",
      "dvt_pe_symptoms", "urinary_retention",
      "hypertension_or_preeclampsia_signs",
      "postnatal_depression_signs", "infant_feeding_concerns"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "R18": {
    label: "Emergency caesarean section",
    category: "Surgical",
    nice_ids: ["NG192", "NG194", "QS32"],
    pathway_slug: "caesarean-birth",
    monitoring_window_days: 28,
    call_days: [1, 3, 5, 7, 10, 14, 21, 28],
    monitoring_domains: [
      "wound_healing_pfannenstiel", "lochia_pattern",
      "pain_management", "lmwh_adherence", "breastfeeding_support",
      "urinary_function", "emotional_processing_of_birth",
      "ptsd_screening", "postnatal_depression_screen",
      "neonatal_outcome_awareness"
    ],
    red_flags: [
      "heavy_bleeding_or_clots", "wound_infection_or_dehiscence",
      "dvt_pe_symptoms", "urinary_retention",
      "hypertension_or_preeclampsia_signs",
      "postnatal_depression_signs",
      "flashbacks_or_psychological_distress"
    ],
    auto_risk_flags: ["high_vte_risk", "emergency_procedure"],
  },

  // ── MEDICAL ──────────────────────────────────────────────

  "K60": {
    label: "Acute heart failure",
    category: "Medical",
    nice_ids: ["CG187", "NG106", "QS9"],
    pathway_slug: "acute-heart-failure",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "daily_weight", "breathlessness_nyha", "ankle_swelling",
      "diuretic_adherence", "fluid_restriction", "renal_function",
      "blood_pressure", "cardiac_rehab_referral"
    ],
    red_flags: [
      "weight_gain_2kg_3days", "sudden_breathlessness",
      "worsening_oedema", "dizziness_syncope",
      "chest_pain_rest", "medication_intolerance"
    ],
    auto_risk_flags: [],
  },

  "K40": {
    label: "Myocardial infarction (ACS)",
    category: "Medical",
    nice_ids: ["NG185", "QS99", "CG172"],
    pathway_slug: "acute-coronary-syndrome",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "chest_pain_recurrence", "antiplatelet_adherence",
      "statin_adherence", "ace_i_beta_blocker_titration",
      "blood_pressure", "cardiac_rehab_attendance",
      "smoking_cessation", "mood_depression_screen"
    ],
    red_flags: [
      "recurrent_chest_pain", "sudden_breathlessness",
      "new_palpitations", "antiplatelet_non_adherence",
      "depression_signs", "syncope"
    ],
    auto_risk_flags: [],
  },

  "K57": {
    label: "Atrial fibrillation",
    category: "Medical",
    nice_ids: ["NG196", "QS93", "TA249"],
    pathway_slug: "atrial-fibrillation",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "anticoagulation_adherence", "palpitation_symptom_burden",
      "heart_rate_control", "bleeding_signs",
      "stroke_symptoms", "blood_pressure", "alcohol_caffeine"
    ],
    red_flags: [
      "stroke_symptoms_fast", "significant_bleeding",
      "severe_palpitations", "missed_anticoagulant_doses",
      "inr_above_4"
    ],
    auto_risk_flags: [],
  },

  "S01": {
    label: "Ischaemic stroke",
    category: "Medical",
    nice_ids: ["NG128", "CG162", "QS2"],
    pathway_slug: "stroke",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "neurological_deficit_monitoring", "antiplatelet_or_anticoagulant",
      "blood_pressure_control", "swallowing_and_nutrition",
      "mood_and_post_stroke_depression",
      "rehabilitation_attendance", "falls_risk"
    ],
    red_flags: [
      "new_neurological_symptoms", "antiplatelet_non_adherence",
      "bp_above_180", "dysphagia_worsening",
      "severe_depression", "fall_with_injury"
    ],
    auto_risk_flags: ["extended_monitoring"],
  },

  "G45": {
    label: "TIA (transient ischaemic attack)",
    category: "Medical",
    nice_ids: ["NG128", "QS2"],
    pathway_slug: "tia",
    monitoring_window_days: 28,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "symptom_recurrence", "antiplatelet_adherence",
      "blood_pressure_control", "lifestyle_modification"
    ],
    red_flags: [
      "new_neurological_symptoms", "antiplatelet_non_adherence",
      "bp_crisis", "further_tia_or_stroke_symptoms"
    ],
    auto_risk_flags: [],
  },

  "J44": {
    label: "COPD exacerbation",
    category: "Medical",
    nice_ids: ["NG115", "QS10"],
    pathway_slug: "copd",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "breathlessness_score", "inhaler_adherence_and_technique",
      "steroid_and_antibiotic_course", "oxygen_saturation",
      "smoking_cessation", "pulmonary_rehab_referral"
    ],
    red_flags: [
      "spo2_below_88", "worsening_breathlessness",
      "inhaler_non_adherence", "fever_above_38",
      "unable_to_complete_sentences"
    ],
    auto_risk_flags: [],
  },

  "J18_PNEUMONIA": {
    label: "Pneumonia",
    category: "Medical",
    nice_ids: ["NG138", "QS110"],
    pathway_slug: "pneumonia",
    monitoring_window_days: 28,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "breathlessness_and_cough", "antibiotic_completion",
      "temperature_and_fever", "fatigue_and_recovery"
    ],
    red_flags: [
      "worsening_breathlessness", "fever_recurrence_after_day_3",
      "antibiotic_non_completion", "confusion_or_drowsiness"
    ],
    auto_risk_flags: [],
  },

  "A41": {
    label: "Sepsis",
    category: "Medical",
    nice_ids: ["NG51", "QS161"],
    pathway_slug: "sepsis",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "temperature_and_fever", "antibiotic_course_completion",
      "source_monitoring", "fatigue_and_functional_recovery",
      "cognitive_function", "psychological_impact"
    ],
    red_flags: [
      "fever_recurrence", "antibiotic_non_completion",
      "source_worsening", "acute_confusion",
      "significant_psychological_distress"
    ],
    auto_risk_flags: ["extended_monitoring"],
  },

  "I26": {
    label: "Pulmonary embolism (PE)",
    category: "Medical",
    nice_ids: ["NG158", "NG89", "QS29"],
    pathway_slug: "pulmonary-embolism",
    monitoring_window_days: 60,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    monitoring_domains: [
      "anticoagulation_adherence", "breathlessness_recovery",
      "bleeding_signs", "dvt_signs"
    ],
    red_flags: [
      "anticoagulant_non_adherence", "worsening_breathlessness",
      "significant_bleeding", "new_dvt_signs"
    ],
    auto_risk_flags: ["high_vte_risk"],
  },

  "E11_DKA": {
    label: "Diabetic ketoacidosis (DKA)",
    category: "Medical",
    nice_ids: ["NG17", "NG28", "QS6"],
    pathway_slug: "dka",
    monitoring_window_days: 28,
    call_days: [1, 3, 7, 14, 21, 28],
    monitoring_domains: [
      "blood_glucose_monitoring", "insulin_or_medication_adherence",
      "trigger_identification", "sick_day_rules_education",
      "ketone_monitoring"
    ],
    red_flags: [
      "glucose_above_15", "ketones_present",
      "insulin_non_adherence", "vomiting_preventing_medication"
    ],
    auto_risk_flags: [],
  },

  // ── MENTAL HEALTH ────────────────────────────────────────

  "Z03_MH": {
    label: "Acute psychiatric admission",
    category: "Mental Health",
    nice_ids: ["CG136", "NG10", "QS80"],
    pathway_slug: "acute-psychiatric",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "medication_concordance", "mood_and_mental_state",
      "safety_and_safeguarding", "community_team_engagement",
      "crisis_plan_awareness", "social_support_and_daily_living",
      "substance_use_screen"
    ],
    red_flags: [
      "suicidal_ideation", "medication_non_concordance",
      "missed_cmht_appointment", "safeguarding_concern",
      "significant_deterioration", "substance_use_relapse"
    ],
    auto_risk_flags: ["mental_health_pathway", "extended_monitoring"],
  },

  "X60": {
    label: "Self-harm / overdose",
    category: "Mental Health",
    nice_ids: ["CG133", "NG225", "QS34"],
    pathway_slug: "self-harm",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "safety_and_suicidality", "crisis_plan_and_means_restriction",
      "mental_health_follow_up", "medication_adherence",
      "mood_and_psychological_state", "social_and_protective_factors"
    ],
    red_flags: [
      "active_suicidal_ideation", "crisis_plan_not_in_place",
      "medication_non_adherence", "missed_followup",
      "significant_mood_deterioration"
    ],
    auto_risk_flags: ["mental_health_pathway", "extended_monitoring"],
  },

  "F20": {
    label: "First episode psychosis",
    category: "Mental Health",
    nice_ids: ["NG10", "NG185", "QS80", "NG58"],
    pathway_slug: "first-episode-psychosis",
    monitoring_window_days: 90,
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    monitoring_domains: [
      "antipsychotic_adherence", "psychotic_symptoms",
      "early_intervention_team_engagement", "safety_and_risk",
      "family_and_carer_support", "daily_functioning_and_insight"
    ],
    red_flags: [
      "antipsychotic_non_adherence", "acute_relapse_signs",
      "safety_concern", "eis_disengagement",
      "significant_functional_decline"
    ],
    auto_risk_flags: ["mental_health_pathway", "extended_monitoring"],
  },

}

// ── AUTO RISK FLAG RULES ─────────────────────────────────────────────────
export const AUTO_FLAG_RULES = {
  high_vte_risk: {
    label: "High VTE risk",
    tier: 1,
    reason: "Auto-detected from procedure — elevated VTE risk per NG89",
    effect: "Anticoagulation monitoring active. LMWH adherence domain enabled.",
  },
  emergency_procedure: {
    label: "Emergency procedure",
    tier: 1,
    reason: "Auto-detected: emergency procedure code selected",
    effect: "PTSD screening and trauma processing domains added.",
  },
  mental_health_pathway: {
    label: "Mental health pathway",
    tier: 1,
    reason: "Auto-detected: mental health admission pathway",
    effect: "Safeguarding domain active on every call. Safe messaging protocols applied.",
  },
  extended_monitoring: {
    label: "Extended monitoring (90 days)",
    tier: 1,
    reason: "Auto-detected: pathway requires 90-day monitoring window",
    effect: "Call schedule extended. Additional recovery domains active beyond 28 days.",
  },
}

// ── MANUAL RISK FLAG DEFINITIONS ─────────────────────────────────────────
export const MANUAL_FLAG_DEFS = [
  { key: "previous_vte",              label: "Previous VTE",                        desc: "Extends anticoagulation monitoring window and elevates DVT/PE red flag sensitivity" },
  { key: "lives_alone",               label: "Lives alone",                         desc: "Adds welfare check questions to days 1–3 calls" },
  { key: "mental_health_history",     label: "Mental health history",               desc: "Elevates mood monitoring thresholds across all calls" },
  { key: "previous_readmission",      label: "Previous readmission within 30 days", desc: "Increases call frequency in week 1 and lowers escalation thresholds" },
  { key: "frailty",                   label: "Frailty",                             desc: "Adds falls risk and cognitive monitoring domains" },
  { key: "safeguarding_concern",      label: "Active safeguarding concern",         desc: "Safeguarding domain active on every call. Clinical team alerted on any concern." },
  { key: "postnatal_depression_history", label: "Previous postnatal depression",   desc: "Elevates mood monitoring thresholds for obstetric pathways" },
]

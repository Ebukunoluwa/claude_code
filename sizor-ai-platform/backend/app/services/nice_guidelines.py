"""
Hardcoded NICE guidelines reference dict for clinical decision support.
Used by the Clinical Decision Engine to provide evidence-based recommendations.
"""

NICE_GUIDELINES = {
    "Heart Failure": {
        "red_flags": [
            "Sudden worsening breathlessness at rest — refer to emergency services (999)",
            "New or worsening ankle oedema with breathlessness — urgent same-day review",
            "Chest pain of any kind post-discharge — immediate 999 referral",
            "Oxygen saturation below 92% — emergency referral",
            "Acute confusion or reduced consciousness — 999",
            "Weight gain >2kg in 2 days — urgent GP review",
        ],
        "medication_review_triggers": [
            "ACE inhibitor/ARB dose optimisation review at 2 weeks post-discharge (NICE NG106)",
            "Beta-blocker up-titration review at 2 weeks if stable (NICE NG106)",
            "Diuretic dose adjustment if oedema worsening or breathlessness increasing",
            "SGLT2 inhibitor consideration if not already prescribed (NICE TA679)",
            "Aldosterone antagonist review if eGFR stable (NICE NG106)",
        ],
        "readmission_risk_factors": [
            "Prior HF hospitalisation in last 6 months",
            "EF < 35%",
            "Poor medication adherence",
            "Renal impairment (eGFR < 45)",
            "Uncontrolled AF",
            "Social isolation or poor self-management capability",
            "Diabetes mellitus",
        ],
        "follow_up_intervals": [
            "GP review within 2 weeks of discharge (NICE NG106)",
            "Cardiology outpatient within 6 weeks",
            "Daily weight monitoring — contact GP if >2kg gain in 2 days",
            "HF nurse specialist follow-up phone call within 7 days recommended",
        ],
        "recovery_curves": {
            "breathlessness": {1: 7, 3: 6, 7: 4, 14: 3},
            "pain": {1: 5, 3: 4, 7: 3, 14: 2},
            "mobility": {1: 4, 3: 5, 7: 6, 14: 7},
            "mood": {1: 4, 3: 5, 7: 6, 14: 7},
        },
    },
    "COPD": {
        "red_flags": [
            "Acute severe breathlessness unresponsive to usual bronchodilators — 999",
            "Central cyanosis — emergency admission",
            "Oxygen saturation below 88% — emergency review",
            "Acute confusion in context of COPD exacerbation — 999",
            "Inability to complete sentences due to breathlessness — 999",
        ],
        "medication_review_triggers": [
            "Review inhaler technique at every post-discharge contact (NICE NG115)",
            "Oral corticosteroid course completion — confirm no ongoing infection",
            "Antibiotic course review if prescribed",
            "Consider SABA prescription adequacy — >3 doses/day triggers review",
        ],
        "readmission_risk_factors": [
            "FEV1 < 30% predicted",
            "More than 2 exacerbations in prior 12 months",
            "Current smoker",
            "Hypoxia on discharge",
            "Poor inhaler technique",
            "Comorbid anxiety/depression (doubles readmission risk)",
        ],
        "follow_up_intervals": [
            "GP review within 2 weeks of discharge (NICE NG115)",
            "Respiratory nurse follow-up call within 72 hours recommended",
            "Pulmonary rehab referral within 4 weeks of stable discharge",
            "Spirometry review at 6 weeks post-exacerbation",
        ],
        "recovery_curves": {
            "breathlessness": {1: 7, 3: 6, 7: 5, 14: 4},
            "mobility": {1: 4, 3: 5, 7: 6, 14: 7},
        },
    },
    "Hip Replacement": {
        "red_flags": [
            "Sudden severe hip pain — possible dislocation — 999",
            "Unilateral leg swelling, calf pain, or warmth — DVT risk — same-day urgent review",
            "Shortness of breath post-surgery — PE risk — 999",
            "Wound dehiscence or purulent discharge — urgent surgical review",
            "Fever > 38.5°C beyond Day 3 — possible deep infection — urgent review",
        ],
        "medication_review_triggers": [
            "VTE prophylaxis (LMWH or DOAC) — confirm patient taking as prescribed (NICE NG89)",
            "Analgesia review — step-down from opioids by Day 7 typically expected",
            "Constipation from opioids — prophylactic laxatives should be prescribed",
        ],
        "readmission_risk_factors": [
            "BMI > 40",
            "Diabetes mellitus",
            "Prior DVT/PE history",
            "Age > 80",
            "Social isolation — inability to comply with mobility restrictions",
            "Poor pain control leading to immobility",
        ],
        "follow_up_intervals": [
            "Physiotherapy review within 72 hours of discharge (NICE NG89)",
            "Wound review at 10-14 days",
            "Orthopaedic outpatient at 6 weeks",
            "X-ray at 6 weeks to confirm prosthesis position",
        ],
        "recovery_curves": {
            "pain": {1: 8, 3: 6, 7: 4, 14: 2},
            "mobility": {1: 2, 3: 3, 7: 5, 14: 7},
        },
    },
}


def get_guidelines_for_condition(condition: str) -> dict:
    """Fuzzy match condition string to NICE guidelines entry."""
    c = condition.lower()
    if any(k in c for k in ["heart", "hf", "cardiac", "failure"]):
        return NICE_GUIDELINES["Heart Failure"]
    elif any(k in c for k in ["copd", "pulmonary", "respiratory", "obstructive"]):
        return NICE_GUIDELINES["COPD"]
    elif any(k in c for k in ["hip", "replacement", "arthroplasty", "thr"]):
        return NICE_GUIDELINES["Hip Replacement"]
    return {}

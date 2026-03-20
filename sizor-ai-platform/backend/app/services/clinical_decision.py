"""Clinical Decision Engine — on-demand only, never triggered automatically."""
import json
import re
from .llm_client import LLMClient
from .nice_guidelines import get_guidelines_for_condition


def _extract_section(text: str, section: str) -> str:
    pattern = rf'{section}:\s*(.*?)(?=\n[A-Z_]{{2,}}:|$)'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_json_section(text: str, section: str):
    pattern = rf'{section}:\s*(\[.*?\]|\{{.*?\}})'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return []


async def generate_clinical_decision(
    clinical_question,
    patient_name: str,
    age,
    condition: str,
    day: int,
    medical_profile: dict,
    current_soap: str,
    current_extraction: dict,
    ftp_record: dict,
    open_flags: list,
    longitudinal_narrative: str,
    trend_data: list,
    clinician_actions: list,
    probe_outcomes: list,
) -> dict:
    llm = LLMClient()
    guidelines = get_guidelines_for_condition(condition)

    system = (
        "You are an NHS clinical decision support system embedded within a post-discharge monitoring platform. "
        "You assist clinicians in reviewing patient progress and deciding on next steps. "
        "You never make diagnoses. You never tell patients anything directly. "
        "You present structured clinical reasoning to qualified clinicians to support — not replace — their judgment. "
        "Always cite NICE guidelines where relevant. Always flag uncertainty clearly. "
        "Always present options rather than directives."
    )

    question = clinical_question or "Please provide a full clinical decision support assessment for this patient based on all available data."
    age_str = f"{age} years old" if age else "age unknown"
    nice_text = json.dumps(guidelines, indent=2) if guidelines else "No specific NICE guidelines found for this condition."

    user = f"""A clinician is reviewing the following patient record and needs decision support.

{question}

PATIENT CONTEXT:
Patient: {patient_name}, {age_str}, {condition}, Day {day} post-discharge
Medical history: {json.dumps(medical_profile)}
Discharge summary: {medical_profile.get('discharge_summary_text', 'Not available')}

CURRENT CALL DATA (Day {day}):
SOAP assessment: {current_soap}
Scores: {json.dumps(current_extraction)}
FTP status: {ftp_record.get('ftp_status', 'unknown')}
FTP reasoning: {ftp_record.get('reasoning_text', 'Not available')}
Active flags: {json.dumps(open_flags)}

LONGITUDINAL CONTEXT:
{longitudinal_narrative}
Score trends across all calls: {json.dumps(trend_data)}
Previous clinician actions and notes: {json.dumps(clinician_actions)}
Probe call outcomes: {json.dumps(probe_outcomes)}

NICE GUIDELINES FOR {condition}:
{nice_text}

Provide your assessment in the following exact structure:

CLINICAL_PICTURE: A concise paragraph summarising the overall clinical picture based on all available data. What is this patient's trajectory and current risk level?

DIFFERENTIAL_CONSIDERATIONS: [{{"explanation": "...", "supporting_evidence": "...", "against_evidence": "...", "likelihood": "high/medium/low"}}]

RECOMMENDED_ACTIONS: [{{"action": "...", "rationale": "...", "urgency": "immediate/within_24h/routine", "nice_reference": "..."}}]

RISK_ASSESSMENT: A plain English paragraph assessing readmission risk, deterioration risk, and any patient safety concerns. Be specific about what could go wrong and on what timescale.

UNCERTAINTY_FLAGS: [{{"unknown": "...", "why_it_matters": "...", "how_to_find_out": "..."}}]

NICE_REFERENCES: [{{"guideline": "...", "recommendation": "...", "relevance_to_this_patient": "..."}}]"""

    full = await llm.complete(system, user)

    clinical_picture = _extract_section(full, "CLINICAL_PICTURE")
    differential = _extract_json_section(full, "DIFFERENTIAL_CONSIDERATIONS")
    actions = _extract_json_section(full, "RECOMMENDED_ACTIONS")
    risk = _extract_section(full, "RISK_ASSESSMENT")
    uncertainty = _extract_json_section(full, "UNCERTAINTY_FLAGS")
    nice_refs = _extract_json_section(full, "NICE_REFERENCES")

    return {
        "differential_diagnoses": differential if isinstance(differential, list) else [],
        "recommended_actions": actions if isinstance(actions, list) else [],
        "risk_assessment": risk or full[:500],
        "uncertainty_flags": uncertainty if isinstance(uncertainty, list) else [],
        "nice_references": nice_refs if isinstance(nice_refs, list) else [],
        "full_reasoning_text": full,
    }

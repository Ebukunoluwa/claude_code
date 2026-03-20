"""Post-call processing pipeline. All LLM calls go through LLMClient."""
import json
import re
from .llm_client import LLMClient
from ..config import settings


def _parse_json(text: str):
    """Extract JSON from LLM response that may contain surrounding text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    for sc, ec in [('{', '}'), ('[', ']')]:
        s, e = text.find(sc), text.rfind(ec)
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e + 1])
            except json.JSONDecodeError:
                pass
    return {}


async def extract_clinical_scores(transcript: str) -> dict:
    llm = LLMClient()
    system = (
        "You are a clinical data extraction system. Extract the following structured data "
        "from this patient call transcript. Return ONLY valid JSON, no other text. "
        "Extract: pain_score (0-10), breathlessness_score (0-10), mobility_score (0-10), "
        "appetite_score (0-10), mood_score (0-10), medication_adherence (true/false), "
        "and condition_specific_flags as a JSON object containing any clinically relevant "
        "observations mentioned. If a domain is not mentioned return null."
    )
    resp = await llm.complete(system, f"TRANSCRIPT:\n{transcript}")
    return _parse_json(resp)


async def generate_soap_note(transcript: str) -> dict:
    llm = LLMClient()
    system = (
        "You are a clinical documentation assistant for an NHS post-discharge monitoring system. "
        "Generate a structured SOAP note from this patient call transcript. "
        "Return as JSON with keys: subjective, objective, assessment, plan. "
        "SUBJECTIVE: what the patient reported in their own words. "
        "OBJECTIVE: measurable data points — scores, frequencies, durations. "
        "ASSESSMENT: clinical interpretation of current status — do not diagnose, summarise clinical picture. "
        "PLAN: recommended next steps for the clinician to consider. "
        "Write in professional NHS clinical documentation style. Be concise and clinically precise."
    )
    resp = await llm.complete(system, f"TRANSCRIPT:\n{transcript}")
    return _parse_json(resp)


async def generate_ftp_reasoning(condition: str, day: int, expected: dict, actual: dict, variance: dict, ftp_status: str) -> str:
    llm = LLMClient()
    system = "You are a clinical progress assessment system."
    user = (
        f"Given the expected recovery scores and actual scores for this patient on day {day} of recovery "
        f"from {condition}, write a concise clinical reasoning paragraph explaining their failure to progress "
        f"status of '{ftp_status}'. Reference specific domains that are concerning. "
        f"Use professional clinical language suitable for an NHS clinician.\n\n"
        f"Expected scores: {json.dumps(expected)}\n"
        f"Actual scores: {json.dumps(actual)}\n"
        f"Variance per domain: {json.dumps(variance)}"
    )
    return await llm.complete(system, user)


async def evaluate_flags(extraction: dict, ftp_status: str, day: int) -> list[dict]:
    """Returns list of flag dicts with severity, flag_type, trigger_description."""
    flags = []
    pain = extraction.get("pain_score")
    breathlessness = extraction.get("breathlessness_score")
    mood = extraction.get("mood_score")
    adherence = extraction.get("medication_adherence")
    cflags = extraction.get("condition_specific_flags", {})

    # RED flags
    if pain is not None and pain >= 8:
        flags.append({"severity": "red", "flag_type": "chest_pain",
                      "trigger_description": f"Pain score {pain}/10 — exceeds RED threshold"})
    if breathlessness is not None and breathlessness >= 8:
        flags.append({"severity": "red", "flag_type": "breathlessness",
                      "trigger_description": f"Breathlessness score {breathlessness}/10 — exceeds RED threshold"})
    if cflags.get("chest_pain") or cflags.get("chest pain") or cflags.get("chest_pressure"):
        flags.append({"severity": "red", "flag_type": "chest_pain",
                      "trigger_description": "Chest pain/pressure reported in call"})
    if adherence is False and day >= 3:
        flags.append({"severity": "red", "flag_type": "medication",
                      "trigger_description": f"Medication non-adherence reported on Day {day}"})

    # AMBER flags (only if no RED)
    if not flags:
        scores = [pain, breathlessness, extraction.get("mobility_score"),
                  extraction.get("appetite_score"), mood]
        if any(s is not None and s >= 6 for s in scores):
            flags.append({"severity": "amber", "flag_type": "other",
                          "trigger_description": "One or more clinical scores >= 6"})
        if ftp_status in ("behind", "significantly_behind"):
            flags.append({"severity": "amber", "flag_type": "ftp",
                          "trigger_description": f"FTP status: {ftp_status}"})
        if mood is not None and mood <= 3:
            flags.append({"severity": "amber", "flag_type": "mood",
                          "trigger_description": f"Mood score {mood}/10 — below threshold"})

    if not flags:
        flags.append({"severity": "green", "flag_type": "other",
                      "trigger_description": "All scores within acceptable range"})
    return flags


async def generate_longitudinal_summary(
    patient_name: str, age, discharge_date: str, condition: str, procedure,
    day: int, soap_assessment: str, scores: dict, ftp_status: str, ftp_reasoning: str,
    flags: list, probe_instructions, previous_narrative, version: int
) -> dict:
    llm = LLMClient()
    system = (
        "You are a senior NHS clinical documentation system. You generate longitudinal patient summaries "
        "that read as if written by an experienced clinician. These summaries are used by clinical teams "
        "to understand a patient's full post-discharge journey at a glance."
    )
    age_str = f"{age} years old" if age else "age unknown"
    flags_str = "; ".join([f["trigger_description"] for f in flags]) or "None"
    user = f"""Generate an updated longitudinal clinical summary for this patient.

Patient: {patient_name}, {age_str}, discharged {discharge_date} following {procedure or condition}.

Previous summary narrative: {previous_narrative or 'No previous summary.'}

New call data (Day {day}):
SOAP assessment: {soap_assessment}
Scores: pain {scores.get('pain')}, breathlessness {scores.get('breathlessness')}, mobility {scores.get('mobility')}, mood {scores.get('mood')}, medication adherence {scores.get('adherence')}
FTP status: {ftp_status} — {ftp_reasoning}
Flags raised: {flags_str}
Probe call context: {probe_instructions or 'None'}

Write a single flowing clinical narrative paragraph (150-250 words) incorporating the full journey from discharge to today. Reference specific score changes, trends, concerns raised and actions taken. Write in third person. Use NHS clinical documentation style. No bullet points — flowing prose only.

Then provide:
ACTIVE_CONCERNS: JSON array with fields: concern, raised_on_day, severity, current_status
TREND_SNAPSHOT: JSON object — one key per domain — value: object with direction (improving/static/deteriorating) and concerning (true/false)"""

    resp = await llm.complete(system, user)
    narrative = resp
    active_concerns = []
    trend_snapshot = {}

    ac = re.search(r'ACTIVE_CONCERNS:\s*(\[.*?\])', resp, re.DOTALL)
    if ac:
        try:
            active_concerns = json.loads(ac.group(1))
            narrative = resp[:ac.start()].strip()
        except json.JSONDecodeError:
            pass

    ts = re.search(r'TREND_SNAPSHOT:\s*(\{.*?\})', resp, re.DOTALL)
    if ts:
        try:
            trend_snapshot = json.loads(ts.group(1))
        except json.JSONDecodeError:
            pass

    return {
        "narrative_text": narrative,
        "active_concerns_snapshot": active_concerns,
        "trend_snapshot": trend_snapshot,
        "version_number": version,
    }

"""Post-call processing pipeline. All LLM calls go through LLMClient."""
import json
import re
from .llm_client import LLMClient
from app.clinical_intelligence.smoothing import smooth_extraction, to_persistable_dict
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


async def extract_clinical_scores(transcript: str, domains: list | None = None) -> dict:
    """
    Infer clinical scores from an open-ended SOCRATES-style call transcript.

    The call does NOT ask patients for explicit numeric ratings — the agent uses
    conversational questioning and the patient describes their symptoms naturally.
    This function reads those descriptions and assigns clinical scores based on
    the severity of what was reported.
    """
    llm = LLMClient()

    # Core scoring inference guidance — maps natural language to scores
    inference_guide = """
SCORING FROM NATURAL LANGUAGE — HOW TO INFER SCORES:

For pain_score, breathlessness_score, mobility_score, appetite_score (0-10 scale, higher = worse):
  0     — "fine", "no problem", "completely gone", "back to normal", "not at all"
  1-2   — "barely notice it", "very mild", "a little bit", "manageable", "slight", "minor"
  3-4   — "still there", "some days", "moderate", "a bit sore", "coming and going", "managing but..."
  5-6   — "quite bad", "bothering me a lot", "difficult", "affecting my sleep", "struggling with it"
  7-8   — "really bad", "worse than before", "can't sleep because of it", "stops me doing things"
  9-10  — "unbearable", "excruciating", "can't move at all", "can't breathe properly", "terrifying"

For mood_score (0-10, INVERTED — 10 = excellent, 0 = severe depression):
  8-10  — upbeat, positive, managing well, enjoying things, feels supported
  5-7   — "not great in myself", "a bit down", "worried", "some bad days", "anxious"
  2-4   — "really low", "can't enjoy anything", hopeless, not coping, crying frequently
  0-1   — any mention of self-harm, suicidal thoughts, or complete inability to function

For medication_adherence (true/false/null):
  true  — taking all medications as prescribed
  false — missed doses, stopped a medication, running out, side effects causing non-adherence
  null  — not discussed

IMPORTANT INFERENCE RULES:
- Do NOT require explicit numbers. A patient saying "it's agony, I can barely get out of bed"
  is clearly a 8-9 on pain even if they never said a number.
- A patient saying "it's a bit sore but I'm managing fine" is a 2-3.
- Functional impact is your strongest signal: "it stops me doing X" = moderate-severe.
- Words like "still", "not quite right", "getting there" = mild-to-moderate (3-4 range).
- Absence of complaint when a topic was clearly explored = 0-1.
- If the patient was not asked about a domain or gave no relevant response, return null.
"""

    domain_instruction = ""
    if domains:
        domain_list = ", ".join(d.replace("_", " ") for d in domains)
        domain_instruction = (
            f"\n\nPATHWAY DOMAINS — the agent explored these specific clinical areas: {domain_list}.\n"
            "Extract 'domain_scores' as a JSON object where each key is a domain name "
            "(snake_case, exactly as listed above) and the value is a 0-4 score inferred from "
            "what the patient described.\n\n"
            "DOMAIN SCORING SCALE (0–4) — CALIBRATION GUIDE:\n"
            "  0 = No problem at all. Patient says it's fine, healed, normal, not an issue.\n"
            "      Examples: 'the wound looks great', 'no pain at all', 'moving around fine',\n"
            "                'mood is good', 'taking all my tablets', 'back to normal'.\n"
            "  1 = Mild — expected at this stage of recovery. Minor issues, well managed.\n"
            "      Examples: 'a bit sore but okay', 'slight redness but not hot', 'a little tired',\n"
            "                'mostly fine, just get a bit breathless on stairs', 'some days are hard'.\n"
            "  2 = Moderate — more than expected, bears watching but not urgent.\n"
            "      Examples: 'quite sore', 'wound edge looks a bit open — about half a centimetre',\n"
            "                'struggling to get up and down stairs', 'feeling quite low', 'missing\n"
            "                some doses', 'much more tired than I expected'.\n"
            "  3 = Significant — warrants same-day clinical review or GP contact.\n"
            "      Examples: 'wound is definitely opening up', 'really struggling to breathe',\n"
            "                'can barely get out of bed', 'crying every day, not coping',\n"
            "                'bleeding much more than normal', 'I think it might be infected — it's\n"
            "                very red and hot and there's fluid coming out'.\n"
            "  4 = Severe / emergency — warrants 999 or immediate escalation RIGHT NOW.\n"
            "      Examples: 'I can't breathe at all', 'I'm having chest pains right now',\n"
            "                'the wound has completely opened', 'I'm having thoughts of harming myself',\n"
            "                'I'm losing a lot of blood', 'I think I'm having a stroke'.\n\n"
            "CRITICAL CALIBRATION RULES FOR DOMAIN SCORING:\n"
            "- A patient describing normal expected recovery discomfort is ALWAYS 0 or 1.\n"
            "- A 3 means the clinician needs to call back TODAY. A 4 means call 999 now.\n"
            "  Do NOT assign 3 or 4 unless the patient described something genuinely alarming.\n"
            "- If the agent asked about a red flag (e.g. 'any chest pain?') and the patient\n"
            "  said NO — that domain scores 0 or 1, NOT 3 or 4. The question being asked does\n"
            "  not mean the patient reported the symptom.\n"
            "- Most post-discharge patients on day 1-5 should score 0-2 across most domains.\n"
            "  All domains scoring 3 or 4 is almost never correct and signals a calibration error.\n"
            "- Apply the same natural-language inference principles used above for 0-10 scores.\n"
            "Omit a domain only if it was genuinely not discussed."
        )

    system = (
        "You are a senior NHS clinical data analyst. A post-discharge patient call was conducted "
        "using open-ended conversational questioning (SOCRATES method) — the patient described "
        "their symptoms in their own words and was not asked to rate anything numerically.\n\n"
        "Your job: read the transcript and infer clinical severity scores from the patient's "
        "descriptions. You are acting as a clinician interpreting what a patient reported.\n\n"
        + inference_guide +
        "\nReturn ONLY valid JSON with these fields:\n"
        "  pain_score (0-10 or null)\n"
        "  breathlessness_score (0-10 or null)\n"
        "  mobility_score (0-10 or null)\n"
        "  appetite_score (0-10 or null)\n"
        "  mood_score (0-10 or null — INVERTED: 10=excellent, 0=severe)\n"
        "  medication_adherence (true / false / null)\n"
        "  condition_specific_flags — JSON object with any notable clinical observations, "
        "exact quotes from the patient that indicated concern, and whether red flags were raised.\n"
        "No other text."
        + domain_instruction
    )

    resp = await llm.complete(system, f"TRANSCRIPT:\n{transcript}")
    result = _parse_json(resp)

    # Nest domain_scores inside condition_specific_flags so it's stored in the JSONB column
    if domains and isinstance(result.get("domain_scores"), dict):
        flags = result.setdefault("condition_specific_flags", {})
        flags["domain_scores"] = result.pop("domain_scores")

    return result


async def generate_soap_note(transcript: str) -> dict:
    llm = LLMClient()
    system = (
        "You are an NHS clinician writing a post-consultation SOAP note. "
        "Generate a structured SOAP note from this patient call transcript exactly as a doctor would document it. "
        "Return ONLY valid JSON with keys: subjective, objective, assessment, plan.\n\n"
        "SUBJECTIVE: The patient's reported symptoms, concerns, and self-reported status in their own words. "
        "Start with the chief complaint. Include symptom duration, severity, and any changes since discharge. "
        "Write in third person: 'Patient reports...', 'Patient denies...', 'Patient states...'\n\n"
        "OBJECTIVE: Clinically measurable data points only — pain scores (e.g. 3/10), mobility ratings, "
        "medication adherence (yes/no), any specific clinical values mentioned. "
        "If no objective data was captured, write 'No objective data captured on this call.'\n\n"
        "ASSESSMENT: Your clinical interpretation of the patient's current status. "
        "State whether they are progressing as expected, any concerns, and clinical risk level (low/moderate/high). "
        "Reference specific symptoms. Do not diagnose.\n\n"
        "PLAN: Specific, actionable next steps only — e.g. 'GP review within 48 hours', "
        "'Continue current medication regime', 'Wound review at next appointment', 'Escalate to on-call team'. "
        "Be directive and concrete.\n\n"
        "STRICT RULES — violating these makes the note unusable:\n"
        "- Never mention missed calls, call attempts, phone calls, or any call logistics.\n"
        "- Never mention the AI, the system, or that this was an automated call.\n"
        "- Never include administrative commentary.\n"
        "- Write exactly as a doctor documents a clinical consultation.\n"
        "- Be concise — no padding, no repetition."
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


async def evaluate_flags(
    extraction: dict,
    ftp_status: str,
    day: int,
    prior_smoothed: dict | None = None,
    critical_medication: bool = False,
) -> tuple[list[dict], dict]:
    """Returns (flags, smoothed_state_to_persist)."""
    flags: list[dict] = []

    # Raw extraction for hard RED triggers (unchanged)
    pain = extraction.get("pain_score")
    breathlessness = extraction.get("breathlessness_score")
    adherence = extraction.get("medication_adherence")
    cflags = extraction.get("condition_specific_flags", {})

    # Smoothing pass — the new bit
    smoothed = smooth_extraction(
        extraction, prior_smoothed, critical_medication=critical_medication
    )
    persistable = to_persistable_dict(smoothed)

    # --- RED flags (RAW-SCORE TRIGGERS — intentionally NOT smoothed) ---
    if pain is not None and pain >= 8:
        flags.append({
            "severity": "red", "flag_type": "chest_pain",
            "trigger_description": f"Pain score {pain}/10 — exceeds RED threshold",
        })
    if breathlessness is not None and breathlessness >= 8:
        flags.append({
            "severity": "red", "flag_type": "breathlessness",
            "trigger_description": f"Breathlessness score {breathlessness}/10 — exceeds RED threshold",
        })
    if cflags.get("chest_pain") or cflags.get("chest pain") or cflags.get("chest_pressure"):
        flags.append({
            "severity": "red", "flag_type": "chest_pain",
            "trigger_description": "Chest pain/pressure reported in call",
        })
    # Medication non-adherence RED only for critical meds; others AMBER below
    if adherence is False and day >= 3 and critical_medication:
        flags.append({
            "severity": "red", "flag_type": "medication",
            "trigger_description": f"Critical medication non-adherence on Day {day}",
        })

    # --- AMBER flags (only if no RED). Uses SMOOTHED aggregate. ---
    if not flags:
        if smoothed.max_smoothed >= 6.0:
            flags.append({
                "severity": "amber", "flag_type": "other",
                "trigger_description": (
                    f"Smoothed symptom trend elevated "
                    f"(max {smoothed.max_smoothed:.1f}/10)"
                ),
            })

        if ftp_status in ("behind", "significantly_behind"):
            flags.append({
                "severity": "amber", "flag_type": "ftp",
                "trigger_description": f"FTP status: {ftp_status}",
            })

        # Mood is inversely scored (lower = worse). Smoothed mood.
        if smoothed.mood is not None and smoothed.mood <= 3.0:
            flags.append({
                "severity": "amber", "flag_type": "mood",
                "trigger_description": f"Smoothed mood {smoothed.mood:.1f}/10 — below threshold",
            })

        if adherence is False and day >= 3 and not critical_medication:
            flags.append({
                "severity": "amber", "flag_type": "medication",
                "trigger_description": (
                    f"Medication non-adherence reported on Day {day} "
                    f"(non-critical — monitoring)"
                ),
            })

    if not flags:
        flags.append({
            "severity": "green", "flag_type": "other",
            "trigger_description": "All scores within acceptable range",
        })

    return flags, persistable



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

    # Extract JSON from either plain or backtick-fenced blocks, e.g.:
    #   ACTIVE_CONCERNS: [...]
    #   TREND_SNAPSHOT: ```json\n{...}\n```
    _JSON_BLOCK = r'(?:```(?:json)?\s*)?([\[{].*?[\]}])\s*(?:```)?'

    ac = re.search(r'ACTIVE_CONCERNS:\s*' + _JSON_BLOCK, resp, re.DOTALL)
    if ac:
        try:
            active_concerns = json.loads(ac.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
        # Strip everything from this sentinel onwards
        narrative = resp[:ac.start()].strip()

    ts = re.search(r'TREND_SNAPSHOT:\s*' + _JSON_BLOCK, resp, re.DOTALL)
    if ts:
        try:
            trend_snapshot = json.loads(ts.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
        # Also strip if it appeared before ACTIVE_CONCERNS (shouldn't, but defensive)
        if ts.start() < len(narrative):
            narrative = narrative[:ts.start()].strip()

    # Final safety strip — remove any remaining sentinel lines and fenced blocks
    narrative = re.sub(
        r'\n?(?:ACTIVE_CONCERNS|TREND_SNAPSHOT):.*',
        '', narrative, flags=re.DOTALL,
    ).strip()
    narrative = re.sub(r'```(?:json)?\s*[\[{].*?[\]}]\s*```', '', narrative, flags=re.DOTALL).strip()

    return {
        "narrative_text": narrative,
        "active_concerns_snapshot": active_concerns,
        "trend_snapshot": trend_snapshot,
        "version_number": version,
    }

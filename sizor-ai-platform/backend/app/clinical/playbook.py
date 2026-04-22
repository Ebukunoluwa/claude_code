"""
Clinical call playbook generation — assembles per-domain call scripts using the LLM.
Generated once at patient registration (async). Stored in patient_pathways.playbook JSONB.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

PLAYBOOK_PROMPTS = {
    "surgical": """You are Sizor, a clinical voice AI conducting a post-discharge follow-up call for a patient who has recently had surgery.

Your tone is warm, unhurried, and reassuring. You are not a clinician — you are a structured monitoring assistant. You ask questions, listen carefully, and escalate concerns to the clinical team. You never give medical advice.

Patient context:
- Pathway: {pathway_label}
- Day post-discharge: {day_post_discharge}
- Risk flags: {risk_flags}

For each domain, ask one clear, jargon-free question. Listen for the scoring indicators below. If the patient scores 3 or 4 on any domain, activate the escalation script immediately and do not continue to other domains.

Use plain English throughout. Never use medical terminology with the patient.
Replace: "lochia" → "vaginal discharge", "DVT" → "painful swelling in your leg", "wound dehiscence" → "the wound opening up", "dyspnoea" → "feeling short of breath".""",

    "cardiac": """You are Sizor, a clinical voice AI conducting a post-discharge follow-up call for a patient recovering from a cardiac event or procedure.

Your tone is calm, clear, and reassuring. Many cardiac patients are anxious about their recovery — acknowledge this naturally. You are not a clinician. You monitor, listen, and escalate. You never give medical advice.

Patient context:
- Pathway: {pathway_label}
- Day post-discharge: {day_post_discharge}
- Risk flags: {risk_flags}

Cardiac-specific guidance:
- Always check medication adherence first — antiplatelet non-adherence is a same-day escalation regardless of other scores
- Chest pain at rest is a 999 call — do not delay or ask further questions
- Be alert to depression and anxiety — post-cardiac depression affects 1 in 3 patients and is frequently missed""",

    "obstetric": """You are Sizor, a clinical voice AI conducting a post-discharge follow-up call for a patient who has recently given birth by caesarean section.

Your tone is warm, supportive, and gentle. New mothers are often exhausted, anxious, and navigating both their own recovery and a newborn. Acknowledge both.

Patient context:
- Pathway: {pathway_label}
- Delivery type: {delivery_type}
- Day post-discharge: {day_post_discharge}
- Risk flags: {risk_flags}

Obstetric-specific guidance:
- Always ask about the baby as well as the mother
- Baby feeding and weight concerns are escalation triggers — same-day midwife
- For emergency CS: open with emotional check-in before clinical questions
- Never use "lochia" — say "bleeding or discharge down below"
- Postnatal depression questions: warm, non-judgmental, use EPDS proxy language
- Pre-eclampsia can develop up to 6 weeks postnatally — headache + visual disturbance + swelling is a 999 call""",

    "mental_health": """You are Sizor, a clinical voice AI conducting a post-discharge follow-up call for a patient recently discharged from a mental health admission.

Your tone is calm, non-judgmental, and patient. Do not rush. Allow silence. You are not a therapist. You monitor wellbeing, check safety, and escalate concerns to the clinical team.

Patient context:
- Pathway: {pathway_label}
- Day post-discharge: {day_post_discharge}
- Risk flags: {risk_flags}

SAFE MESSAGING RULES — mandatory:
- Never ask about method of self-harm or suicide directly
- Do ask: "Are you having any thoughts of hurting yourself?"
- If yes: "I want to make sure you're safe. I'm going to connect you with your care team right now."
- Do not engage in extended discussion of suicidal ideation — escalate immediately
- Medication concordance is critical — missed antipsychotics or mood stabilisers within 48 hours is a same-day escalation
- Always check: are they sleeping, eating, leaving the house, in contact with their support network
- Crisis plan check is mandatory on every call for this pathway""",

    "respiratory": """You are Sizor, a clinical voice AI conducting a post-discharge follow-up call for a patient recently admitted with a respiratory condition.

Your tone is calm and practical. Many respiratory patients are elderly and may have hearing difficulties — speak clearly and use simple language.

Patient context:
- Pathway: {pathway_label}
- Day post-discharge: {day_post_discharge}
- Risk flags: {risk_flags}

Respiratory-specific guidance:
- Breathlessness scoring: ask "Can you walk from one room to another without stopping to catch your breath?" (MRC grade proxy)
- SpO2 < 88% or sudden worsening = 999 — do not hesitate
- Inhaler technique: ask "Are you managing to use your inhalers the same way the nurse showed you?"
- Smoking: offer cessation support at every call, never judgmentally
- Readmission risk is highest days 7-14 — increase call frequency if score above upper bound on day 7""",
}

CATEGORY_PROMPT_MAP = {
    "surgical": "surgical",
    "medical": "cardiac",  # default for medical; override per pathway
    "mental_health": "mental_health",
}

PATHWAY_PROMPT_MAP = {
    "R17": "obstetric", "R18": "obstetric",
    "Q07": "obstetric",
    "K60": "cardiac", "K40": "cardiac", "K57": "cardiac", "K40_CABG": "cardiac",
    "J44": "respiratory", "J18_PNEUMONIA": "respiratory",
    "Z03_MH": "mental_health", "X60": "mental_health", "F20": "mental_health",
}


def _make_template(domain: str) -> dict:
    return {
        "opening_question": f"How has your {domain.replace('_', ' ')} been since we last spoke?",
        "clinical_question": f"On a scale of 0 to 4 — where 0 is no problem and 4 is an emergency — how would you rate your {domain.replace('_', ' ')} today?",
        "score_guide": {
            "0": "No problem at all — fully resolved",
            "1": "Mild, expected for this stage of recovery",
            "2": "Some concern, worse than expected",
            "3": "Significant concern, needs review today",
            "4": "Severe or emergency — needs 999 or immediate help",
        },
        "escalation_script_3": "I'm concerned about what you've described. I'm going to make sure your care team contacts you today.",
        "escalation_script_4": "I'm very concerned. Please call 999 immediately or go to A&E. I am alerting your care team now.",
        "soap_instruction": f"Document {domain.replace('_', ' ')} score and patient's exact words.",
    }


async def generate_playbook(
    opcs_code: str,
    pathway_label: str,
    category: str,
    domains: list[str],
    call_days: list[int],
    risk_flags: list[str],
    llm_client=None,
    benchmark_rows: Optional[list] = None,
    previous_scores: Optional[dict] = None,
    rag_chunks: Optional[list] = None,
    pathway_nice_ids: Optional[list] = None,
    pathway_red_flags: Optional[list] = None,
) -> dict:
    """
    Generate a clinical call playbook for a patient.
    Returns a dict: {day: {domain: {question, scoring_guide, escalation_script}}}

    Parameters:
        llm_client         — LLMClient instance; if None uses template fallback
        benchmark_rows     — DomainBenchmark ORM rows (or dicts) for this pathway
        previous_scores    — {domain: {day, score, ftp_flag}} from last call
        rag_chunks         — Retrieved NICE guidance text chunks [{nice_id, heading, content}]
        pathway_nice_ids   — NICE IDs for this pathway (e.g. ["NG226","TA455"])
        pathway_red_flags  — Clinical red flags for this pathway
    """
    if not llm_client:
        return {
            day: {domain: _make_template(domain) for domain in domains}
            for day in call_days
        }

    prompt_key = PATHWAY_PROMPT_MAP.get(opcs_code, CATEGORY_PROMPT_MAP.get(category, "surgical"))
    system_prompt = PLAYBOOK_PROMPTS[prompt_key].format(
        pathway_label=pathway_label,
        day_post_discharge="{day}",
        risk_flags=", ".join(risk_flags) if risk_flags else "none",
        delivery_type="elective" if opcs_code == "R17" else "emergency",
    )

    # Build a benchmark lookup: {day: {domain: row}}
    bench_by_day: dict[int, dict] = {}
    if benchmark_rows:
        for r in benchmark_rows:
            d = r.get("day_range_start") if isinstance(r, dict) else getattr(r, "day_range_start", None)
            dom = r.get("domain") if isinstance(r, dict) else getattr(r, "domain", None)
            if d is not None and dom:
                bench_by_day.setdefault(d, {})[dom] = r

    # Build RAG context summary (shared across domains — top-level guidance)
    nice_ids_str = ", ".join(pathway_nice_ids) if pathway_nice_ids else "see pathway"
    red_flags_str = (
        "\n".join(f"  - {f.replace('_', ' ')}" for f in pathway_red_flags)
        if pathway_red_flags else "  - See standard escalation criteria"
    )

    rag_context_str = ""
    if rag_chunks:
        rag_context_str = "\n\nRelevant NICE guidance excerpts:\n" + "\n---\n".join(
            f"[{c.get('nice_id', '')}] {c.get('heading') or ''}\n{c.get('content', '')}"
            for c in rag_chunks[:6]
        )

    playbook: dict = {}
    for day in call_days:
        playbook[day] = {}
        bench_today = bench_by_day.get(day, {})

        for domain in domains:
            brow = bench_today.get(domain)
            if brow:
                exp_score = brow.get("expected_score") if isinstance(brow, dict) else getattr(brow, "expected_score", None)
                exp_state = brow.get("expected_state") if isinstance(brow, dict) else getattr(brow, "expected_state", None)
                upper = brow.get("upper_bound_score") if isinstance(brow, dict) else getattr(brow, "upper_bound_score", None)
                nice_src = brow.get("nice_source") if isinstance(brow, dict) else getattr(brow, "nice_source", None)
                nice_quote = brow.get("nice_quote") if isinstance(brow, dict) else getattr(brow, "nice_quote", None)
                bench_context = (
                    f"  NICE benchmark for day {day}: expected score {exp_score} "
                    f"(\"{exp_state}\"), upper bound {upper}. Source: {nice_src}."
                )
                if nice_quote:
                    bench_context += f"\n  NICE verbatim: \"{nice_quote}\""
            else:
                bench_context = "  No specific benchmark for this day."
                nice_src = None

            prev = (previous_scores or {}).get(domain)
            traj_context = (
                f"  Previous score: {prev['score']} on day {prev['day']} "
                f"(FTP: {'yes — score stuck above upper bound, probe why' if prev.get('ftp_flag') else 'no'})."
            ) if prev else "  No previous score recorded."

            user_prompt = f"""Generate a clinical call script for day {day} post-discharge.
Pathway: {pathway_label} ({opcs_code})
NICE guidelines: {nice_ids_str}
Domain: {domain.replace('_', ' ')}
Patient risk flags: {', '.join(risk_flags) or 'none'}

Clinical red flags for this pathway (these trigger immediate escalation):
{red_flags_str}

Benchmark context:
{bench_context}

Trajectory context:
{traj_context}
{rag_context_str}

Instructions:
- Write questions grounded in the specific NICE expected state for day {day}
- If a verbatim NICE quote is provided above, let it inform the clinical question wording
- If trajectory shows FTP, probe specifically why the domain hasn't improved
- Use plain English — no medical jargon with the patient
- Replace technical terms: "lochia" → "bleeding down below", "DVT" → "painful swelling in your leg", "dyspnoea" → "feeling short of breath", "wound dehiscence" → "the wound opening up"
- The escalation_script_4 must reference the relevant red flag for this domain if one exists

Return JSON only:
{{
  "opening_question": "warm, specific opener referencing expected state at day {day}",
  "clinical_question": "specific question to elicit 0-4 scoring data for this domain",
  "score_guide": {{
    "0": "patient response at score 0 — exactly matches expected state",
    "1": "patient response at score 1 — mild, within expected range",
    "2": "patient response at score 2 — above expected, needs monitoring",
    "3": "patient response at score 3 — significant concern, clinical review today",
    "4": "patient response at score 4 — emergency"
  }},
  "escalation_script_3": "exact words Sizor says if score is 3",
  "escalation_script_4": "exact words Sizor says if score is 4 — reference 999 or A&E if appropriate",
  "soap_instruction": "how to document this domain in NHS SOAP format"
}}"""
            try:
                import re as _re
                raw = await llm_client.complete(system_prompt, user_prompt)
                m = _re.search(r'\{.*\}', raw, re.DOTALL)
                playbook[day][domain] = json.loads(m.group()) if m else _make_template(domain)
            except Exception as exc:
                logger.warning("Playbook LLM failed day=%s domain=%s: %s", day, domain, exc)
                playbook[day][domain] = _make_template(domain)

    return playbook

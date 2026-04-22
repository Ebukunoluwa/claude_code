from __future__ import annotations


def _format_call_context(ctx: dict) -> str:
    """
    Convert the call-context dict from the backend into a prompt-ready text block.
    Includes per-domain score history compared against NICE benchmarks.
    """
    lines = ["════════════════════════════════════════════════════════════════",
             "PREVIOUS CALL HISTORY — use this to follow up on unresolved concerns",
             "════════════════════════════════════════════════════════════════"]

    summaries = ctx.get("call_summaries", [])
    for i, s in enumerate(summaries, 1):
        day_label = f"Day {s['day']}" if s.get("day") is not None else f"Call {i}"
        lines.append(f"\n[{day_label}]")
        if s.get("what_patient_reported"):
            lines.append(f"  Patient reported: {s['what_patient_reported']}")
        if s.get("assessment"):
            lines.append(f"  Assessment: {s['assessment']}")
        if s.get("plan"):
            lines.append(f"  Plan: {s['plan']}")

        # Generic scores (legacy / fallback)
        scores = s.get("scores", {})
        if scores:
            score_parts = []
            if "pain" in scores:
                score_parts.append(f"pain={scores['pain']}/10")
            if "mood" in scores:
                score_parts.append(f"mood={scores['mood']}/10")
            if "mobility" in scores:
                score_parts.append(f"mobility={scores['mobility']}/10")
            if "medication_adherent" in scores:
                score_parts.append(f"medication={'adherent' if scores['medication_adherent'] else 'NON-ADHERENT'}")
            if score_parts:
                lines.append(f"  Scores: {', '.join(score_parts)}")
            if scores.get("concerns_noted"):
                lines.append(f"  Concerns noted: {scores['concerns_noted']}")
            if scores.get("red_flags"):
                lines.append(f"  Red flags: {scores['red_flags']}")

        # Per-domain 0-4 scores with NICE benchmark comparison
        domain_scores = s.get("domain_scores", [])
        if domain_scores:
            lines.append("  Domain scores (0–4 scale):")
            for d in domain_scores:
                domain_label = d["domain"].replace("_", " ").title()
                score = d["score"]
                exp = d.get("expected")
                upper = d.get("upper_bound")
                nice_label = d.get("label", "")
                if upper is not None and score > upper:
                    flag = " ⚠ ABOVE EXPECTED — PROBE THIS"
                elif exp is not None and score <= exp:
                    flag = " ✓ on track"
                else:
                    flag = ""
                bench_str = f" (NICE expects ≤{upper}/4: {nice_label})" if upper is not None else ""
                lines.append(f"    {domain_label}: {score}/4{bench_str}{flag}")

    open_flags = ctx.get("open_flags", [])
    if open_flags:
        lines.append("\nOPEN CLINICAL FLAGS (unresolved — must follow up):")
        for f in open_flags:
            lines.append(f"  ⚠ [{f['severity'].upper()}] {f['type'].replace('_', ' ')}: {f['description']}")

    active_concerns = ctx.get("active_concerns", [])
    if active_concerns:
        lines.append("\nACTIVE CONCERNS FROM LONGITUDINAL RECORD:")
        for c in active_concerns:
            lines.append(f"  • {c}")

    lines.append("""
CONTINUITY INSTRUCTIONS:
- If the patient mentions anything related to the concerns above, acknowledge it and probe further.
- If an open flag exists, ask specifically about that symptom or issue during the call.
- For any domain marked ⚠ ABOVE EXPECTED: open with a specific follow-up, e.g. "Last time you mentioned your wound was still quite sore — how has that been since?"
- Do not read out clinical jargon or benchmark numbers — frame questions naturally and conversationally.
- Only bring up previous concerns if they are clinically relevant; do not make the patient feel surveilled.
""")
    return "\n".join(lines)


def _format_playbook(
    playbook: dict,
    pathway_label: str,
    day: int,
    red_flags: list[str],
    domain_priority: list[dict] | None = None,
    medications: list[str] | None = None,
) -> str:
    """
    Convert a single-day playbook dict into a structured call script section.

    domain_priority — ordered list from get_call_context:
      [{domain, last_score, last_day, expected, upper_bound, nice_label, above_expected, priority}]
      Flagged (above_expected) domains are listed first.
    """
    lines = [
        "════════════════════════════════════════════════════════════════",
        f"CLINICAL CALL SCRIPT — {pathway_label.upper()} — DAY {day} POST-DISCHARGE",
        "════════════════════════════════════════════════════════════════",
        "",
        f"IMPORTANT: The patient is on Day {day} post-discharge. Always say 'Day {day}'",
        "when referencing time — never say 'a few days ago', '2 weeks', or any vague timeframe.",
        "Use only the clinical_question and scoring guide from each domain below.",
        "",
        "SCORING: All domains use a 0–4 scale (0 = no problem, 4 = emergency).",
        "RULE: Score 3 on any domain → say escalation_script_3, flag for clinical review.",
        "RULE: Score 4 on any domain → say escalation_script_4, continue call.",
        "",
    ]

    # Red flags block
    if red_flags:
        lines.append("PATHWAY RED FLAGS — these ALWAYS trigger score 4 response:")
        for rf in red_flags:
            lines.append(f"  • {rf.replace('_', ' ')}")
        lines.append("")

    # Build priority index for inline context
    priority_index: dict[str, dict] = {}
    flagged_domains: list[str] = []
    if domain_priority:
        for p in domain_priority:
            priority_index[p["domain"]] = p
            if p.get("above_expected"):
                flagged_domains.append(p["domain"])

    # Priority callout — tell the agent which domains need extra attention today
    if flagged_domains:
        lines.append("⚠ PRIORITY DOMAINS — these were ABOVE NICE expected range on the last call:")
        for d in flagged_domains:
            p = priority_index[d]
            lines.append(
                f"  • {d.replace('_', ' ').title()}: scored {p['last_score']}/4 on Day {p['last_day']} "
                f"(NICE upper bound: {p['upper_bound']}/4 — \"{p['nice_label']}\")"
            )
        lines.append("  → Ask these domains first and probe more deeply if the score has not improved.")
        lines.append("")

    lines.append("PHASE 3 — CLINICAL ASSESSMENT")
    lines.append("─" * 64)

    # Order domains: priority (above_expected) first, then rest
    if domain_priority:
        ordered_domains = [p["domain"] for p in domain_priority if p["domain"] in playbook]
        # Append any playbook domains not in domain_priority (shouldn't happen but safe)
        for d in playbook:
            if d not in ordered_domains:
                ordered_domains.append(d)
    else:
        ordered_domains = list(playbook.keys())

    for i, domain in enumerate(ordered_domains, 1):
        script = playbook.get(domain)
        if not script:
            continue

        domain_label = domain.replace("_", " ").title()
        p = priority_index.get(domain, {})
        is_priority = p.get("above_expected", False)

        header = f"\nDomain {i}: {domain_label}"
        if is_priority:
            header += "  ⚠ PRIORITY"
        lines.append(header)

        # Inline previous score context for this domain
        if p.get("last_score") is not None:
            exp = p.get("expected")
            upper = p.get("upper_bound")
            nice_label = p.get("nice_label", "")
            trend_note = ""
            if is_priority:
                trend_note = " — ABOVE EXPECTED, probe why it hasn't improved"
            elif exp is not None and p["last_score"] <= exp:
                trend_note = " — on track"
            lines.append(
                f"  Previous score (Day {p['last_day']}): {p['last_score']}/4"
                f" | NICE expects ≤{upper}/4 at this stage: \"{nice_label}\"{trend_note}"
            )

        clinical = script.get("clinical_question", "")
        score_guide = script.get("score_guide", {})
        esc3 = script.get("escalation_script_3", "")
        esc4 = script.get("escalation_script_4", "")

        if clinical:
            lines.append(f'  Question: "{clinical}"')

        if score_guide:
            lines.append("  Scoring guide (listen for these responses):")
            for score, desc in sorted(score_guide.items()):
                lines.append(f"    {score}/4 — {desc}")

        if esc3:
            lines.append(f'  If score 3: "{esc3}"')
        if esc4:
            lines.append(f'  If score 4: "{esc4}"')

    lines += ["",
        "════════════════════════════════════════════════════════════════",
        "PHASE 4 — MEDICATION & ADHERENCE",
        "─" * 64,
    ]
    if medications:
        lines.append("The patient is prescribed the following medications:")
        for m in medications:
            lines.append(f"  • {m}")
        lines.append('Ask: "Are you managing to take all of your medications as prescribed — things like ' + ", ".join(medications[:3]) + ('…' if len(medications) > 3 else '') + '?"')
    else:
        lines.append('Ask: "Are you taking all your prescribed medications exactly as directed?"')
    lines += [
        "  If no → probe which medications and why, flag as AMBER or RED depending on criticality.",
        "",
        "PHASE 5 — MENTAL HEALTH SCREEN (PHQ-2)",
        "─" * 64,
        '  Q: "Over the past two weeks, have you been feeling down, depressed, or hopeless?"',
        '  Q: "Over the past two weeks, have you had little interest or pleasure in doing things?"',
        "",
    ]

    return "\n".join(lines)


def _nhs_spoken(nhs: str) -> str:
    """Convert NHS digits to spoken word form for prompt matching."""
    import re
    digits = re.sub(r"\D", "", nhs)
    words = {"0":"zero","1":"one","2":"two","3":"three","4":"four",
             "5":"five","6":"six","7":"seven","8":"eight","9":"nine"}
    return " ".join(words.get(d, d) for d in digits)


def _generic_clinical_section(day_in_recovery: int | None) -> str:
    """
    Return a generic clinical assessment script that adapts based on how many days
    post-discharge the patient is. Divides recovery into early (0-3), mid (4-14),
    and late (15+) phases with appropriate question emphasis.
    """
    if day_in_recovery is None:
        phase = "general"
    elif day_in_recovery <= 3:
        phase = "early"
    elif day_in_recovery <= 14:
        phase = "mid"
    else:
        phase = "late"

    if phase == "early":
        phase_note = (
            f"NOTE: This is Day {day_in_recovery} — the EARLY phase of recovery. "
            "Focus questions on immediate post-discharge concerns: wound/site care, "
            "acute pain, early mobility, and medication initiation. "
            "Patients at this stage are most at risk of complications."
        )
        q3 = '"Have you had a fever or felt unusually hot or shivery since leaving hospital?"'
        q4 = '"Have you noticed any unexpected bleeding, swelling, redness, or discharge from your wound or procedure site?"'
        q7 = '"Are you managing to get up and move around a little, even just walking to the bathroom?"'
    elif phase == "mid":
        phase_note = (
            f"NOTE: This is Day {day_in_recovery} — the MID phase of recovery. "
            "Focus on recovery progress: wound healing, building mobility, appetite return, "
            "and mood. Watch for signs of delayed complications or depression."
        )
        q3 = '"Have you had any fever, chills, or signs of infection — like increased redness or warmth around your wound?"'
        q4 = '"How is your wound or procedure site looking — is it healing as you\'d expect?"'
        q7 = '"How is your mobility progressing — are you able to do more each day compared to last week?"'
    else:
        phase_note = (
            f"NOTE: This is Day {day_in_recovery} — the LATE/ONGOING recovery phase. "
            "Focus on functional recovery, return to normal activities, ongoing symptoms, "
            "and readiness for any follow-up appointments."
        )
        q3 = '"Have you had any ongoing symptoms that concern you — such as persistent pain, fatigue, or breathlessness?"'
        q4 = '"Is your wound or procedure site fully healed, or are there any lingering issues?"'
        q7 = '"Are you getting back to your normal daily activities — things like cooking, walking, going outside?"'

    return f"""PHASE 3 — CLINICAL ASSESSMENT
{phase_note}
────────────────────────────────
Ask the following questions one at a time. Wait for a full response before asking the next.
  Q1: "Overall, how are you feeling since leaving hospital — on a scale from 1 to 10 where \
10 is perfectly well and 1 is very unwell?"
  Q2: "Are you experiencing any pain? If yes, how would you rate it from 0 to 10 where \
10 is the worst pain you can imagine?"
  Q3: {q3}
  Q4: {q4}

PHASE 4 — RECOVERY SPECIFICS
──────────────────────────────
  Q5: "Are you taking all of your prescribed medications exactly as directed?"
       If no — probe: which medications, and why? Flag as AMBER or RED depending on criticality.
  Q6: "Are you managing to eat and drink normally? How is your appetite?"
  Q7: {q7}

PHASE 5 — MENTAL HEALTH SCREEN (PHQ-2)
───────────────────────────────────────
  Q8: "Over the past two weeks, have you been feeling down, depressed, or hopeless?"
  Q9: "Over the past two weeks, have you had little interest or pleasure in doing things you usually enjoy?"
"""


def build_system_prompt(
    patient_name: str,
    nhs_number: str,
    next_appointment: str = "not yet scheduled",
    previous_context: dict | None = None,
    postcode: str = "",
) -> str:
    """
    Build the NHS/NICE-aligned system prompt for the check-in agent.

    When the patient has an active pathway with a generated playbook, phases 3 & 4
    are replaced with NICE-grounded domain-specific questions for that pathway and day.
    Falls back to the generic script when no playbook is available.
    """
    # Extract playbook and pathway data from context
    playbook = None
    pathway_label = None
    day_in_recovery = None
    discharge_date = None
    red_flags = []
    risk_flags = []
    domain_priority = []
    current_medications = []
    allergies = []

    if previous_context:
        playbook = previous_context.get("playbook")
        pathway_label = previous_context.get("pathway_label")
        day_in_recovery = previous_context.get("day_in_recovery")
        discharge_date = previous_context.get("discharge_date")
        red_flags = previous_context.get("red_flags", [])
        risk_flags = previous_context.get("risk_flags", [])
        domain_priority = previous_context.get("domain_priority", [])
        current_medications = previous_context.get("current_medications", [])
        allergies = previous_context.get("allergies", [])

    # ── Build patient context line ────────────────────────────────────────────
    if day_in_recovery is not None:
        recovery_line = f"\n  - Day in recovery   : Day {day_in_recovery} post-discharge"
        if pathway_label:
            recovery_line += f" ({pathway_label})"
    else:
        recovery_line = ""

    if discharge_date and discharge_date != "None":
        discharge_line = f"\n  - Discharge date    : {discharge_date}"
    else:
        discharge_line = ""

    # ── Build clinical assessment section ────────────────────────────────────
    if playbook and pathway_label and day_in_recovery is not None:
        clinical_section = _format_playbook(
            playbook=playbook,
            pathway_label=pathway_label,
            day=day_in_recovery,
            red_flags=red_flags,
            domain_priority=domain_priority or None,
            medications=current_medications or None,
        )
        pathway_context = (
            f"\nPATHWAY: {pathway_label} — Day {day_in_recovery} post-discharge\n"
        )
    else:
        # Generic fallback script — adapts questions to recovery phase
        clinical_section = _generic_clinical_section(day_in_recovery)
        pathway_context = ""
        if day_in_recovery is not None:
            pathway_context = f"\nRECOVERY PHASE: Day {day_in_recovery} post-discharge\n"

    # ── Build medication & allergy lines ─────────────────────────────────────
    meds_line = ""
    if current_medications:
        meds_line = "\n  - Medications      : " + ", ".join(current_medications)

    allergies_line = ""
    if allergies:
        allergies_line = "\n  - Allergies        : " + ", ".join(allergies) + "  ← NEVER suggest or mention these"

    risk_flags_line = ""
    if risk_flags:
        risk_flags_line = (
            "\n\nMONITORING RISK FLAGS (raised by clinical team — probe if patient mentions these):\n"
            + "\n".join(f"  • {rf}" for rf in risk_flags)
        )

    return f"""You are Sarah, an NHS automated post-discharge check-in agent calling on behalf \
of the NHS. You are professional, calm, empathetic, and speak in clear British English.

PATIENT DETAILS:
  - Patient name     : {patient_name}
  - NHS number       : {nhs_number}  (spoken: {_nhs_spoken(nhs_number)})
  - Next appointment : {next_appointment}{discharge_line}{recovery_line}{meds_line}{allergies_line}{pathway_context}{risk_flags_line}
════════════════════════════════════════════════════════════════
CALL SCRIPT — follow each phase in order
════════════════════════════════════════════════════════════════

PHASE 1 — IDENTITY VERIFICATION (MANDATORY)
──────────────────────────────────────────
1. Greet the patient: "Good [morning/afternoon], this is Sarah calling from the NHS \
post-discharge care line. Could I please speak with {patient_name}?"
2. Ask for their full name.
   - Accept any response that includes their first name OR last name (not case-sensitive).
3. Ask them to confirm their date of birth: "Could you please tell me your date of birth?"
   - Accept it verbally (e.g. "fourteenth of March nineteen fifty-eight") and convert to digits.
   - If DOB matches, say: "Thank you, I've been able to verify your identity."
   - If DOB does NOT match, say warmly: "No problem at all — not to worry. \
Could I take your postcode instead to verify your identity?" then wait for their postcode.
4. POSTCODE FALLBACK: If the date of birth failed, verify using postcode instead.
   - Accept it however they say it (e.g. "SW1A 2AA" or "S W one A two A A").
   - If postcode matches, say: "Thank you, I've been able to verify your identity."
   - If postcode also fails, apologise warmly and continue the call to help them as best you can.
   - Do NOT end the call just because verification failed.
5. Only proceed to Phase 2 once identity is confirmed (date of birth OR postcode).

PHASE 2 — CONSENT & RECORDING NOTICE
──────────────────────────────────────
"This call may be recorded for quality and clinical purposes. Do you consent to continue?"
If they decline, thank them and end the call politely.

{clinical_section}
PHASE 6 — OPEN-ENDED CHECK
────────────────────────────
  "Is there anything else you'd like to mention or any concerns about your recovery \
that we haven't covered?"

PHASE 7 — CLOSE
────────────────
  - Confirm next appointment: "Your next appointment is on {next_appointment}."
  - If no appointment: "Please contact your GP surgery to schedule a follow-up."
  - "Thank you for speaking with me today. Please call NHS 111 if you have any urgent \
concerns. Take care. Goodbye."

════════════════════════════════════════════════════════════════
URGENCY ESCALATION RULES (apply at all times, across all phases)
════════════════════════════════════════════════════════════════

RED — If the patient reports any of the following, respond with warmth and empathy,
gently signpost 999/NHS 111, then continue the call normally. Do NOT end the call.
Do NOT alarm them. Do NOT say "that sounds concerning" or "that's worrying".
  • Chest pain or tightness at rest
  • Severe difficulty breathing
  • Pain score 8+/10 (unbearable)
  • Active heavy bleeding
  • Thoughts of self-harm or suicide
  • Any pathway red flag listed above (if playbook is active)

HOW TO RESPOND (warm, not alarming):
Acknowledge empathetically — for example: "Oh I'm really sorry to hear that, \
that must be really hard for you."
Then gently say: "I just want to make sure you know — if things feel like they're \
getting worse or you're worried at any point, please don't hesitate to ring NHS 111 \
or 999, they're always there to help."
Then continue asking your remaining check-in questions as normal.
The call will be flagged automatically for clinical review.

AMBER — Continue the call but note concern. Do NOT use alarming language.
  • Fever above 38°C
  • Pain score 5–7/10
  • Not taking critical medications
  • Significant unexplained swelling or discharge
Say something caring like: "I'm sorry to hear that — I'll make sure your care team \
takes a look at that for you today."

════════════════════════════════════════════════════════════════
GENERAL GUIDANCE
════════════════════════════════════════════════════════════════
- Keep responses concise — this is a phone call, not a chat.
- Ask one question at a time. Wait for the answer before continuing.
- Never diagnose or offer medical advice — signpost only (NHS 111, GP, 999).
- If the patient is distressed, acknowledge their feelings before moving on.
- Maintain GDPR compliance: do not repeat NHS numbers aloud more than once.

{_format_call_context(previous_context) if previous_context else ""}"""

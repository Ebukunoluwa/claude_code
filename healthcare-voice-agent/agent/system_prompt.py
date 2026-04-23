from __future__ import annotations


def _socrates_probes(domain: str) -> list[str]:
    """
    Return a short list of SOCRATES-style follow-up probes for a given domain.
    These are only asked if the patient confirms a problem — never read as a list.
    The agent picks the 2-3 most relevant to what the patient just said.
    """
    d = domain.lower()

    # Pain variants
    if any(k in d for k in ("pain", "ache", "discomfort", "sore")):
        return [
            "Whereabouts exactly — can you point to the area or describe where it is?",
            "What does it feel like — sharp, dull, burning, throbbing, or something else?",
            "Is it there all the time, or does it come and go?",
            "Does it spread anywhere — like down your arm, into your back, or anywhere else?",
            "What makes it better, and what makes it worse?",
            "How is it affecting what you can do — is it stopping you from sleeping, moving, or doing things around the house?",
        ]

    # Breathlessness / chest
    if any(k in d for k in ("breath", "chest", "respir", "lung", "cough")):
        return [
            "When does it come on — at rest, or when you're moving around?",
            "How far can you walk before you notice it?",
            "Is it getting worse, staying the same, or improving since you left hospital?",
            "Any chest tightness, pain, or a cough alongside it?",
            "Are you able to hold a conversation comfortably, or do you need to stop and catch your breath?",
        ]

    # Wound / healing / infection
    if any(k in d for k in ("wound", "incis", "site", "heal", "infect", "dressing")):
        return [
            "How does it look — is the skin closed, and what colour is it around the area?",
            "Any redness, swelling, or warmth around it?",
            "Is there any discharge or fluid coming from it — and if so, what does it look like?",
            "Has the appearance changed at all since your last dressing check?",
            "Any fever or chills alongside it?",
        ]

    # Mobility / movement / walking
    if any(k in d for k in ("mobil", "walk", "move", "gait", "balance", "fall", "physio")):
        return [
            "What can you manage at the moment — are you able to get around the house on your own?",
            "Do you need any support — like a walking frame, stick, or someone to help you?",
            "Have you had any falls or near-misses since you got home?",
            "How does it compare to before you went into hospital — is it improving?",
            "Is anything stopping you from doing your exercises or moving more?",
        ]

    # Swelling / oedema / fluid
    if any(k in d for k in ("swell", "oedema", "fluid", "bloat", "ankl", "leg")):
        return [
            "Whereabouts is the swelling — one leg, both legs, your ankles, or somewhere else?",
            "Is it worse at a particular time of day — like in the evening?",
            "Is the skin tight or shiny over the swollen area?",
            "Has it changed since you left hospital — better, worse, or the same?",
            "Any redness, pain, or warmth in the swollen area?",
        ]

    # Appetite / eating / weight / nausea
    if any(k in d for k in ("appetit", "eat", "food", "nausea", "vomit", "weight", "nutrition")):
        return [
            "Are you managing to eat regular meals, or is food feeling difficult?",
            "Has your appetite changed compared to before you went into hospital?",
            "Any nausea or sickness — and if so, how often?",
            "Are you managing to drink enough — does your mouth feel dry?",
            "Have you noticed any weight loss or your clothes feeling looser?",
        ]

    # Bowels / bladder / urinary
    if any(k in d for k in ("bowel", "stool", "urine", "bladder", "catheter", "toilet", "constip", "diarr")):
        return [
            "Have you been able to use the toilet normally — any difficulties?",
            "Any pain, burning, or discomfort when you pass urine?",
            "Have your bowels opened since you left hospital?",
            "Any blood in your urine or stools?",
            "Any unexpected changes compared to what's normal for you?",
        ]

    # Mood / mental health / sleep / anxiety
    if any(k in d for k in ("mood", "mental", "anxiet", "depress", "sleep", "emotion", "worry", "stress", "psycho")):
        return [
            "How have you been feeling in yourself — in your mood and spirits?",
            "Is there anything that's been worrying you or weighing on your mind?",
            "How has your sleep been — are you managing to rest?",
            "Do you feel you have enough support around you at home?",
            "Are you enjoying any of the things you normally would, or has that been difficult?",
        ]

    # Fatigue / tiredness / energy
    if any(k in d for k in ("fatig", "tired", "energy", "exhaust", "weak")):
        return [
            "How would you describe your energy levels compared to before you went into hospital?",
            "Are you able to get through the day, or do you need to rest a lot?",
            "Is the tiredness improving, staying the same, or getting worse?",
            "Is it affecting your ability to eat, move around, or do things for yourself?",
        ]

    # Medication
    if any(k in d for k in ("medic", "tablet", "drug", "prescription", "adherence", "dose")):
        return [
            "Are you managing to take all your medications at the right times?",
            "Has anything made it difficult — side effects, forgetting, or anything else?",
            "Do you have enough of your medications at home, or are any running low?",
        ]

    # Generic fallback — covers any domain not matched above
    return [
        "Can you describe what you've been experiencing?",
        "When did you first notice it — was it before you left hospital or since you got home?",
        "Is it getting better, staying the same, or getting worse?",
        "How is it affecting your day-to-day life — what can't you do because of it?",
        "Is there anything that makes it better or worse?",
    ]


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
    Convert a single-day playbook dict into a SOCRATES-style call script.

    Questions are open-ended and conversational — no numeric rating scales asked aloud.
    Severity is inferred from what the patient describes, not from a self-reported number.
    The post-call pipeline extracts clinical scores from the transcript independently.

    domain_priority — ordered list from get_call_context:
      [{domain, last_score, last_day, expected, upper_bound, nice_label, above_expected, priority}]
    """
    # Build priority index
    priority_index: dict[str, dict] = {}
    flagged_domains: list[str] = []
    if domain_priority:
        for p in domain_priority:
            priority_index[p["domain"]] = p
            if p.get("above_expected"):
                flagged_domains.append(p["domain"])

    # Order domains: priority (above_expected) first, then rest
    if domain_priority:
        ordered_domains = [p["domain"] for p in domain_priority if p["domain"] in playbook]
        for d in playbook:
            if d not in ordered_domains:
                ordered_domains.append(d)
    else:
        ordered_domains = list(playbook.keys())

    total_domains = len(ordered_domains)

    lines = [
        "════════════════════════════════════════════════════════════════",
        f"CLINICAL CALL SCRIPT — {pathway_label.upper()} — DAY {day} POST-DISCHARGE",
        "════════════════════════════════════════════════════════════════",
        "",
        f"The patient is on Day {day} post-discharge from {pathway_label}.",
        "These questions are NICE-aligned for this specific pathway.",
        "",
        "HOW TO ASK QUESTIONS:",
        "  • Open-ended first — let them describe in their own words.",
        "  • Never ask 'rate it from 0 to 4' or give a scale — let the description reveal severity.",
        "  • If they confirm a problem, follow up with 2-3 probes from the list provided.",
        "  • Pick only the probes most relevant to what they've just said — don't read them all out.",
        "  • The most useful probe is always: 'How is that affecting your day-to-day life?'",
        "  • If two domains clearly overlap, combine into one conversation — cover both in one exchange.",
        "    You still need to have understood both topics from the response.",
        "",
    ]

    # ── Red flags ─────────────────────────────────────────────────────────────
    if red_flags:
        lines += [
            "RED FLAGS — listen for these throughout the ENTIRE call.",
            "If the patient mentions ANY of the following, respond immediately:",
        ]
        for rf in red_flags:
            lines.append(f"  🔴 {rf.replace('_', ' ')}")
        lines += [
            "  → Say warmly but clearly: \"I'm really glad you told me that. Please call 999 right",
            "    away — don't wait. I'm making sure your care team knows immediately. Take care.\"",
            "",
        ]

    # ── Priority domains ──────────────────────────────────────────────────────
    if flagged_domains:
        lines.append("⚠ AREAS OF CONCERN from last call — explore these more carefully today:")
        for d in flagged_domains:
            p = priority_index[d]
            lines.append(
                f"  • {d.replace('_', ' ').title()}: was concerning on Day {p['last_day']} "
                f"(NICE target: \"{p['nice_label']}\" — not yet met)"
            )
        lines.append("  Start here. If still a problem, probe why it hasn't improved.")
        lines.append("")

    lines += [
        "SEVERITY INFERENCE (internal guide — do NOT say these to the patient):",
        "  Reassuring: 'much better', 'fine', 'barely notice it', 'back to normal'",
        "  Monitoring needed: 'still there', 'not great', 'managing', 'comes and goes'",
        "  Clinical concern: 'worse than before', 'really struggling', 'can't sleep because of it'",
        "  Urgent: 'unbearable', 'can't move', 'scares me', 'getting worse fast', 'can't breathe'",
        "  → Use these cues to decide whether to acknowledge and move on, or escalate.",
        "",
        "PHASE 3 — CLINICAL ASSESSMENT",
        "─" * 64,
        "Cover ALL domains below before closing. One at a time. Wait for a full answer.",
        "",
    ]

    for i, domain in enumerate(ordered_domains, 1):
        script = playbook.get(domain)
        if not script:
            continue

        domain_label = domain.replace("_", " ").title()
        p = priority_index.get(domain, {})
        is_priority = p.get("above_expected", False)

        header = f"[{i}/{total_domains}] {domain_label}"
        if is_priority:
            header += "  ⚠ was a concern last time"
        lines.append(header)

        # Previous context — tell agent what to expect
        if p.get("last_score") is not None:
            nice_label = p.get("nice_label", "")
            if is_priority:
                lines.append(
                    f"  Last call: still above NICE target (\"{nice_label}\") — check if improved."
                )
            else:
                lines.append(f"  Last call: on track (\"{nice_label}\").")

        # Opening question from NICE playbook
        clinical = script.get("clinical_question", "")
        if clinical:
            # Strip any existing numeric scale language from the playbook question
            import re as _re
            clinical = _re.sub(
                r'\bon\s+a\s+scale\s+of\s+\d[^.]*\.?', '', clinical, flags=_re.IGNORECASE
            ).strip().rstrip(",").strip()
            lines.append(f'  Open with: "{clinical}"')

        # SOCRATES follow-up probes for this domain
        probes = _socrates_probes(domain)
        if probes:
            lines.append("  If they mention a problem, explore with (pick the 2-3 most relevant):")
            for probe in probes:
                lines.append(f'    – "{probe}"')

        # Concern indicators derived from score guide
        score_guide = script.get("score_guide", {})
        concern_phrases = []
        urgent_phrases = []
        for score_val, desc in sorted(score_guide.items()):
            try:
                sv = int(score_val)
            except (ValueError, TypeError):
                continue
            if sv >= 4:
                urgent_phrases.append(desc)
            elif sv >= 3:
                concern_phrases.append(desc)

        if urgent_phrases:
            lines.append(f"  Escalate immediately if they describe: {'; '.join(urgent_phrases)}")
        if concern_phrases:
            lines.append(f"  Flag for review if they describe: {'; '.join(concern_phrases)}")

        # Escalation scripts
        esc3 = script.get("escalation_script_3", "")
        esc4 = script.get("escalation_script_4", "")
        if esc3:
            lines.append(f'  If concerning → say: "{esc3}"')
        if esc4:
            lines.append(f'  If urgent → say: "{esc4}"')

        lines.append("")

    # ── Medication adherence ──────────────────────────────────────────────────
    lines += [
        "════════════════════════════════════════════════════════════════",
        "PHASE 4 — MEDICATION ADHERENCE (mandatory)",
        "─" * 64,
    ]
    if medications:
        lines.append("Patient is prescribed:")
        for m in medications:
            lines.append(f"  • {m}")
        med_example = medications[0] if medications else "your medication"
        lines += [
            f'  Ask: "Are you managing to take all your medications regularly — things like {med_example}?"',
            '  If any missed → "Which one — and has anything made it difficult to take it?"',
            "  Flag missed critical medication as RED. Non-critical as AMBER.",
        ]
    else:
        lines += [
            '  Ask: "Are you managing to take all your prescribed medications as directed?"',
            '  If no → "Which ones — and what\'s made it difficult?"',
            "  Flag missed critical medication as RED. Non-critical as AMBER.",
        ]
    lines.append("")

    # ── Mental health screen ──────────────────────────────────────────────────
    lines += [
        "PHASE 5 — MENTAL HEALTH & WELLBEING (mandatory)",
        "─" * 64,
        '  Ask: "And how have you been feeling in yourself — your mood and spirits — since you got home?"',
        "  If they express low mood, worry, or distress, gently follow up:",
        '    – "Have you been finding it hard to enjoy things you normally would?"',
        '    – "Is there anything that\'s been weighing on your mind?"',
        '    – "Do you feel you have enough support around you at home?"',
        "  Acknowledge warmly. Flag AMBER if mood is low. Flag RED if any mention of self-harm.",
        "",
        "════════════════════════════════════════════════════════════════",
        "BEFORE MOVING TO THE CLOSE — confirm you have explored:",
    ]
    for i, domain in enumerate(ordered_domains, 1):
        lines.append(f"  [{i}] {domain.replace('_', ' ').title()}")
    lines += [
        "  [M] Medications",
        "  [W] Mood and wellbeing",
        "Only once all areas have been explored, move to Phase 6.",
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
    Generic SOCRATES-style clinical assessment — used when no specific NICE pathway is registered.
    Adapts question emphasis based on recovery phase.
    """
    if day_in_recovery is None or day_in_recovery > 14:
        phase = "late"
    elif day_in_recovery <= 3:
        phase = "early"
    else:
        phase = "mid"

    if phase == "early":
        phase_note = (
            f"Day {day_in_recovery} — EARLY recovery. "
            "Prioritise: acute pain, wound/site, infection signs, medication start, mobility."
        )
        wound_q = "Have you had a look at your wound or procedure site — how is it looking and feeling?"
        mobility_q = "Are you managing to get up and move around a little — even short walks to the bathroom?"
        extra_q = "Have you had any fever, chills, or felt unusually hot or shivery?"
    elif phase == "mid":
        phase_note = (
            f"Day {day_in_recovery} — MID recovery. "
            "Prioritise: wound healing progress, mobility improvement, appetite, mood."
        )
        wound_q = "How is your wound or procedure site looking — is it healing as you'd expect?"
        mobility_q = "How is your mobility coming along — are you able to do a bit more each day?"
        extra_q = "Any signs of infection — redness, warmth, discharge, or swelling around the wound?"
    else:
        phase_note = (
            f"Day {day_in_recovery} — LATE recovery. "
            "Prioritise: return to normal activities, lingering symptoms, follow-up readiness."
        )
        wound_q = "Is your wound or procedure site fully healed, or are there any lingering issues?"
        mobility_q = "Are you getting back to your normal activities — things like cooking, going outside, getting around?"
        extra_q = "Any ongoing symptoms that are concerning you — pain, breathlessness, fatigue?"

    return f"""PHASE 3 — CLINICAL ASSESSMENT (ALL 6 AREAS MANDATORY)
{phase_note}
────────────────────────────────────────────────────────────────
HOW TO ASK: Open-ended first. Let them describe in their own words.
Never ask for a number — let what they say reveal the severity.
If they mention a problem, follow up with 2-3 relevant probes before moving on.
The most useful follow-up is always: "How is that affecting your day-to-day life?"

SEVERITY CUES (internal guide — do not say to patient):
  Reassuring: "fine", "getting better", "back to normal", "barely notice it"
  Monitor: "still there", "not great", "some days", "a bit sore"
  Concern: "really struggling", "worse than before", "can't sleep because of it"
  Urgent: "unbearable", "can't move", "can't breathe", "getting worse fast"

[1/6] OVERALL WELLBEING
  Open with: "Overall, how have you been feeling since leaving hospital?"
  Probes if they mention a problem:
    – "Is that different to how you felt when you were first discharged — better, worse, or the same?"
    – "What's the main thing making it difficult?"
    – "How is it affecting your day — what can't you do because of it?"

[2/6] PAIN OR DISCOMFORT
  Open with: "Have you had any pain or discomfort since you got home?"
  Probes:
    – "Whereabouts exactly — can you point to it or describe where it is?"
    – "What does it feel like — sharp, dull, aching, burning, or something else?"
    – "Is it there all the time or does it come and go?"
    – "What makes it better or worse?"
    – "How is it affecting your sleep and your ability to move around?"
  Escalate if: unbearable, sudden severe chest pain, pain spreading to arm or jaw.

[3/6] WOUND / PROCEDURE SITE
  Open with: "{wound_q}"
  Probes:
    – "Any redness, swelling, or warmth around it?"
    – "Any discharge or fluid — and if so, what does it look like?"
    – "Any fever or chills alongside it?"
  Escalate if: pus, spreading redness, high fever, wound opened up.

[4/6] MOBILITY & DAILY ACTIVITIES
  Open with: "{mobility_q}"
  Probes:
    – "What are you finding difficult that you'd normally do easily?"
    – "Do you need any support to get around — a frame, a stick, or someone helping?"
    – "Any falls or near-misses since you got home?"
  Flag if: unable to get out of bed, housebound unexpectedly, new falls.

[5/6] {extra_q[:extra_q.index('—')].strip() if '—' in extra_q else 'ADDITIONAL CHECKS'}
  Open with: "{extra_q}"
  Probes as needed based on their response.

PHASE 4 — MEDICATION & APPETITE (MANDATORY)
────────────────────────────────────────────
  Ask: "Are you managing to take all your medications as prescribed?"
  If no → "Which ones, and what's made it difficult?"
  Flag missed critical medication RED. Non-critical AMBER.

  Ask: "How is your appetite — are you managing to eat and drink normally?"
  If poor → "How long has your appetite been off? Any nausea or sickness?"
  Flag poor appetite persisting >3 days as AMBER.

PHASE 5 — MOOD & WELLBEING (MANDATORY)
────────────────────────────────────────
  Ask: "And how have you been feeling in yourself — your mood and spirits since you got home?"
  If low mood → follow up:
    – "Have you been finding it hard to enjoy things you normally would?"
    – "Is anything weighing on your mind?"
    – "Do you feel you have enough support around you?"
  Flag AMBER if persistent low mood. Flag RED if any mention of self-harm.

COMPLETION CHECK — all 6 areas must be explored before moving to the close:
  [1] Overall wellbeing  [2] Pain  [3] Wound/site  [4] Mobility  [5] Additional checks
  [6] Medications + Appetite  [W] Mood and wellbeing
"""


def _domain_template(domain: str) -> dict:
    """
    Minimal inline template used as a last-resort safety net when no
    LLM-generated playbook has arrived yet.  Identical structure to the
    backend _make_template so _format_playbook renders it correctly.
    """
    label = domain.replace("_", " ").replace("-", " ")
    return {
        "clinical_question": (
            f"On a scale of 0 to 4 — where 0 is no problem at all and 4 is a medical emergency — "
            f"how would you rate your {label} today?"
        ),
        "score_guide": {
            "0": "No problem — fully resolved or not present",
            "1": "Mild — expected at this stage of recovery",
            "2": "Moderate — more than expected, monitoring needed",
            "3": "Significant — needs clinical review today",
            "4": "Severe or emergency — needs 999 or immediate help",
        },
        "escalation_script_3": (
            "I want to make sure your care team is aware of that. "
            "I'll flag this for a clinician to follow up with you today."
        ),
        "escalation_script_4": (
            "I'm very concerned about what you've described. "
            "Please call 999 immediately or go to your nearest A&E. "
            "I'm alerting your care team right now."
        ),
    }


def build_system_prompt(
    patient_name: str,
    nhs_number: str,
    next_appointment: str = "not yet scheduled",
    previous_context: dict | None = None,
    postcode: str = "",
    is_continuation: bool = False,
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
    # When a clinical pathway is registered the generic script MUST NOT fire.
    # The backend guarantees a non-null playbook via _make_template, but as a
    # defence-in-depth layer we also synthesise templates here if the playbook
    # is somehow still empty (e.g. network/cache race on a very fast Day-1 call).
    if pathway_label and day_in_recovery is not None:
        effective_playbook = playbook or {}
        if not effective_playbook:
            if domain_priority:
                # Rebuild from the domain_priority list sent by the backend
                effective_playbook = {
                    p["domain"]: _domain_template(p["domain"])
                    for p in domain_priority
                }
            else:
                # Absolute last resort — a single recovery-progress question
                effective_playbook = {"recovery_progress": _domain_template("recovery progress")}

        clinical_section = _format_playbook(
            playbook=effective_playbook,
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
        # Generic script only for patients with no registered pathway at all
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

    # Extract first name for the greeting (never read out the full name)
    _name_parts = patient_name.strip().split()
    _first_name = _name_parts[0] if _name_parts else "there"

    _phase_1_2 = (
        f"""PHASE 1 — CONTINUATION (call reconnected after cut-off)
──────────────────────────────────────────
This call reconnected after an earlier call to {_first_name} was cut off unexpectedly.

Do NOT re-do the full introduction. Say something warm and brief:
"Hi {_first_name}, it's Sarah again — I'm so sorry we got cut off earlier. \
Are you okay to carry on for a moment?"

If the previous call history below shows identity was already verified: \
skip verification entirely and go straight to the clinical questions.
If there is no prior call history or it's unclear: quickly confirm their surname \
("Just to double-check I have the right person — could you tell me your surname?"), \
then proceed straight to the clinical questions.

Do NOT repeat the consent notice. Do NOT re-introduce yourself at length."""
        if is_continuation else
        f"""PHASE 1 — IDENTITY VERIFICATION (MANDATORY)
──────────────────────────────────────────
IMPORTANT: Never say the patient's full name aloud. Use first name only for the greeting.

1. Greet: "Good [morning/afternoon], this is Sarah calling from the NHS \\
post-discharge care line. Am I speaking with {_first_name}?"
   - If yes (or they confirm it's them): proceed to step 2.
   - If no / they want to fetch them: ask them to get {_first_name} and wait.
2. Confirm surname: "Could you just confirm your surname for me?"
   - Accept any response matching their last name (not case-sensitive).
3. Ask for date of birth: "Thank you. And could you confirm your date of birth?"
   - Accept it verbally (e.g. "fourteenth of March nineteen fifty-eight") and convert to digits.
   - If DOB matches, say: "Perfect, thank you — I've been able to verify your identity."
   - If DOB does NOT match, say warmly: "No problem at all — not to worry. \\
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
If they decline, thank them and end the call politely."""
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

{_phase_1_2}

{clinical_section}
PHASE 6 — OPEN-ENDED CHECK
────────────────────────────
Only reach this phase once ALL clinical domains, medication adherence, and the mental
health screen have been completed and scored.
  "Is there anything else you'd like to mention or any concerns about your recovery \
that we haven't covered?"
Listen carefully — if they raise something new that maps to a clinical domain you hadn't
covered yet, address it now before closing.

PHASE 7 — CLOSE
────────────────
  - Confirm next appointment: "Your next appointment is on {next_appointment}."
  - If no appointment: "Please contact your GP surgery to schedule a follow-up if you haven't already."
  - "Thank you so much for speaking with me today — your answers really help your care team. \
Please don't hesitate to call NHS 111 if anything concerns you. Take care. Goodbye."

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

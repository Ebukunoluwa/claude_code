"""Phase 4 coverage-enforcement helpers.

Build-time filtering of the Phase 3 Required Questions and Red Flag
Probes registries for a given (opcs_code, call_day). Phase 4 does NOT
make clinical judgements about the content — it consumes the Phase 3
manifests verbatim. See PHASE_4_PLAN.md §Constants for the one
CLINICAL_REVIEW_NEEDED constant (the 80% coverage threshold).
"""
from __future__ import annotations

import logging

from .models import RedFlagProbe, RequiredQuestion
from .pathways import PATHWAYS, RED_FLAG_PROBES, REQUIRED_QUESTIONS


logger = logging.getLogger(__name__)


def build_required_questions(
    opcs_code: str | None, call_day: int,
) -> list[RequiredQuestion]:
    """Filter the Phase 3 Required Questions manifest for a specific
    pathway + day. Returns only questions whose day_ranges include the
    given call_day.

    Day-band match: any (start, end) tuple in q.day_ranges where
    start <= call_day <= end.

    Returns [] for unknown opcs_code, for the Z03_MH scaffold, or when
    no questions match the day-band (valid in late calls past the
    manifest's day coverage).
    """
    if opcs_code is None:
        return []
    questions = REQUIRED_QUESTIONS.get(opcs_code)
    if questions is None:
        logger.warning(
            "build_required_questions: unknown opcs_code=%r, returning []",
            opcs_code,
        )
        return []
    return [
        q for q in questions
        if any(start <= call_day <= end for (start, end) in q.day_ranges)
    ]


def build_red_flag_probes(opcs_code: str | None) -> list[RedFlagProbe]:
    """Return all Red Flag Probes for the pathway. Red flags have no
    day-band filter — they apply on every call regardless of day.

    Returns [] for unknown opcs_code or the Z03_MH scaffold. Order
    matches insertion order of the per-pathway RED_FLAG_PROBES dict
    (Python 3.7+ guarantees dict order).
    """
    if opcs_code is None:
        return []
    probes = RED_FLAG_PROBES.get(opcs_code)
    if probes is None:
        logger.warning(
            "build_red_flag_probes: unknown opcs_code=%r, returning []",
            opcs_code,
        )
        return []
    return list(probes.values())


def get_mandatory_call_checklist(opcs_code: str | None, call_day: int) -> str:
    """Return a deterministic, system-prompt-ready checklist string for
    a given (opcs_code, call_day). Phase 6 will embed this in the prompt
    builder; Phase 4 builds the structure so the integration point is
    ready.

    Determinism: same (opcs_code, call_day) inputs produce a byte-equal
    string across calls. Item order follows the manifest's insertion
    order (author intent preserved — typically domain-grouped).

    Unknown / None opcs_code returns a stub that signals no checklist is
    available. Z03_MH scaffold returns a distinct stub pointing at the
    CONTENT_BLOCK sentinel — the voice agent must not call Z03_MH.
    """
    if opcs_code is None:
        return (
            "## MANDATORY CALL CHECKLIST — unavailable\n\n"
            "No pathway was identified for this patient. Escalate to a "
            "clinician before proceeding with the call.\n"
        )

    playbook = PATHWAYS.get(opcs_code)
    if playbook is None:
        logger.warning(
            "get_mandatory_call_checklist: unknown opcs_code=%r",
            opcs_code,
        )
        return (
            f"## MANDATORY CALL CHECKLIST — unknown pathway {opcs_code!r}\n\n"
            "No checklist is available for this pathway code. Escalate "
            "to a clinician before proceeding.\n"
        )

    # Z03_MH scaffold has empty manifests and is explicitly blocked from
    # voice-agent consumption. Return a distinct stub rather than an
    # empty-looking checklist that could be mistaken for "nothing to ask".
    if opcs_code == "Z03_MH":
        return (
            f"## MANDATORY CALL CHECKLIST — {playbook.label} (Day {call_day})\n\n"
            "CONTENT BLOCKED: the mental-health cluster scaffold has no "
            "signed-off patient-facing content. The voice agent MUST NOT "
            "initiate calls on this pathway. Escalate to the mental-health "
            "clinician lead for sign-off before enabling.\n"
        )

    required_qs = build_required_questions(opcs_code, call_day)
    red_flag_probes = build_red_flag_probes(opcs_code)

    lines: list[str] = [
        f"## MANDATORY CALL CHECKLIST — {playbook.label} (Day {call_day})",
        "",
        "You MUST cover every item in the Required Questions list before",
        "ending this call. If the patient explicitly declines to discuss",
        "an item, record their decline and move on. Do not silently skip.",
        "",
        "### Required Questions (ask each in this call)",
    ]
    if required_qs:
        for q in required_qs:
            lines.append(f"- [{q.domain}] {q.question_text}")
    else:
        lines.append(
            f"_(No required questions in the Phase 3 manifest cover day "
            f"{call_day} for this pathway — check with the clinical lead "
            f"whether the monitoring window has ended.)_"
        )

    lines.extend([
        "",
        "### Red Flag Probes (MUST ASK EVERY CALL regardless of other content)",
        "",
        "Each is a single observation. All must be asked. If a probe fires",
        "positive, follow the escalation tier immediately.",
        "",
    ])
    if red_flag_probes:
        for p in red_flag_probes:
            lines.append(f"- [{p.flag_code}] {p.patient_facing_question}")
            lines.append(
                f"  Escalation if positive: {p.follow_up_escalation.value}"
            )
    else:
        lines.append(
            "_(No red flag probes registered for this pathway.)_"
        )

    # Trailing newline for clean concatenation into system prompts.
    return "\n".join(lines) + "\n"

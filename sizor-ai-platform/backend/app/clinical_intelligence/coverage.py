"""Phase 4 coverage-enforcement helpers.

Build-time filtering of the Phase 3 Required Questions and Red Flag
Probes registries for a given (opcs_code, call_day). Phase 4 does NOT
make clinical judgements about the content — it consumes the Phase 3
manifests verbatim. See PHASE_4_PLAN.md §Constants for the one
CLINICAL_REVIEW_NEEDED constant (the 80% coverage threshold).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import CoverageReport, RedFlagProbe, RequiredQuestion
from .pathways import PATHWAYS, RED_FLAG_PROBES, REQUIRED_QUESTIONS

if TYPE_CHECKING:
    from ..services.llm_client import LLMClient


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


# ======================================================================
# LLM-based coverage classifier (D4)
# ======================================================================

_COVERAGE_SYSTEM_PROMPT_HEADER = """\
You are a clinical audit reviewer. A post-discharge phone call was conducted.
Your job is to determine, for each Required Question and each Red Flag Probe
listed below, whether the voice agent covered the topic during the call and
how the patient responded.

Definitions:
  - asked: the agent raised the topic during the call, in any wording. A
    paraphrased question still counts as asked.
  - declined: the patient explicitly said they didn't want to discuss the
    topic. This STILL counts as asked — the agent did raise it — but is
    logged separately.
  - silently_skipped: the agent never raised the topic in the transcript.
    This is the failure case Phase 4 is designed to detect.
  - positive: for a red flag probe only — the patient reported having the
    symptom the probe asks about (the probe fired positive).

For SOCRATES domains: list any domain where the patient described an
above-expected symptom (triggered). List any domain where the agent then
ran SOCRATES-style follow-up probing (completed). Completed is a subset
of triggered.

Return ONLY valid JSON with these keys:
  required_questions_asked: list of question_text strings the agent raised
  required_questions_patient_declined: subset of asked where patient declined
  red_flag_probes_asked: list of flag_code strings the agent raised
  red_flag_probes_positive: subset of asked where patient reported symptom
  socrates_probes_triggered: list of domain strings that warranted follow-up
  socrates_probes_completed: subset of triggered where follow-up was done

Use the EXACT strings from the lists below. Do not paraphrase them in your
output. The strings are identifiers, not instructions for you to rewrite.

No prose, no explanation — JSON only.
"""


def _build_coverage_system_prompt(
    required_qs: list[RequiredQuestion],
    red_flag_probes: list[RedFlagProbe],
    opcs_code: str,
    call_day: int,
) -> str:
    """Assemble the system prompt for the coverage classifier. Deterministic
    for the same inputs — order follows the manifest."""
    pathway_label = PATHWAYS[opcs_code].label if opcs_code in PATHWAYS else opcs_code
    parts = [
        _COVERAGE_SYSTEM_PROMPT_HEADER,
        f"\n\nCALL CONTEXT: {pathway_label} ({opcs_code}), Day {call_day} post-discharge.\n",
        "\nREQUIRED QUESTIONS EXPECTED:\n",
    ]
    if required_qs:
        for q in required_qs:
            parts.append(f"  [{q.domain}] {q.question_text}\n")
    else:
        parts.append("  (none for this day)\n")
    parts.append("\nRED FLAG PROBES EXPECTED:\n")
    if red_flag_probes:
        for p in red_flag_probes:
            parts.append(f"  [{p.flag_code}] {p.patient_facing_question}\n")
    else:
        parts.append("  (none for this pathway)\n")
    return "".join(parts)


def _parse_classifier_json(text: str) -> dict:
    """Parse LLM JSON response, tolerant of markdown fences and surrounding
    prose. Same strategy as services/post_call_pipeline._parse_json but
    local to avoid a circular import between clinical_intelligence and
    services."""
    import json
    import re
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


async def validate_call_coverage(
    transcript: str,
    opcs_code: str | None,
    call_day: int,
    llm_client: "LLMClient | None" = None,
) -> CoverageReport:
    """Post-call coverage classifier.

    Reads the transcript, asks an LLM to determine which Required Questions
    and Red Flag Probes were covered / asked / positive, and returns a
    CoverageReport with lists populated and coverage_percentage computed
    in Python (not inferred by the LLM).

    Arguments:
      transcript: the raw call transcript. May be empty.
      opcs_code: the patient's active pathway OPCS code. May be None.
      call_day: day in recovery at time of call.
      llm_client: injectable LLMClient instance. Tests pass a stub;
                  production instantiates fresh each call (matching
                  the extract_clinical_scores pattern).

    Failure behaviour:
      - opcs_code None → empty expected lists, coverage_percentage None.
      - Pathway with no RQs and no RFPs (Z03_MH scaffold) → coverage 100
        (nothing to cover, nothing missed).
      - LLM call raises or returns unparseable JSON → coverage 0,
        incomplete_items populated with every expected item, raw response
        stored in raw_classifier_output downstream.

    Never raises. Always returns a valid CoverageReport so the pipeline
    can persist it regardless of classifier outcome.
    """
    required_qs = build_required_questions(opcs_code, call_day)
    red_flag_probes = build_red_flag_probes(opcs_code)

    rqs_expected = [q.question_text for q in required_qs]
    rfps_expected = [p.flag_code for p in red_flag_probes]

    if opcs_code is None:
        return CoverageReport(
            required_questions_expected=rqs_expected,
            red_flag_probes_expected=rfps_expected,
            coverage_percentage=None,
        )

    # Z03_MH scaffold or end-of-window call: nothing to classify.
    if not required_qs and not red_flag_probes:
        return CoverageReport(
            required_questions_expected=rqs_expected,
            red_flag_probes_expected=rfps_expected,
            coverage_percentage=100.0,
        )

    # Build prompt + call LLM.
    system = _build_coverage_system_prompt(
        required_qs, red_flag_probes, opcs_code, call_day,
    )
    user = f"TRANSCRIPT:\n{transcript}"

    if llm_client is None:
        from ..services.llm_client import LLMClient
        llm_client = LLMClient()

    try:
        resp = await llm_client.complete(system, user)
        parsed = _parse_classifier_json(resp)
    except Exception as exc:
        logger.error(
            "Coverage classifier LLM call failed for opcs=%s day=%s: %s",
            opcs_code, call_day, exc, exc_info=True,
        )
        parsed = {}

    # LLM returned nothing usable → conservative report: everything
    # incomplete, 0% coverage, caller can see the raw response in logs.
    if not parsed:
        logger.warning(
            "Coverage classifier returned unparseable JSON for opcs=%s day=%s",
            opcs_code, call_day,
        )
        return CoverageReport(
            required_questions_expected=rqs_expected,
            red_flag_probes_expected=rfps_expected,
            coverage_percentage=0.0,
            incomplete_items=list(rqs_expected) + list(rfps_expected),
        )

    # Whitelist classifier output against expected lists — LLM may hallucinate
    # items or paraphrase despite the prompt instruction. Only accept exact
    # matches to expected strings so coverage_percentage is trustworthy.
    rqs_asked_raw = parsed.get("required_questions_asked") or []
    rqs_asked = [q for q in rqs_asked_raw if q in rqs_expected]
    rqs_declined_raw = parsed.get("required_questions_patient_declined") or []
    rqs_declined = [q for q in rqs_declined_raw if q in rqs_asked]

    rfps_asked_raw = parsed.get("red_flag_probes_asked") or []
    rfps_asked = [f for f in rfps_asked_raw if f in rfps_expected]
    rfps_positive_raw = parsed.get("red_flag_probes_positive") or []
    rfps_positive = [f for f in rfps_positive_raw if f in rfps_asked]

    socrates_triggered = list(parsed.get("socrates_probes_triggered") or [])
    socrates_completed_raw = parsed.get("socrates_probes_completed") or []
    socrates_completed = [
        d for d in socrates_completed_raw if d in socrates_triggered
    ]

    # Coverage percentage: asked / expected × 100. Computed in Python,
    # not by the LLM.
    expected_total = len(rqs_expected) + len(rfps_expected)
    asked_total = len(rqs_asked) + len(rfps_asked)
    coverage_pct = (
        round(100.0 * asked_total / expected_total, 1)
        if expected_total > 0 else 100.0
    )

    # Incomplete items: expected minus asked, union of RQs + RFPs.
    incomplete = (
        [q for q in rqs_expected if q not in rqs_asked]
        + [f for f in rfps_expected if f not in rfps_asked]
    )

    return CoverageReport(
        required_questions_expected=rqs_expected,
        required_questions_asked=rqs_asked,
        required_questions_patient_declined=rqs_declined,
        red_flag_probes_expected=rfps_expected,
        red_flag_probes_asked=rfps_asked,
        red_flag_probes_positive=rfps_positive,
        socrates_probes_triggered=socrates_triggered,
        socrates_probes_completed=socrates_completed,
        coverage_percentage=coverage_pct,
        incomplete_items=incomplete,
        raw_classifier_output=parsed,
    )

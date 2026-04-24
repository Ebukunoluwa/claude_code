"""Phase 4 D4 — validate_call_coverage LLM classifier.

Five golden-transcript scenarios with a stubbed LLMClient. No live LLM
calls — the classifier's deterministic wrapping around a mock response
is what we test.

Uses W40 (Total Knee Replacement) day-7 as the fixture pathway because
its manifest is well-established and fresh in the Phase 3 merge.
Day 7 returns 6 RQs + 12 RFPs for a total of 18 expected items.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from app.clinical_intelligence.coverage import (
    build_red_flag_probes,
    build_required_questions,
    validate_call_coverage,
)


class _StubLLM:
    """Minimal async stand-in for LLMClient. Tests configure what
    complete() should return before invoking the classifier."""

    def __init__(self, response: str):
        self._response = response
        self.last_system: str | None = None
        self.last_user: str | None = None

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system = system_prompt
        self.last_user = user_prompt
        return self._response


def _run(coro):
    return asyncio.run(coro)


def _w40_day7_expected():
    """Convenience: return the expected RQ question_texts and RFP
    flag_codes for W40 day 7."""
    rqs = build_required_questions("W40", 7)
    rfps = build_red_flag_probes("W40")
    return (
        [q.question_text for q in rqs],
        [p.flag_code for p in rfps],
    )


# ─── Scenario 1: perfect call ──────────────────────────────────────────

def test_perfect_call_all_items_covered():
    """Classifier marks every expected RQ and RFP as asked, none
    positive, none declined. Coverage = 100%."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    stub_response = json.dumps({
        "required_questions_asked": rqs_expected,
        "required_questions_patient_declined": [],
        "red_flag_probes_asked": rfps_expected,
        "red_flag_probes_positive": [],
        "socrates_probes_triggered": [],
        "socrates_probes_completed": [],
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated full call transcript",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    assert report.coverage_percentage == 100.0
    assert report.required_questions_asked == rqs_expected
    assert report.red_flag_probes_asked == rfps_expected
    assert report.required_questions_patient_declined == []
    assert report.red_flag_probes_positive == []
    assert report.incomplete_items == []


# ─── Scenario 2: incomplete call (silent skip of some RQs) ─────────────

def test_incomplete_call_silent_skip():
    """Two of six RQs silently skipped. Coverage drops. Missing items
    show up in incomplete_items. The skipped RQs do NOT appear in
    required_questions_asked."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    # Pretend the agent skipped the last two RQs.
    rqs_asked_partial = rqs_expected[:-2]

    stub_response = json.dumps({
        "required_questions_asked": rqs_asked_partial,
        "red_flag_probes_asked": rfps_expected,
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated partial call transcript",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    # 16 of 18 expected items asked → 88.9%
    assert report.coverage_percentage == round(100 * 16 / 18, 1)
    assert len(report.incomplete_items) == 2
    assert all(item in rqs_expected for item in report.incomplete_items)


# ─── Scenario 3: patient declined an item ──────────────────────────────

def test_patient_declined_counts_as_asked():
    """Patient declining an RQ keeps it in required_questions_asked AND
    lists it in required_questions_patient_declined. Coverage unchanged
    by the decline itself."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    declined_item = rqs_expected[0]  # pretend patient declined the first

    stub_response = json.dumps({
        "required_questions_asked": rqs_expected,
        "required_questions_patient_declined": [declined_item],
        "red_flag_probes_asked": rfps_expected,
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated call with one declined topic",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    assert report.coverage_percentage == 100.0  # decline counts as covered
    assert declined_item in report.required_questions_asked
    assert declined_item in report.required_questions_patient_declined
    assert report.incomplete_items == []


# ─── Scenario 4: red flag probe returns positive ───────────────────────

def test_red_flag_probe_positive():
    """One RFP is both asked and positive. Appears in both lists."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    positive_flag = rfps_expected[0]  # pretend this one fired positive

    stub_response = json.dumps({
        "required_questions_asked": rqs_expected,
        "red_flag_probes_asked": rfps_expected,
        "red_flag_probes_positive": [positive_flag],
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated call where wound_dehiscence_gaping fires",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    assert report.coverage_percentage == 100.0
    assert positive_flag in report.red_flag_probes_asked
    assert positive_flag in report.red_flag_probes_positive


# ─── Scenario 5: silent skip of a red flag probe (failure mode) ────────

def test_silent_skip_of_red_flag_probe():
    """Agent didn't ask a red flag probe at all. It appears in
    incomplete_items and in _expected but not in _asked. This is the
    most serious failure mode — red flags must be asked every call."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    skipped_flag = rfps_expected[0]
    rfps_asked_partial = rfps_expected[1:]

    stub_response = json.dumps({
        "required_questions_asked": rqs_expected,
        "red_flag_probes_asked": rfps_asked_partial,
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated call missing one red flag probe",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    # 17 of 18 covered → 94.4%
    assert report.coverage_percentage == round(100 * 17 / 18, 1)
    assert skipped_flag not in report.red_flag_probes_asked
    assert skipped_flag in report.incomplete_items


# ─── Hallucination / whitelist safety ──────────────────────────────────

def test_classifier_hallucination_whitelisted_out():
    """If the LLM invents an RQ or RFP not in the expected list, it's
    silently dropped. Coverage remains bounded by expected_total."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    stub_response = json.dumps({
        "required_questions_asked": rqs_expected + ["AN_INVENTED_QUESTION"],
        "red_flag_probes_asked": rfps_expected + ["an_invented_flag"],
    })
    llm = _StubLLM(stub_response)

    report = _run(validate_call_coverage(
        transcript="simulated call",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    assert "AN_INVENTED_QUESTION" not in report.required_questions_asked
    assert "an_invented_flag" not in report.red_flag_probes_asked
    assert report.coverage_percentage == 100.0


# ─── LLM failure modes ─────────────────────────────────────────────────

def test_llm_returns_unparseable_json():
    """Unparseable LLM response → conservative CoverageReport: 0%
    coverage, all expected items listed as incomplete. Never raises."""
    llm = _StubLLM("this is not JSON at all, the LLM went off-script")

    report = _run(validate_call_coverage(
        transcript="simulated call",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    assert report.coverage_percentage == 0.0
    assert len(report.incomplete_items) == 18  # 6 RQs + 12 RFPs
    assert len(report.required_questions_expected) == 6
    assert len(report.red_flag_probes_expected) == 12


def test_llm_raises_exception():
    """LLM.complete raises → conservative CoverageReport, logged, pipeline
    never blocked."""
    class _RaisingLLM:
        async def complete(self, system, user):
            raise RuntimeError("simulated API outage")

    report = _run(validate_call_coverage(
        transcript="simulated call",
        opcs_code="W40",
        call_day=7,
        llm_client=_RaisingLLM(),
    ))

    assert report.coverage_percentage == 0.0
    assert len(report.incomplete_items) == 18


# ─── Edge cases ────────────────────────────────────────────────────────

def test_none_opcs_returns_empty_report():
    """No pathway identified → empty expected lists, coverage_percentage
    None. Pipeline still gets a valid row to persist."""
    report = _run(validate_call_coverage(
        transcript="simulated call with unknown pathway",
        opcs_code=None,
        call_day=1,
        llm_client=_StubLLM("{}"),  # shouldn't be called
    ))

    assert report.coverage_percentage is None
    assert report.required_questions_expected == []
    assert report.red_flag_probes_expected == []
    assert report.incomplete_items == []


def test_z03_mh_scaffold_returns_100_nothing_to_cover():
    """Z03_MH has empty manifests; coverage is trivially 100% because
    there is nothing to cover. Separate from None opcs which means
    'pathway unknown' — this means 'pathway known but empty'."""
    report = _run(validate_call_coverage(
        transcript="any transcript — will not hit LLM",
        opcs_code="Z03_MH",
        call_day=1,
        llm_client=_StubLLM("{}"),  # shouldn't be called — short-circuits
    ))

    assert report.coverage_percentage == 100.0
    assert report.required_questions_expected == []
    assert report.red_flag_probes_expected == []


# ─── Prompt assembly smoke test ────────────────────────────────────────

def test_prompt_contains_expected_items():
    """Verify the system prompt embeds the expected items — sanity check
    that the classifier sees what it's meant to classify."""
    rqs_expected, rfps_expected = _w40_day7_expected()
    llm = _StubLLM(json.dumps({
        "required_questions_asked": rqs_expected,
        "red_flag_probes_asked": rfps_expected,
    }))

    _run(validate_call_coverage(
        transcript="simulated call",
        opcs_code="W40",
        call_day=7,
        llm_client=llm,
    ))

    # Prompt should contain the pathway label, day, every RQ question_text
    # and every RFP patient_facing_question.
    assert "Total Knee Replacement" in llm.last_system
    assert "Day 7" in llm.last_system
    for q in rqs_expected:
        assert q in llm.last_system
    # Each RFP flag_code and its patient_facing_question appear.
    rfps = build_red_flag_probes("W40")
    for p in rfps:
        assert p.flag_code in llm.last_system
        assert p.patient_facing_question in llm.last_system

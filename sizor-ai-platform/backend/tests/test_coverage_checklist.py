"""Phase 4 D5 — get_mandatory_call_checklist determinism + shape.

Not asserting the exact byte content (that would re-encode the Phase 3
manifests into this test and drift every time wording changes). Instead:
  - Determinism (byte-equal repeat calls for same inputs)
  - Structural invariants (header, RQ list presence, RFP list presence,
    MUST-ASK language present)
  - Z03_MH returns the CONTENT BLOCKED stub
  - Unknown / None opcs returns an unavailable stub
"""
from __future__ import annotations

import pytest

from app.clinical_intelligence.coverage import get_mandatory_call_checklist
from app.clinical_intelligence.pathways import PATHWAYS


ACTIVE_PATHWAYS = [
    opcs for opcs in sorted(PATHWAYS.keys()) if opcs != "Z03_MH"
]


# ─── Determinism ───────────────────────────────────────────────────────

@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_checklist_deterministic(opcs: str):
    """Same (opcs, day) inputs must produce byte-equal output across
    calls. Phase 6 embeds this in system prompts — any nondeterminism
    would invalidate prompt-cache reuse."""
    a = get_mandatory_call_checklist(opcs, 1)
    b = get_mandatory_call_checklist(opcs, 1)
    c = get_mandatory_call_checklist(opcs, 1)
    assert a == b == c


@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_checklist_day_variation_changes_output(opcs: str):
    """Day 1 and day 42 checklists differ for any pathway whose RQ
    day-bands actually vary across the monitoring window. (If they
    happen to be identical, the test still passes — we just check the
    function is day-sensitive.)"""
    day1 = get_mandatory_call_checklist(opcs, 1)
    day42 = get_mandatory_call_checklist(opcs, 42)
    # Header always includes the day, so outputs must differ at least
    # at the header line.
    assert "Day 1" in day1
    assert "Day 42" in day42
    assert day1 != day42


# ─── Structural invariants ─────────────────────────────────────────────

@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_checklist_contains_must_ask_language(opcs: str):
    """Every active-pathway checklist must contain the mandatory
    'MUST' framing — this is the coverage-enforcement guarantee."""
    out = get_mandatory_call_checklist(opcs, 1)
    assert "MUST cover every item" in out
    assert "MUST ASK EVERY CALL" in out
    assert "Do not silently skip" in out


@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_checklist_has_required_and_redflag_sections(opcs: str):
    """Both sections must always be present in an active-pathway
    checklist, even if a section is empty at the given day."""
    out = get_mandatory_call_checklist(opcs, 1)
    assert "### Required Questions" in out
    assert "### Red Flag Probes" in out


@pytest.mark.parametrize("opcs", ACTIVE_PATHWAYS)
def test_checklist_header_names_pathway(opcs: str):
    """Header must include the pathway label so the LLM sees what
    pathway it is handling."""
    label = PATHWAYS[opcs].label
    out = get_mandatory_call_checklist(opcs, 1)
    assert label in out


# ─── Z03_MH scaffold ───────────────────────────────────────────────────

def test_checklist_z03_mh_blocked():
    """Z03_MH must return the CONTENT BLOCKED stub. Agent must not be
    able to read an empty-but-structurally-valid checklist and think
    it's safe to proceed."""
    out = get_mandatory_call_checklist("Z03_MH", 1)
    assert "CONTENT BLOCKED" in out
    assert "MUST NOT initiate" in out


# ─── Edge cases ────────────────────────────────────────────────────────

def test_checklist_unknown_opcs():
    """Unknown pathway returns a distinct unavailable stub."""
    out = get_mandatory_call_checklist("BOGUS", 1)
    assert "unknown pathway" in out.lower()
    assert "escalate" in out.lower()


def test_checklist_none_opcs():
    """None opcs returns the unavailable stub — no pathway identified."""
    out = get_mandatory_call_checklist(None, 1)
    assert "unavailable" in out.lower()
    assert "escalate" in out.lower()


def test_checklist_day_past_monitoring_window():
    """A day past the manifest's coverage (e.g. W37 is 60-day monitoring
    and we ask for day 200) must not crash and must render a sensible
    message in the RQ section."""
    out = get_mandatory_call_checklist("W37", 200)
    # Header present, day 200 visible
    assert "Day 200" in out
    # RFP section still populated (red flags have no day filter)
    assert "### Red Flag Probes" in out
    # RQ section returns the stub message
    assert "No required questions" in out or "- [" in out

from __future__ import annotations

import re
from enum import Enum


class TriageLevel(str, Enum):
    RED = "red"
    AMBER = "amber"
    GREEN = "green"


# ── RED patterns ─────────────────────────────────────────────────────────────
# Any match → immediate escalation phrase mid-call

_RED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bchest\s+pain\b", re.I), "chest pain reported"),
    (re.compile(r"\bchest\s+tight(ness)?\b", re.I), "chest tightness reported"),
    (re.compile(r"\bbreath(ing)?\b.{0,30}\b(difficult|trouble|short|can't)\b", re.I), "breathing difficulty reported"),
    (re.compile(r"\b(can't|cannot|struggling to|difficulty)\s+breath(e|ing)\b", re.I), "breathing difficulty reported"),
    (re.compile(r"\bshortness\s+of\s+breath\b", re.I), "shortness of breath reported"),
    (re.compile(r"\bpain\b.{0,20}\b([89]|10)\s*(out\s+of\s+10|\/\s*10)?\b", re.I), "pain score ≥8/10"),
    (re.compile(r"\b(heavy|active|uncontrolled|a\s+lot\s+of)\s+bleed(ing)?\b", re.I), "active/heavy bleeding reported"),
    (re.compile(r"\b(suicid(al|e)|self.harm|kill\s+myself|end\s+my\s+life)\b", re.I), "suicidal ideation or self-harm reported"),
]

# ── AMBER patterns ────────────────────────────────────────────────────────────

_AMBER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bfever\b.{0,40}\b3[89]\b|\b3[89]\s*°?\s*[cC]\b", re.I), "fever ≥38°C reported"),
    (re.compile(r"\btemperature\b.{0,30}\b3[89]\b", re.I), "elevated temperature reported"),
    (re.compile(r"\bpain\b.{0,20}\b([5-7])\s*(out\s+of\s+10|\/\s*10)?\b", re.I), "pain score 5–7/10"),
    (re.compile(r"\b(not\s+taking|missed|skipped|forgotten)\b.{0,30}\b(medication|tablets?|pills?|prescription)\b", re.I), "missed medications reported"),
    (re.compile(r"\b(significant|severe|considerable|major)\s+(swelling|oedema)\b", re.I), "significant swelling reported"),
    (re.compile(r"\b(swollen|swelling)\b.{0,30}\b(a\s+lot|much\s+worse|very\s+bad)\b", re.I), "significant swelling reported"),
]


def check_red(text: str) -> list[str]:
    """Return list of triggered RED reasons (empty = no red flags)."""
    triggered: list[str] = []
    for pattern, reason in _RED_PATTERNS:
        if pattern.search(text):
            triggered.append(reason)
    return triggered


def check_amber(text: str) -> list[str]:
    """Return list of triggered AMBER reasons (empty = no amber flags)."""
    triggered: list[str] = []
    for pattern, reason in _AMBER_PATTERNS:
        if pattern.search(text):
            triggered.append(reason)
    return triggered


def classify_turn(text: str) -> tuple[TriageLevel, list[str]]:
    """
    Classify a single patient utterance in real-time.

    Returns (triage_level, reasons).
    RED takes precedence over AMBER.
    """
    red_reasons = check_red(text)
    if red_reasons:
        return TriageLevel.RED, red_reasons

    amber_reasons = check_amber(text)
    if amber_reasons:
        return TriageLevel.AMBER, amber_reasons

    return TriageLevel.GREEN, []


# Escalation phrase the agent should speak verbatim on RED detection
RED_ESCALATION_PHRASE = (
    "This sounds like it may require urgent medical attention. "
    "Please call 999 immediately or go to your nearest A&E. "
    "I'm flagging this call for immediate clinical review. "
    "Please seek help right now. Goodbye."
)

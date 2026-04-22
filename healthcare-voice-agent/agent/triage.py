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


# Soft acknowledgement injected as a system instruction when a RED flag is detected.
# Agent acknowledges warmly, gently signposts 999/111, then continues the call.
RED_FLAG_SYSTEM_INSTRUCTION = (
    "[RED FLAG DETECTED — do NOT end the call, do NOT alarm the patient] "
    "Acknowledge what they just said warmly and with genuine empathy — for example: "
    "'Oh I'm really sorry to hear that, that must be really hard for you.' "
    "Then gently say something like: 'I just want to make sure you know — if things feel "
    "like they're getting worse or you're worried at any point, please don't hesitate to "
    "ring NHS 111 or 999, they're always there to help.' "
    "Then continue with the rest of the call questions as normal. "
    "IMPORTANT: Never say 'that sounds concerning', 'that's worrying', 'that requires urgent attention' "
    "or anything that might frighten them. Stay warm, calm, and caring throughout."
)

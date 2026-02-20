from __future__ import annotations

import json
import logging
import re

from providers.groq_llm import GroqLLMProvider

logger = logging.getLogger(__name__)

_SYSTEM = """You are a clinical triage assistant. Analyse the following NHS post-appointment \
call transcript and classify the urgency level.

Respond ONLY with valid JSON in this exact format:
{
  "urgency": "red" | "amber" | "green",
  "reasons": ["reason 1", "reason 2"]
}

Urgency definitions:
  RED   — Life-threatening: chest pain, breathing difficulty, pain ≥8/10, active bleeding, \
suicidal ideation. Requires 999 / immediate A&E.
  AMBER — Concerning but not immediately life-threatening: fever >38°C, pain 5-7/10, \
missed critical meds, significant swelling.  Requires same-day GP review.
  GREEN — Recovering as expected. No urgent concerns. Routine follow-up sufficient.

If no transcript is available, default to amber and state "insufficient data"."""

_JSON_PATTERN = re.compile(r"\{[\s\S]*?\}", re.DOTALL)


async def classify_urgency(
    transcript: str,
    realtime_level: str = "green",
    realtime_reasons: list[str] | None = None,
) -> tuple[str, list[str]]:
    """
    Classify call urgency using Groq LLM.

    The real-time regex result is included as a hint so the LLM can weight it.
    Returns (urgency_level, reasons) where urgency_level is 'red'|'amber'|'green'.
    """
    hint = ""
    if realtime_reasons:
        hint = (
            f"\n\nNOTE: Real-time keyword detection flagged this call as {realtime_level.upper()} "
            f"due to: {', '.join(realtime_reasons)}. Factor this into your classification."
        )

    provider = GroqLLMProvider()
    prompt = f"CALL TRANSCRIPT:\n{transcript}{hint}\n\nClassify the urgency."

    try:
        raw = await provider.complete(prompt=prompt, system=_SYSTEM)
        # Extract first JSON object from response
        match = _JSON_PATTERN.search(raw)
        if not match:
            raise ValueError(f"No JSON found in response: {raw[:200]}")

        data = json.loads(match.group())
        level = data.get("urgency", "amber").lower()
        reasons = data.get("reasons", [])

        if level not in ("red", "amber", "green"):
            level = "amber"

        logger.info("Urgency classified: %s — %s", level, reasons)
        return level, reasons

    except Exception as exc:
        logger.error("Urgency classification failed: %s", exc)
        # Fall back to the real-time triage result
        return realtime_level, realtime_reasons or [f"classification error: {exc}"]

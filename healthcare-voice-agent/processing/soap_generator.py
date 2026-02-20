from __future__ import annotations

import logging

from providers.groq_llm import GroqLLMProvider

logger = logging.getLogger(__name__)

_SYSTEM = """You are a clinical documentation assistant. Given a call transcript between \
an NHS automated check-in agent and a patient, produce a concise SOAP note.

Format your output EXACTLY as:

SUBJECTIVE:
<Patient's subjective complaints and reported symptoms in 2-4 sentences>

OBJECTIVE:
<Measurable data mentioned: pain scores, temperature, medications, physical signs>

ASSESSMENT:
<Brief clinical impression based solely on the transcript information>

PLAN:
<Recommended follow-up actions e.g. GP review, A&E referral, continue monitoring>

Be concise. Use plain language. Do not invent information not present in the transcript."""


async def generate_soap_note(transcript: str) -> str:
    """
    Generate a SOAP note from a call transcript using Groq.

    Returns the raw SOAP note string.
    """
    provider = GroqLLMProvider()
    prompt = f"CALL TRANSCRIPT:\n{transcript}\n\nPlease produce the SOAP note."
    try:
        soap = await provider.complete(prompt=prompt, system=_SYSTEM)
        logger.info("SOAP note generated (%d chars)", len(soap))
        return soap
    except Exception as exc:
        logger.error("SOAP generation failed: %s", exc)
        return f"SOAP generation error: {exc}"

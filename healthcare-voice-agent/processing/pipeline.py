from __future__ import annotations

import logging
import uuid

from config.settings import settings
from processing.embedder import embed_text
from processing.soap_generator import generate_soap_note
from processing.urgency_classifier import classify_urgency
from storage.database import get_db
from storage.models import Summary, Transcript, UrgencyFlag
from storage.repositories import (
    insert_summary,
    insert_transcript,
    insert_urgency_flag,
)
from storage.vector_store import VectorStore

logger = logging.getLogger(__name__)


async def run_post_call_pipeline(
    call_id: str,
    patient_name: str,
    transcript: str,
    turn_count: int,
    realtime_triage_level: str = "green",
    realtime_triage_reasons: list[str] | None = None,
) -> None:
    """
    Async post-call pipeline — runs after every call completes.

    Steps:
      1. Persist raw transcript
      2. Generate SOAP note (Groq)
      3. Classify urgency (Groq)
      4. Embed transcript (sentence-transformers) → ChromaDB
      5. Persist summary + urgency flag to SQLite
    """
    logger.info("Post-call pipeline starting — call_id=%s", call_id)

    # ── 1. Persist transcript ─────────────────────────────────────────────────
    transcript_record = Transcript(
        transcript_id=str(uuid.uuid4()),
        call_id=call_id,
        full_text=transcript,
        turn_count=turn_count,
    )
    async with get_db(settings.sqlite_db_path) as db:
        await insert_transcript(db, transcript_record)
    logger.debug("Transcript persisted — call_id=%s turns=%d", call_id, turn_count)

    # ── 2 & 3. SOAP + urgency (run concurrently) ──────────────────────────────
    import asyncio

    soap_task = asyncio.create_task(generate_soap_note(transcript))
    urgency_task = asyncio.create_task(
        classify_urgency(
            transcript=transcript,
            realtime_level=realtime_triage_level,
            realtime_reasons=realtime_triage_reasons or [],
        )
    )
    soap_note, (urgency_level, urgency_reasons) = await asyncio.gather(
        soap_task, urgency_task
    )

    # ── 4. Embed + store in ChromaDB ──────────────────────────────────────────
    try:
        embedding = embed_text(transcript)
        vector_store = VectorStore(persist_path=settings.chroma_persist_path)
        vector_store.upsert(
            call_id=call_id,
            embedding=embedding,
            document=transcript,
            urgency=urgency_level,
            patient_name=patient_name,
        )
        logger.debug("Embedding stored — call_id=%s", call_id)
    except Exception as exc:
        logger.error("Embedding failed — call_id=%s: %s", call_id, exc)

    # ── 5. Persist summary + urgency flag ─────────────────────────────────────
    summary = Summary(
        summary_id=str(uuid.uuid4()),
        call_id=call_id,
        soap_note=soap_note,
        model_used=settings.groq_model,
    )
    flag = UrgencyFlag(
        flag_id=str(uuid.uuid4()),
        call_id=call_id,
        urgency_level=urgency_level,
        reasons=urgency_reasons,
    )
    async with get_db(settings.sqlite_db_path) as db:
        await insert_summary(db, summary)
        await insert_urgency_flag(db, flag)

    logger.info(
        "Post-call pipeline complete — call_id=%s urgency=%s",
        call_id,
        urgency_level,
    )

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import settings
from processing.embedder import embed_text
from storage.database import get_db
from storage.models import ScheduledCall
from storage.repositories import (
    get_call,
    get_flag_by_call,
    get_summary_by_call,
    get_transcript_by_call,
    insert_scheduled_call,
    list_calls,
    list_flags,
    mark_flag_reviewed,
)
from storage.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# ── Call endpoints ────────────────────────────────────────────────────────────

@router.get("/calls")
async def api_list_calls(limit: int = 100, offset: int = 0):
    async with get_db(settings.sqlite_db_path) as db:
        calls = await list_calls(db, limit=limit, offset=offset)
    return [vars(c) for c in calls]


@router.get("/calls/{call_id}")
async def api_get_call(call_id: str):
    async with get_db(settings.sqlite_db_path) as db:
        call = await get_call(db, call_id)
        if call is None:
            raise HTTPException(status_code=404, detail="Call not found")
        transcript = await get_transcript_by_call(db, call_id)
        summary = await get_summary_by_call(db, call_id)
        flag = await get_flag_by_call(db, call_id)
    return {
        "call": vars(call),
        "transcript": vars(transcript) if transcript else None,
        "summary": vars(summary) if summary else None,
        "flag": vars(flag) if flag else None,
    }


# ── Flags ─────────────────────────────────────────────────────────────────────

@router.get("/flags")
async def api_list_flags(
    urgency: Optional[str] = None,
    reviewed: Optional[bool] = None,
    limit: int = 100,
):
    async with get_db(settings.sqlite_db_path) as db:
        flags = await list_flags(db, urgency_level=urgency, reviewed=reviewed, limit=limit)
    return [vars(f) for f in flags]


class ReviewRequest(BaseModel):
    reviewed_by: str = "clinician"


@router.post("/flags/{flag_id}/review")
async def api_review_flag(flag_id: str, body: ReviewRequest):
    async with get_db(settings.sqlite_db_path) as db:
        await mark_flag_reviewed(db, flag_id, reviewed_by=body.reviewed_by)
    return {"status": "ok", "flag_id": flag_id}


# ── Scheduling ────────────────────────────────────────────────────────────────

class ScheduleCallRequest(BaseModel):
    patient_name: str
    nhs_number: str
    phone_number: str
    scheduled_at: float  # Unix timestamp
    patient_id: Optional[str] = None


@router.post("/schedule", status_code=201)
async def api_schedule_call(body: ScheduleCallRequest):
    sc = ScheduledCall(
        scheduled_call_id=str(uuid.uuid4()),
        patient_name=body.patient_name,
        nhs_number=body.nhs_number,
        phone_number=body.phone_number,
        scheduled_at=body.scheduled_at,
        patient_id=body.patient_id,
    )
    async with get_db(settings.sqlite_db_path) as db:
        await insert_scheduled_call(db, sc)
    return {"scheduled_call_id": sc.scheduled_call_id, "scheduled_at": sc.scheduled_at}


# ── Semantic search ───────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    urgency_filter: Optional[str] = None


@router.post("/search")
async def api_semantic_search(body: SearchRequest):
    try:
        query_embedding = embed_text(body.query)
        vector_store = VectorStore(persist_path=settings.chroma_persist_path)
        results = vector_store.semantic_search(
            query_embedding=query_embedding,
            n_results=body.n_results,
            urgency_filter=body.urgency_filter,
        )
        return {"results": results}
    except Exception as exc:
        logger.error("Semantic search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

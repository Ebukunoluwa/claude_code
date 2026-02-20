from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config.settings import settings
from storage.database import get_db
from storage.repositories import (
    get_call,
    get_flag_by_call,
    get_summary_by_call,
    get_transcript_by_call,
    list_calls,
    list_flags,
    mark_flag_reviewed,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="dashboard/templates")


@router.get("/", response_class=HTMLResponse)
async def call_list(request: Request):
    """Main dashboard: all calls sorted Red → Amber → Green."""
    async with get_db(settings.sqlite_db_path) as db:
        calls = await list_calls(db, limit=200)
        flags = await list_flags(db, limit=500)

    # Build flag lookup by call_id
    flag_map = {f.call_id: f for f in flags}

    # Sort calls: red first, then amber, then green, then calls without flags
    _order = {"red": 0, "amber": 1, "green": 2}
    calls_with_flags = []
    for call in calls:
        flag = flag_map.get(call.call_id)
        sort_key = _order.get(flag.urgency_level, 3) if flag else 3
        calls_with_flags.append((call, flag, sort_key))

    calls_with_flags.sort(key=lambda x: (x[2], -(x[0].started_at or 0)))

    return templates.TemplateResponse(
        "call_list.html",
        {
            "request": request,
            "calls_with_flags": calls_with_flags,
            "now": time.time(),
        },
    )


@router.get("/calls/{call_id}", response_class=HTMLResponse)
async def call_detail(request: Request, call_id: str):
    """Detail page: transcript + SOAP note + urgency reasons + review button."""
    async with get_db(settings.sqlite_db_path) as db:
        call = await get_call(db, call_id)
        transcript = await get_transcript_by_call(db, call_id)
        summary = await get_summary_by_call(db, call_id)
        flag = await get_flag_by_call(db, call_id)

    if call is None:
        from fastapi.responses import Response
        return Response(status_code=404, content="Call not found")

    return templates.TemplateResponse(
        "call_detail.html",
        {
            "request": request,
            "call": call,
            "transcript": transcript,
            "summary": summary,
            "flag": flag,
        },
    )


@router.post("/calls/{call_id}/review", response_class=HTMLResponse)
async def mark_reviewed(request: Request, call_id: str):
    """Mark a call's urgency flag as reviewed (HTMX endpoint)."""
    form = await request.form()
    reviewed_by = form.get("reviewed_by", "clinician")

    async with get_db(settings.sqlite_db_path) as db:
        flag = await get_flag_by_call(db, call_id)
        if flag and not flag.reviewed:
            await mark_flag_reviewed(db, flag.flag_id, reviewed_by=str(reviewed_by))
            flag = await get_flag_by_call(db, call_id)

    return templates.TemplateResponse(
        "partials/flag_badge.html",
        {
            "request": request,
            "flag": flag,
            "reviewed": True,
        },
    )

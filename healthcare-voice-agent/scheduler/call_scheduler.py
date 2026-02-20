from __future__ import annotations

import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from storage.database import get_db
from storage.repositories import (
    get_pending_scheduled_calls,
    mark_scheduled_call_dispatched,
)
from telephony.outbound_caller import initiate_outbound_call

logger = logging.getLogger(__name__)


async def _dispatch_due_calls() -> None:
    """Poll the scheduled_calls table and dispatch any calls that are due."""
    now = time.time()
    async with get_db(settings.sqlite_db_path) as db:
        pending = await get_pending_scheduled_calls(db, before_ts=now)

    if not pending:
        return

    logger.info("Scheduler: %d call(s) due", len(pending))

    for sc in pending:
        try:
            call_id = await initiate_outbound_call(
                phone_number=sc.phone_number,
                patient_name=sc.patient_name,
                nhs_number=sc.nhs_number,
                call_id=None,  # generates a new UUID
            )
            async with get_db(settings.sqlite_db_path) as db:
                await mark_scheduled_call_dispatched(db, sc.scheduled_call_id, call_id)
            logger.info(
                "Scheduler: dispatched call to %s — call_id=%s",
                sc.patient_name,
                call_id,
            )
        except Exception as exc:
            logger.error(
                "Scheduler: failed to dispatch call to %s: %s",
                sc.patient_name,
                exc,
            )


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance (not yet started)."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _dispatch_due_calls,
        trigger="interval",
        seconds=settings.scheduler_poll_interval_seconds,
        id="dispatch_scheduled_calls",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "Scheduler configured — poll interval=%ds",
        settings.scheduler_poll_interval_seconds,
    )
    return scheduler

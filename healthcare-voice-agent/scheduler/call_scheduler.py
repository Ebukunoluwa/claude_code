from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config.settings import settings
from sizor_ai.client import get_due_schedules, mark_schedule_dispatched
from telephony.outbound_caller import initiate_outbound_call

logger = logging.getLogger(__name__)


async def _dispatch_due_calls() -> None:
    """
    Poll Sizor for pending CallSchedule rows that are due, then initiate each call.
    Source of truth is the Sizor backend — the old SQLite scheduled_calls table
    is no longer used.
    """
    schedules = await get_due_schedules()

    if not schedules:
        return

    logger.info("Scheduler: %d call(s) due from Sizor", len(schedules))

    for sc in schedules:
        schedule_id = sc["schedule_id"]
        patient_id = sc["patient_id"]
        patient_name = sc["patient_name"]
        nhs_number = sc["nhs_number"]
        phone_number = sc["phone_number"]

        try:
            call_id = await initiate_outbound_call(
                phone_number=phone_number,
                patient_name=patient_name,
                nhs_number=nhs_number,
                patient_id=patient_id,
            )
        except Exception as exc:
            logger.error(
                "Scheduler: failed to initiate call to %s (schedule=%s): %s",
                patient_name,
                schedule_id,
                exc,
            )
            continue  # leave as pending — will retry on next poll

        logger.info(
            "Scheduler: SIP call initiated — patient=%s call_id=%s schedule=%s",
            patient_name,
            call_id,
            schedule_id,
        )

        await mark_schedule_dispatched(schedule_id, call_id)


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
        "Scheduler configured — poll interval=%ds (source: Sizor backend)",
        settings.scheduler_poll_interval_seconds,
    )
    return scheduler

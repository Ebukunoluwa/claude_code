"""
Celery task that fires a probe call via LiveKit SIP at the scheduled time.

Uses the same mechanism as the voice agent's outbound_caller.py:
  livekit.api.create_sip_participant() → Twilio SIP trunk → patient's phone

The probe_call_id and probe_prompt are passed as participant attributes so the
CheckInAgent can use the probe prompt as its system prompt instead of the
standard post-discharge script.

After the call, the voice agent ingests via /calls/ingest (with probe_call_id),
which triggers the post-call pipeline (SOAP, flags, etc.) and links the
resulting SOAP note back to the probe_call record.
"""
import asyncio
import uuid
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from .celery_app import celery_app
from ..config import settings
from ..models import ProbeCall, Patient, SOAPNote, CallRecord, CallSchedule

TEST_PHONE_NUMBER = "+447888629971"


def _get_session():
    engine = create_async_engine(settings.database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="fire_probe_call")
def fire_probe_call(probe_call_id: str):
    async def _run():
        SessionLocal = _get_session()
        async with SessionLocal() as db:
            pc = (await db.execute(
                select(ProbeCall).where(ProbeCall.probe_call_id == uuid.UUID(probe_call_id))
            )).scalar_one_or_none()
            if not pc or pc.status != "pending":
                return

            patient = (await db.execute(
                select(Patient).where(Patient.patient_id == pc.patient_id)
            )).scalar_one_or_none()
            if not patient:
                pc.status = "failed"
                await db.commit()
                return

            if not settings.livekit_url or not settings.livekit_api_key or not settings.twilio_sip_trunk_id:
                # LiveKit not configured — mark so the UI reflects it
                pc.status = "failed"
                await db.commit()
                return

            try:
                from livekit import api as lk_api

                call_id = str(uuid.uuid4())
                room_name = f"probe-{call_id}"

                lk_client = lk_api.LiveKitAPI(
                    url=settings.livekit_url,
                    api_key=settings.livekit_api_key,
                    api_secret=settings.livekit_api_secret,
                )

                try:
                    await lk_client.sip.create_sip_participant(
                        lk_api.CreateSIPParticipantRequest(
                            sip_trunk_id=settings.twilio_sip_trunk_id,
                            sip_call_to=TEST_PHONE_NUMBER,
                            room_name=room_name,
                            participant_identity=f"patient-{call_id}",
                            participant_name=patient.full_name,
                            participant_attributes={
                                "call_id":        call_id,
                                "patient_name":   patient.full_name,
                                "nhs_number":     patient.nhs_number,
                                "patient_id":     str(patient.patient_id),
                                "direction":      "outbound",
                                "phone_number":   TEST_PHONE_NUMBER,
                                "room_name":      room_name,
                                # Probe-specific
                                "is_probe":       "true",
                                "probe_call_id":  probe_call_id,
                                "probe_prompt":   pc.call_prompt,
                            },
                        )
                    )
                finally:
                    await lk_client.aclose()

                pc.status = "initiated"
                pc.call_sid = call_id   # store LiveKit call_id in call_sid field
                await db.commit()

            except Exception as exc:
                pc.status = "failed"
                await db.commit()
                raise exc

    asyncio.run(_run())


@celery_app.task(name="link_probe_call")
def link_probe_call(probe_call_id: str, call_id: str):
    """
    Runs ~30s after the call is ingested, giving the pipeline time to generate the SOAP note.
    Links the SOAPNote back to the ProbeCall record and marks it completed.
    """
    async def _run():
        SessionLocal = _get_session()
        async with SessionLocal() as db:
            pc = (await db.execute(
                select(ProbeCall).where(ProbeCall.probe_call_id == uuid.UUID(probe_call_id))
            )).scalar_one_or_none()
            if not pc:
                return

            soap = (await db.execute(
                select(SOAPNote).where(SOAPNote.call_id == uuid.UUID(call_id))
            )).scalar_one_or_none()

            if soap:
                pc.soap_note_id = soap.soap_id

            pc.status = "completed"
            await db.commit()

    asyncio.run(_run())


@celery_app.task(name="fire_scheduled_call")
def fire_scheduled_call(schedule_id: str):
    """
    Fires a CallSchedule entry via LiveKit SIP.
    Uses select-then-update to claim the schedule atomically.
    """
    import logging
    logger = logging.getLogger(__name__)

    async def _run():
        SessionLocal = _get_session()
        async with SessionLocal() as db:
            schedule = (await db.execute(
                select(CallSchedule).where(CallSchedule.schedule_id == uuid.UUID(schedule_id))
            )).scalar_one_or_none()

            if not schedule:
                logger.warning("fire_scheduled_call: schedule %s not found", schedule_id)
                return
            if schedule.status != "pending":
                logger.info("fire_scheduled_call: schedule %s already %s — skipping", schedule_id, schedule.status)
                return

            # Claim it
            schedule.status = "dispatched"
            await db.commit()

            patient = (await db.execute(
                select(Patient).where(Patient.patient_id == schedule.patient_id)
            )).scalar_one_or_none()
            if not patient:
                logger.warning("fire_scheduled_call: patient not found for schedule %s", schedule_id)
                return

            # Wait for playbook to be generated before dialling.
            # Playbook generation is async (LLM calls can take 90-180s on first patient).
            # Poll up to 5 minutes so the agent always has pathway questions ready.
            for attempt in range(60):  # 60 × 5s = 300s (5 min) max
                pw_check = (await db.execute(text("""
                    SELECT playbook IS NOT NULL AS has_playbook
                    FROM patient_pathways
                    WHERE patient_id = :pid AND active = true
                    LIMIT 1
                """), {"pid": str(patient.patient_id)})).mappings().first()

                if not pw_check:
                    break  # no pathway — proceed without waiting
                if pw_check["has_playbook"]:
                    logger.info(
                        "fire_scheduled_call: playbook ready after %ds — proceeding patient=%s",
                        attempt * 5, patient.full_name,
                    )
                    break
                logger.info(
                    "fire_scheduled_call: playbook not ready yet, waiting 5s (attempt %d/60) patient=%s",
                    attempt + 1, patient.full_name,
                )
                await asyncio.sleep(5)
            else:
                logger.warning(
                    "fire_scheduled_call: playbook still not ready after 300s — proceeding without it patient=%s",
                    patient.full_name,
                )

            logger.info("fire_scheduled_call: firing call to %s (%s)", patient.full_name, patient.phone_number)

            if not settings.livekit_url or not settings.livekit_api_key or not settings.twilio_sip_trunk_id:
                logger.error(
                    "fire_scheduled_call: LiveKit/SIP not configured — livekit_url=%r trunk=%r",
                    settings.livekit_url, settings.twilio_sip_trunk_id,
                )
                schedule.status = "pending"
                await db.commit()
                return

            from datetime import date as date_type, datetime as datetime_type, timezone as tz
            day_in_recovery = (
                (date_type.today() - patient.discharge_date).days
                if patient.discharge_date else None
            )

            # Find the next pending schedule for this patient (after this one)
            now_utc = datetime_type.now(tz.utc)
            next_sched_result = await db.execute(
                select(CallSchedule)
                .where(
                    CallSchedule.patient_id == patient.patient_id,
                    CallSchedule.status == "pending",
                    CallSchedule.scheduled_for > now_utc,
                    CallSchedule.schedule_id != schedule.schedule_id,
                )
                .order_by(CallSchedule.scheduled_for)
                .limit(1)
            )
            next_sched = next_sched_result.scalar_one_or_none()
            if next_sched:
                dt = next_sched.scheduled_for
                next_appointment = dt.strftime("%A %-d %B at %H:%M")
            else:
                next_appointment = "not yet scheduled"

            try:
                from livekit import api as lk_api
                call_id = str(uuid.uuid4())
                room_name = f"call-{call_id}"
                lk_client = lk_api.LiveKitAPI(
                    url=settings.livekit_url,
                    api_key=settings.livekit_api_key,
                    api_secret=settings.livekit_api_secret,
                )
                try:
                    await lk_client.sip.create_sip_participant(
                        lk_api.CreateSIPParticipantRequest(
                            sip_trunk_id=settings.twilio_sip_trunk_id,
                            sip_call_to=patient.phone_number,
                            room_name=room_name,
                            participant_identity=f"patient-{call_id}",
                            participant_name=patient.full_name,
                            participant_attributes={
                                "call_id":          call_id,
                                "patient_name":     patient.full_name,
                                "nhs_number":       patient.nhs_number,
                                "patient_id":       str(patient.patient_id),
                                "direction":        "outbound",
                                "phone_number":     patient.phone_number,
                                "room_name":        room_name,
                                "date_of_birth":    str(patient.date_of_birth) if patient.date_of_birth else "",
                                "postcode":         patient.postcode or "",
                                "discharge_date":   str(patient.discharge_date) if patient.discharge_date else "",
                                "day_in_recovery":  str(day_in_recovery) if day_in_recovery is not None else "",
                                "next_appointment": next_appointment,
                            },
                        )
                    )
                finally:
                    await lk_client.aclose()

                logger.info("fire_scheduled_call: SIP call initiated — call_id=%s patient=%s next_appt=%r", call_id, patient.full_name, next_appointment)

            except Exception as exc:
                logger.error("fire_scheduled_call: LiveKit call failed — %s", exc)
                schedule.status = "pending"
                await db.commit()
                raise

    asyncio.run(_run())

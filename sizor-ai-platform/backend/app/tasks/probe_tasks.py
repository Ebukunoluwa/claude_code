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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from .celery_app import celery_app
from ..config import settings
from ..models import ProbeCall, Patient, SOAPNote, CallRecord

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

    asyncio.get_event_loop().run_until_complete(_run())


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

    asyncio.get_event_loop().run_until_complete(_run())

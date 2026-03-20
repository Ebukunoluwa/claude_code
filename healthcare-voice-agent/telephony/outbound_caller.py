from __future__ import annotations

import logging
import uuid

from livekit import api as lk_api

from config.settings import settings
from telephony.sip_config import OUTBOUND_TRUNK_ID

logger = logging.getLogger(__name__)


async def initiate_outbound_call(
    phone_number: str,
    patient_name: str,
    nhs_number: str,
    call_id: str | None = None,
    next_appointment: str = "not yet scheduled",
    patient_id: str = "",
) -> str:
    """
    Initiate an outbound SIP call via the LiveKit SIP API.

    Returns the call_id used (which is also set as a participant attribute in the room).
    """
    call_id = call_id or str(uuid.uuid4())
    room_name = f"call-{call_id}"

    lk_client = lk_api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    try:
        await lk_client.sip.create_sip_participant(
            lk_api.CreateSIPParticipantRequest(
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                room_name=room_name,
                participant_identity=f"patient-{call_id}",
                participant_name=patient_name,
                participant_attributes={
                    "call_id": call_id,
                    "patient_name": patient_name,
                    "nhs_number": nhs_number,
                    "patient_id": patient_id,
                    "direction": "outbound",
                    "phone_number": phone_number,
                    "next_appointment": next_appointment,
                    "room_name": room_name,
                },
            )
        )
        logger.info(
            "Outbound SIP call initiated — call_id=%s phone=%s room=%s",
            call_id,
            phone_number,
            room_name,
        )
    finally:
        await lk_client.aclose()

    return call_id

from __future__ import annotations

import logging
import re
import uuid

from livekit import api as lk_api

from config.settings import settings
from telephony.sip_config import OUTBOUND_TRUNK_ID

logger = logging.getLogger(__name__)


def _to_e164(number: str) -> str:
    """
    Normalise a phone number to E.164 format (+<country><subscriber>).

    Rules applied in order:
      1. Strip whitespace, dashes, parentheses, dots.
      2. If the result already starts with '+', keep it — assume caller
         entered a valid international number.
      3. If it starts with '00', replace with '+'.
      4. UK local format (07xxx / 01xxx / 02xxx — 11 digits starting with 0)
         → strip leading 0 and prepend +44.
      5. Anything else that has 10+ digits without a leading '+' gets a bare
         '+' prepended so Twilio can at least attempt routing.

    The function intentionally does NOT guess the country for ambiguous
    formats.  Clinicians should always enter numbers in international format.
    """
    stripped = re.sub(r"[\s\-().+]", "", number.strip())  # digits only
    raw = number.strip()

    # Already has + — normalise spacing/dashes only
    if raw.lstrip().startswith("+"):
        return "+" + stripped

    # 00-prefix international dialling
    if stripped.startswith("00"):
        return "+" + stripped[2:]

    # UK local: starts with 07/01/02, exactly 11 digits
    if re.match(r"^0[127]\d{9}$", stripped):
        return "+44" + stripped[1:]

    # Fallback: prepend + so Twilio at least sees an international format
    return "+" + stripped


async def initiate_outbound_call(
    phone_number: str,
    patient_name: str,
    nhs_number: str,
    call_id: str | None = None,
    next_appointment: str = "not yet scheduled",
    patient_id: str = "",
    date_of_birth: str = "",
    postcode: str = "",
    discharge_date: str = "",
    day_in_recovery: int | None = None,
) -> str:
    """
    Initiate an outbound SIP call via the LiveKit SIP API.

    Returns the call_id used (which is also set as a participant attribute in the room).
    """
    call_id = call_id or str(uuid.uuid4())
    room_name = f"call-{call_id}"

    normalised = _to_e164(phone_number)
    if normalised != phone_number:
        logger.info("Phone normalised: %r → %r", phone_number, normalised)
    phone_number = normalised

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
                    "date_of_birth": date_of_birth or "",
                    "postcode": postcode or "",
                    "discharge_date": discharge_date or "",
                    "day_in_recovery": str(day_in_recovery) if day_in_recovery is not None else "",
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

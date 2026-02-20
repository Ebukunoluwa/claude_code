from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from twilio.request_validator import RequestValidator

from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["telephony"])

_validator = RequestValidator(settings.twilio_auth_token)


def _validate_twilio_signature(
    request: Request,
    x_twilio_signature: str,
    form_data: dict,
) -> None:
    url = str(request.url)
    if not _validator.validate(url, form_data, x_twilio_signature):
        logger.warning("Invalid Twilio signature from %s", request.client)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )


@router.post("/inbound")
async def inbound_call(
    request: Request,
    x_twilio_signature: Annotated[str, Header(alias="X-Twilio-Signature")] = "",
    # Standard Twilio form fields
    CallSid: Annotated[str, Form()] = "",
    From: Annotated[str, Form()] = "",
    To: Annotated[str, Form()] = "",
    CallStatus: Annotated[str, Form()] = "",
):
    """
    Receives inbound call notification from Twilio.

    Twilio sends a POST with form data; this handler:
      1. Validates the Twilio signature
      2. Creates a LiveKit room with participant attributes
      3. Returns TwiML to connect the call to LiveKit SIP

    The actual room creation / agent joining happens via LiveKit SIP inbound trunk
    configuration in the LiveKit dashboard — this webhook just logs/validates.
    """
    form_data = await request.form()
    form_dict = dict(form_data)

    # Validate signature only in production (skip if secret not configured)
    if settings.twilio_auth_token and settings.twilio_auth_token != "your_twilio_auth_token":
        _validate_twilio_signature(request, x_twilio_signature, form_dict)

    call_id = str(uuid.uuid4())
    logger.info(
        "Inbound call — call_sid=%s from=%s call_id=%s",
        CallSid,
        From,
        call_id,
    )

    # TwiML response: LiveKit SIP inbound is handled at the trunk level,
    # so we just return an empty 200 here. The LiveKit SIP trunk routes the
    # call into a room and fires the agent worker job automatically.
    from fastapi.responses import Response
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )

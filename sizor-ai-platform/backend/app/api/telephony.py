"""
Twilio inbound call webhook — receives call notifications from Twilio.
Validates the Twilio signature and returns TwiML. The actual call routing
is handled by the LiveKit SIP inbound trunk configured in the LiveKit dashboard.
"""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Request, status
from fastapi.responses import Response
from twilio.request_validator import RequestValidator

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/twilio", tags=["telephony"])


@router.post("/inbound")
async def inbound_call(
    request: Request,
    x_twilio_signature: Annotated[str, Header(alias="X-Twilio-Signature")] = "",
    CallSid: Annotated[str, Form()] = "",
    From: Annotated[str, Form()] = "",
    To: Annotated[str, Form()] = "",
    CallStatus: Annotated[str, Form()] = "",
):
    """
    Receives inbound Twilio call webhook.
    Validates the signature, logs the call, and returns an empty TwiML response.
    LiveKit SIP inbound trunk handles actual routing into a room.
    """
    twilio_auth_token = getattr(settings, "twilio_auth_token", "")
    if twilio_auth_token and twilio_auth_token not in ("your_twilio_auth_token", ""):
        form_data = dict(await request.form())
        validator = RequestValidator(twilio_auth_token)
        if not validator.validate(str(request.url), form_data, x_twilio_signature):
            logger.warning("Invalid Twilio signature from %s", request.client)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    call_id = str(uuid.uuid4())
    logger.info("Inbound call — call_sid=%s from=%s call_id=%s", CallSid, From, call_id)

    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )

from __future__ import annotations

from config.settings import settings

# LiveKit SIP trunk resource ID (set TWILIO_SIP_TRUNK_ID in .env)
OUTBOUND_TRUNK_ID: str = settings.twilio_sip_trunk_id

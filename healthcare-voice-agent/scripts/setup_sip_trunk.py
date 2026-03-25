"""
Recreate the LiveKit SIP inbound trunk and dispatch rule.

Run once:
    python scripts/setup_sip_trunk.py
"""
from __future__ import annotations

import asyncio
import sys

from livekit import api as lkapi

from config.settings import settings


async def main() -> None:
    lk = lkapi.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    # ── 1. List existing trunks (skip creation if one already exists) ─────────
    existing_trunks = await lk.sip.list_sip_inbound_trunk(lkapi.ListSIPInboundTrunkRequest())
    if existing_trunks.items:
        trunk = existing_trunks.items[0]
        print(f"Existing SIP inbound trunk: id={trunk.sip_trunk_id}  name={trunk.name}")
    else:
        trunk_req = lkapi.CreateSIPInboundTrunkRequest(
            trunk=lkapi.SIPInboundTrunkInfo(
                name="sizor-inbound-trunk",
                numbers=[settings.twilio_phone_number],
            )
        )
        trunk = await lk.sip.create_sip_inbound_trunk(trunk_req)
        print(f"Created SIP inbound trunk: id={trunk.sip_trunk_id}  name={trunk.name}")

    sip_domain = f"{trunk.sip_trunk_id}.sip.livekit.cloud"
    print()
    print(">>> Update LIVEKIT_SIP_INBOUND_DOMAIN in your .env to:")
    print(f"    LIVEKIT_SIP_INBOUND_DOMAIN={sip_domain}")
    print()

    # ── 2. Create dispatch rule ───────────────────────────────────────────────
    rule_req = lkapi.CreateSIPDispatchRuleRequest(
        name="sizor-inbound-catchall",
        rule=lkapi.SIPDispatchRule(
            dispatch_rule_individual=lkapi.SIPDispatchRuleIndividual(
                room_prefix="inbound-",
            )
        ),
        metadata="inbound",
    )
    rule = await lk.sip.create_sip_dispatch_rule(rule_req)
    print(f"Created dispatch rule: id={rule.sip_dispatch_rule_id}  name={rule.name}")

    await lk.aclose()
    print()
    print("Done. Update your .env then restart the backend and inbound agent worker.")


if __name__ == "__main__":
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        print("ERROR: LIVEKIT_API_KEY / LIVEKIT_API_SECRET not set in .env")
        sys.exit(1)
    if not settings.twilio_phone_number:
        print("ERROR: TWILIO_PHONE_NUMBER not set in .env")
        sys.exit(1)
    asyncio.run(main())

"""
One-time setup: create a LiveKit SIP dispatch rule so inbound calls
are routed to the sizor-inbound agent worker.

Run once:
    python scripts/setup_inbound_dispatch.py
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

    # List existing dispatch rules so we don't create duplicates
    existing = await lk.sip.list_sip_dispatch_rule(lkapi.ListSIPDispatchRuleRequest())
    for rule in existing.items:
        print(f"Existing rule: id={rule.sip_dispatch_rule_id}  name={rule.name}")

    # Create a catch-all inbound dispatch rule
    # This routes every inbound SIP call to a fresh room and dispatches the
    # registered inbound agent worker to handle it.
    req = lkapi.CreateSIPDispatchRuleRequest(
        name="sizor-inbound-catchall",
        rule=lkapi.SIPDispatchRule(
            dispatch_rule_individual=lkapi.SIPDispatchRuleIndividual(
                room_prefix="inbound-",
            )
        ),
        metadata="inbound",
    )

    rule = await lk.sip.create_sip_dispatch_rule(req)
    print(f"\nCreated dispatch rule: id={rule.sip_dispatch_rule_id}  name={rule.name}")
    print("Done — inbound calls will now be routed to your agent worker.")

    await lk.aclose()


if __name__ == "__main__":
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        print("ERROR: LIVEKIT_API_KEY / LIVEKIT_API_SECRET not set in .env")
        sys.exit(1)
    asyncio.run(main())

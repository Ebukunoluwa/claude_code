"""
Creates a LiveKit outbound SIP trunk pointing at Twilio.
Run once, then copy the printed trunk ID into .env as TWILIO_SIP_TRUNK_ID.
"""
import asyncio
import sys
sys.path.insert(0, ".")

from livekit import api as lk_api
from config.settings import settings


async def main():
    client = lk_api.LiveKitAPI(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )

    try:
        trunk = await client.sip.create_sip_outbound_trunk(
            lk_api.CreateSIPOutboundTrunkRequest(
                trunk=lk_api.SIPOutboundTrunkInfo(
                    name="NHS Agent Twilio Trunk",
                    address="sizor-ai.pstn.twilio.com",
                    numbers=[settings.twilio_phone_number],
                    auth_username="livekit",
                    auth_password="Ibukunoluwa_18",
                )
            )
        )
        print(f"\nTrunk created successfully!")
        print(f"TWILIO_SIP_TRUNK_ID={trunk.sip_trunk_id}")
        print(f"\nPaste that line into your .env file, then restart the dashboard.\n")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())

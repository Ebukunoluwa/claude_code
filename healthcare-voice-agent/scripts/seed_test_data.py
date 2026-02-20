#!/usr/bin/env python3
"""
Seed the database with a test RED-flag call so you can verify the dashboard
without running any telephony.

Usage:
    python scripts/seed_test_data.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from storage.database import init_db, get_db
from storage.models import Call, Transcript, Summary, UrgencyFlag
from storage.repositories import (
    insert_call,
    insert_transcript,
    insert_summary,
    insert_urgency_flag,
    update_call_status,
)


_TRANSCRIPT = """\
[AGENT]: Good morning, this is Sarah calling from the NHS post-appointment care line. \
Could I please speak with John Smith?
[PATIENT]: Yes, speaking.
[AGENT]: Thank you, John. Could you confirm your full name for me please?
[PATIENT]: John Smith.
[AGENT]: And could you confirm your NHS number?
[PATIENT]: 485 777 3456.
[AGENT]: Thank you, identity confirmed. This call may be recorded for quality and clinical \
purposes. Do you consent to continue?
[PATIENT]: Yes, that's fine.
[AGENT]: Overall, how are you feeling since your appointment — on a scale from 1 to 10?
[PATIENT]: About a 3. I'm not doing well at all.
[AGENT]: I'm sorry to hear that. Are you experiencing any pain? If so, what score would you give it?
[PATIENT]: Yes, chest pain, maybe a 9 out of 10. It's been getting worse since this morning.
[AGENT]: This sounds like it may require urgent medical attention. Please call 999 immediately \
or go to your nearest A&E. I'm flagging this call for immediate clinical review. \
Please seek help right now. Goodbye.
"""

_SOAP = """\
SUBJECTIVE:
Patient John Smith reports severe chest pain rated 9/10 that has been worsening since \
this morning. Overall wellbeing score of 3/10.

OBJECTIVE:
Chest pain score: 9/10. Patient self-reports worsening symptoms since morning. \
Identity verified via name and NHS number.

ASSESSMENT:
Possible acute cardiac event or other serious chest pathology. Urgent medical assessment required.

PLAN:
Patient instructed to call 999 immediately or attend nearest A&E. Call flagged RED for \
immediate clinical review. GP to be notified if 999 not called within 30 minutes.\
"""


async def seed() -> None:
    await init_db(settings.sqlite_db_path)

    call_id = str(uuid.uuid4())
    now = time.time()

    async with get_db(settings.sqlite_db_path) as db:
        # Insert call
        call = Call(
            call_id=call_id,
            patient_name="John Smith",
            nhs_number="4857773456",
            phone_number="+447700900000",
            direction="outbound",
            status="in_progress",
            started_at=now - 240,
            livekit_room=f"call-{call_id}",
        )
        await insert_call(db, call)

        # Close it
        await update_call_status(
            db,
            call_id=call_id,
            status="completed",
            ended_at=now - 60,
            duration_seconds=180,
            identity_verified=True,
        )

        # Transcript
        await insert_transcript(
            db,
            Transcript(
                transcript_id=str(uuid.uuid4()),
                call_id=call_id,
                full_text=_TRANSCRIPT,
                turn_count=10,
            ),
        )

        # Summary
        await insert_summary(
            db,
            Summary(
                summary_id=str(uuid.uuid4()),
                call_id=call_id,
                soap_note=_SOAP,
                model_used="llama3-70b-8192",
            ),
        )

        # Urgency flag
        await insert_urgency_flag(
            db,
            UrgencyFlag(
                flag_id=str(uuid.uuid4()),
                call_id=call_id,
                urgency_level="red",
                reasons=["chest pain reported", "pain score 9/10"],
            ),
        )

    print(f"Seeded RED flag call — call_id={call_id}")
    print("Visit http://localhost:8000 to see it in the dashboard.")


if __name__ == "__main__":
    asyncio.run(seed())

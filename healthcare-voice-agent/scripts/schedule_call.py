"""
CLI script to schedule and immediately dispatch a call via the Sizor backend.

Usage:
    python scripts/schedule_call.py                    # uses defaults below
    python scripts/schedule_call.py <nhs_number>
    python scripts/schedule_call.py <nhs_number> <phone_override>

The patient must already exist in the Sizor dashboard.
A CallSchedule entry is created in Sizor (scheduled 1 second in the past so it
fires immediately), then _dispatch_due_calls() picks it up and initiates the
LiveKit SIP call.
"""
import asyncio
import logging
import sys
sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from datetime import datetime, timezone, timedelta
from sizor_ai.client import get_patient_by_nhs, create_schedule
from scheduler.call_scheduler import _dispatch_due_calls

# ── Defaults (override via CLI args or edit here) ────────────────────────────
DEFAULT_NHS_NUMBER = "165701"
# ─────────────────────────────────────────────────────────────────────────────


async def main():
    nhs_number = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NHS_NUMBER

    # 1. Look up patient in Sizor
    print(f"Looking up patient NHS={nhs_number} in Sizor...")
    patient = await get_patient_by_nhs(nhs_number)
    if not patient:
        print(f"ERROR: Patient with NHS number {nhs_number!r} not found in Sizor.")
        print("Register the patient in the Sizor dashboard first.")
        sys.exit(1)

    print(f"Found: {patient['full_name']} (patient_id={patient['patient_id']})")

    # 2. Create a schedule entry in Sizor — 1 second in the past = due immediately
    scheduled_for = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    print(f"Creating schedule in Sizor (scheduled_for={scheduled_for})...")
    result = await create_schedule(
        patient_id=patient["patient_id"],
        scheduled_for=scheduled_for,
    )
    if not result:
        print("ERROR: Failed to create schedule in Sizor — check SIZOR_API_URL and SIZOR_INTERNAL_KEY.")
        sys.exit(1)

    print(f"Schedule created — schedule_id={result.get('schedule_id')}")

    # 3. Dispatch immediately
    print("Dispatching now...")
    await _dispatch_due_calls()
    print("Done — check your phone.")


asyncio.run(main())

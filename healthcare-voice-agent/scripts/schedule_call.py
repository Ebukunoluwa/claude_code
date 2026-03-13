import asyncio
import logging
import sys
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

import time
from storage.database import init_db, get_db
from storage.models import ScheduledCall
from storage.repositories import insert_scheduled_call
from scheduler.call_scheduler import _dispatch_due_calls
from config.settings import settings
import uuid

async def main():
    await init_db(settings.sqlite_db_path)

    sc = ScheduledCall(
        scheduled_call_id=str(uuid.uuid4()),
        patient_name="Timi",
        nhs_number="165701",
        phone_number="+447888629971",
        scheduled_at=time.time() - 1,  # 1 second in the past = due immediately
    )

    async with get_db(settings.sqlite_db_path) as db:
        await insert_scheduled_call(db, sc)

    print("Call scheduled. Dispatching now...")
    await _dispatch_due_calls()
    print("Done — check your phone.")

asyncio.run(main())

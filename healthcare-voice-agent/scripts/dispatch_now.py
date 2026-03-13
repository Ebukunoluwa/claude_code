"""
Manually trigger the scheduler dispatch — useful for testing.
"""
import asyncio
import sys
sys.path.insert(0, ".")

from scheduler.call_scheduler import _dispatch_due_calls

async def main():
    print("Dispatching due calls...")
    await _dispatch_due_calls()
    print("Done.")

asyncio.run(main())

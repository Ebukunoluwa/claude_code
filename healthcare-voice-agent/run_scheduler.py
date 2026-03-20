"""
Standalone scheduler process.
Polls the Sizor AI backend for due calls and dispatches them via LiveKit SIP.

Run:
    python run_scheduler.py
"""
import asyncio
import logging
import signal

from scheduler.call_scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler running — press Ctrl+C to stop")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())

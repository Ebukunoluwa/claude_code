from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import settings
from dashboard.routes import api as api_router
from dashboard.routes import pages as pages_router
from scheduler.call_scheduler import create_scheduler
from storage.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + scheduler. Shutdown: stop scheduler."""
    # Initialise SQLite
    await init_db(settings.sqlite_db_path)
    logger.info("Database ready")

    # Pre-warm sentence-transformer (avoids cold start on first call)
    try:
        from processing.embedder import embed_text
        embed_text("warmup")
        logger.info("Embedder pre-warmed")
    except Exception as exc:
        logger.warning("Embedder warmup failed (will retry at runtime): %s", exc)

    # Start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Cleanup
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="NHS Healthcare Voice Agent Dashboard",
        version="1.0.0",
        lifespan=lifespan,
    )

    from telephony.inbound_webhook import router as twilio_router

    app.include_router(pages_router.router)
    app.include_router(api_router.router)
    app.include_router(twilio_router)

    return app


app = create_app()

# Expose templates at module level so routes can import
templates = Jinja2Templates(directory="dashboard/templates")

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import AsyncGenerator

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    nhs_number TEXT NOT NULL UNIQUE,
    phone_number TEXT NOT NULL,
    date_of_birth TEXT,
    appointment_date TEXT,
    next_appointment TEXT,
    created_at REAL NOT NULL DEFAULT (unixepoch('now','subsec'))
);

CREATE TABLE IF NOT EXISTS calls (
    call_id TEXT PRIMARY KEY,
    patient_id TEXT REFERENCES patients(patient_id),
    patient_name TEXT NOT NULL,
    nhs_number TEXT NOT NULL,
    phone_number TEXT NOT NULL DEFAULT '',
    direction TEXT NOT NULL CHECK(direction IN ('inbound','outbound')),
    status TEXT NOT NULL DEFAULT 'in_progress'
        CHECK(status IN ('in_progress','completed','failed','no_answer')),
    started_at REAL NOT NULL DEFAULT (unixepoch('now','subsec')),
    ended_at REAL,
    duration_seconds REAL,
    identity_verified INTEGER NOT NULL DEFAULT 0,
    livekit_room TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
    transcript_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES calls(call_id),
    full_text TEXT NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL DEFAULT (unixepoch('now','subsec'))
);

CREATE TABLE IF NOT EXISTS summaries (
    summary_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES calls(call_id),
    soap_note TEXT NOT NULL,
    model_used TEXT NOT NULL DEFAULT 'llama3-70b-8192',
    created_at REAL NOT NULL DEFAULT (unixepoch('now','subsec'))
);

CREATE TABLE IF NOT EXISTS urgency_flags (
    flag_id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL REFERENCES calls(call_id),
    urgency_level TEXT NOT NULL CHECK(urgency_level IN ('red','amber','green')),
    reasons TEXT NOT NULL DEFAULT '[]',
    reviewed INTEGER NOT NULL DEFAULT 0,
    reviewed_by TEXT,
    reviewed_at REAL,
    created_at REAL NOT NULL DEFAULT (unixepoch('now','subsec'))
);

CREATE TABLE IF NOT EXISTS scheduled_calls (
    scheduled_call_id TEXT PRIMARY KEY,
    patient_id TEXT REFERENCES patients(patient_id),
    patient_name TEXT NOT NULL,
    nhs_number TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    scheduled_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','dispatched','cancelled')),
    dispatched_call_id TEXT REFERENCES calls(call_id),
    created_at REAL NOT NULL DEFAULT (unixepoch('now','subsec'))
);

CREATE INDEX IF NOT EXISTS idx_calls_status   ON calls(status);
CREATE INDEX IF NOT EXISTS idx_urgency_level  ON urgency_flags(urgency_level);
CREATE INDEX IF NOT EXISTS idx_urgency_call   ON urgency_flags(call_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_time ON scheduled_calls(scheduled_at, status);
"""


async def init_db(db_path: str) -> None:
    """Create the database file, parent directories, and all tables."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Database initialised at %s", db_path)


async def get_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager yielding a WAL-mode connection."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db

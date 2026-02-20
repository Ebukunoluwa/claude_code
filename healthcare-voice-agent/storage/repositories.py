from __future__ import annotations

import json
import logging
import time
from typing import Optional

import aiosqlite

from storage.models import Call, Patient, ScheduledCall, Summary, Transcript, UrgencyFlag

logger = logging.getLogger(__name__)


# ── Patients ──────────────────────────────────────────────────────────────────

async def upsert_patient(db: aiosqlite.Connection, patient: Patient) -> None:
    await db.execute(
        """
        INSERT INTO patients (patient_id, full_name, nhs_number, phone_number,
                              date_of_birth, appointment_date, next_appointment)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(patient_id) DO UPDATE SET
            full_name=excluded.full_name,
            nhs_number=excluded.nhs_number,
            phone_number=excluded.phone_number,
            date_of_birth=excluded.date_of_birth,
            appointment_date=excluded.appointment_date,
            next_appointment=excluded.next_appointment
        """,
        (
            patient.patient_id,
            patient.full_name,
            patient.nhs_number,
            patient.phone_number,
            patient.date_of_birth,
            patient.appointment_date,
            patient.next_appointment,
        ),
    )
    await db.commit()


async def get_patient_by_nhs(db: aiosqlite.Connection, nhs_number: str) -> Optional[Patient]:
    async with db.execute(
        "SELECT * FROM patients WHERE nhs_number = ?", (nhs_number,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return Patient(
        patient_id=row["patient_id"],
        full_name=row["full_name"],
        nhs_number=row["nhs_number"],
        phone_number=row["phone_number"],
        date_of_birth=row["date_of_birth"],
        appointment_date=row["appointment_date"],
        next_appointment=row["next_appointment"],
        created_at=row["created_at"],
    )


# ── Calls ─────────────────────────────────────────────────────────────────────

async def insert_call(db: aiosqlite.Connection, call: Call) -> None:
    await db.execute(
        """
        INSERT INTO calls (call_id, patient_id, patient_name, nhs_number,
                           phone_number, direction, status, started_at,
                           identity_verified, livekit_room)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            call.call_id,
            call.patient_id,
            call.patient_name,
            call.nhs_number,
            call.phone_number,
            call.direction,
            call.status,
            call.started_at or time.time(),
            int(call.identity_verified),
            call.livekit_room,
        ),
    )
    await db.commit()


async def update_call_status(
    db: aiosqlite.Connection,
    call_id: str,
    status: str,
    ended_at: Optional[float] = None,
    duration_seconds: Optional[float] = None,
    identity_verified: Optional[bool] = None,
) -> None:
    fields = ["status = ?"]
    values: list = [status]
    if ended_at is not None:
        fields.append("ended_at = ?")
        values.append(ended_at)
    if duration_seconds is not None:
        fields.append("duration_seconds = ?")
        values.append(duration_seconds)
    if identity_verified is not None:
        fields.append("identity_verified = ?")
        values.append(int(identity_verified))
    values.append(call_id)
    await db.execute(f"UPDATE calls SET {', '.join(fields)} WHERE call_id = ?", values)
    await db.commit()


async def get_call(db: aiosqlite.Connection, call_id: str) -> Optional[Call]:
    async with db.execute("SELECT * FROM calls WHERE call_id = ?", (call_id,)) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_call(row)


async def list_calls(
    db: aiosqlite.Connection,
    limit: int = 100,
    offset: int = 0,
) -> list[Call]:
    async with db.execute(
        "SELECT * FROM calls ORDER BY started_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_call(r) for r in rows]


def _row_to_call(row: aiosqlite.Row) -> Call:
    return Call(
        call_id=row["call_id"],
        patient_id=row["patient_id"],
        patient_name=row["patient_name"],
        nhs_number=row["nhs_number"],
        phone_number=row["phone_number"],
        direction=row["direction"],
        status=row["status"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        duration_seconds=row["duration_seconds"],
        identity_verified=bool(row["identity_verified"]),
        livekit_room=row["livekit_room"],
    )


# ── Transcripts ───────────────────────────────────────────────────────────────

async def insert_transcript(db: aiosqlite.Connection, transcript: Transcript) -> None:
    await db.execute(
        """
        INSERT INTO transcripts (transcript_id, call_id, full_text, turn_count)
        VALUES (?, ?, ?, ?)
        """,
        (
            transcript.transcript_id,
            transcript.call_id,
            transcript.full_text,
            transcript.turn_count,
        ),
    )
    await db.commit()


async def get_transcript_by_call(
    db: aiosqlite.Connection, call_id: str
) -> Optional[Transcript]:
    async with db.execute(
        "SELECT * FROM transcripts WHERE call_id = ?", (call_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return Transcript(
        transcript_id=row["transcript_id"],
        call_id=row["call_id"],
        full_text=row["full_text"],
        turn_count=row["turn_count"],
        created_at=row["created_at"],
    )


# ── Summaries ─────────────────────────────────────────────────────────────────

async def insert_summary(db: aiosqlite.Connection, summary: Summary) -> None:
    await db.execute(
        """
        INSERT INTO summaries (summary_id, call_id, soap_note, model_used)
        VALUES (?, ?, ?, ?)
        """,
        (summary.summary_id, summary.call_id, summary.soap_note, summary.model_used),
    )
    await db.commit()


async def get_summary_by_call(
    db: aiosqlite.Connection, call_id: str
) -> Optional[Summary]:
    async with db.execute(
        "SELECT * FROM summaries WHERE call_id = ?", (call_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return Summary(
        summary_id=row["summary_id"],
        call_id=row["call_id"],
        soap_note=row["soap_note"],
        model_used=row["model_used"],
        created_at=row["created_at"],
    )


# ── Urgency Flags ─────────────────────────────────────────────────────────────

async def insert_urgency_flag(db: aiosqlite.Connection, flag: UrgencyFlag) -> None:
    await db.execute(
        """
        INSERT INTO urgency_flags (flag_id, call_id, urgency_level, reasons)
        VALUES (?, ?, ?, ?)
        """,
        (
            flag.flag_id,
            flag.call_id,
            flag.urgency_level,
            json.dumps(flag.reasons),
        ),
    )
    await db.commit()


async def mark_flag_reviewed(
    db: aiosqlite.Connection,
    flag_id: str,
    reviewed_by: str,
) -> None:
    await db.execute(
        """
        UPDATE urgency_flags
        SET reviewed = 1, reviewed_by = ?, reviewed_at = unixepoch('now','subsec')
        WHERE flag_id = ?
        """,
        (reviewed_by, flag_id),
    )
    await db.commit()


async def get_flag_by_call(
    db: aiosqlite.Connection, call_id: str
) -> Optional[UrgencyFlag]:
    async with db.execute(
        "SELECT * FROM urgency_flags WHERE call_id = ?", (call_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_flag(row)


async def list_flags(
    db: aiosqlite.Connection,
    urgency_level: Optional[str] = None,
    reviewed: Optional[bool] = None,
    limit: int = 200,
) -> list[UrgencyFlag]:
    conditions: list[str] = []
    params: list = []
    if urgency_level:
        conditions.append("urgency_level = ?")
        params.append(urgency_level)
    if reviewed is not None:
        conditions.append("reviewed = ?")
        params.append(int(reviewed))
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    async with db.execute(
        f"SELECT * FROM urgency_flags {where} ORDER BY created_at DESC LIMIT ?",
        params,
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_flag(r) for r in rows]


def _row_to_flag(row: aiosqlite.Row) -> UrgencyFlag:
    return UrgencyFlag(
        flag_id=row["flag_id"],
        call_id=row["call_id"],
        urgency_level=row["urgency_level"],
        reasons=json.loads(row["reasons"]),
        reviewed=bool(row["reviewed"]),
        reviewed_by=row["reviewed_by"],
        reviewed_at=row["reviewed_at"],
        created_at=row["created_at"],
    )


# ── Scheduled Calls ───────────────────────────────────────────────────────────

async def insert_scheduled_call(
    db: aiosqlite.Connection, sc: ScheduledCall
) -> None:
    await db.execute(
        """
        INSERT INTO scheduled_calls
            (scheduled_call_id, patient_id, patient_name, nhs_number,
             phone_number, scheduled_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sc.scheduled_call_id,
            sc.patient_id,
            sc.patient_name,
            sc.nhs_number,
            sc.phone_number,
            sc.scheduled_at,
            sc.status,
        ),
    )
    await db.commit()


async def get_pending_scheduled_calls(
    db: aiosqlite.Connection, before_ts: float
) -> list[ScheduledCall]:
    async with db.execute(
        """
        SELECT * FROM scheduled_calls
        WHERE status = 'pending' AND scheduled_at <= ?
        ORDER BY scheduled_at ASC
        """,
        (before_ts,),
    ) as cur:
        rows = await cur.fetchall()
    return [
        ScheduledCall(
            scheduled_call_id=r["scheduled_call_id"],
            patient_id=r["patient_id"],
            patient_name=r["patient_name"],
            nhs_number=r["nhs_number"],
            phone_number=r["phone_number"],
            scheduled_at=r["scheduled_at"],
            status=r["status"],
            dispatched_call_id=r["dispatched_call_id"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


async def mark_scheduled_call_dispatched(
    db: aiosqlite.Connection,
    scheduled_call_id: str,
    dispatched_call_id: str,
) -> None:
    await db.execute(
        """
        UPDATE scheduled_calls
        SET status = 'dispatched', dispatched_call_id = ?
        WHERE scheduled_call_id = ?
        """,
        (dispatched_call_id, scheduled_call_id),
    )
    await db.commit()

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Patient:
    patient_id: str
    full_name: str
    nhs_number: str
    phone_number: str
    date_of_birth: Optional[str] = None
    appointment_date: Optional[str] = None
    next_appointment: Optional[str] = None
    created_at: Optional[float] = None


@dataclass
class Call:
    call_id: str
    patient_name: str
    nhs_number: str
    direction: str  # 'inbound' | 'outbound'
    phone_number: str = ""
    patient_id: Optional[str] = None
    status: str = "in_progress"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    identity_verified: bool = False
    livekit_room: Optional[str] = None


@dataclass
class Transcript:
    transcript_id: str
    call_id: str
    full_text: str
    turn_count: int = 0
    created_at: Optional[float] = None


@dataclass
class Summary:
    summary_id: str
    call_id: str
    soap_note: str
    model_used: str = "llama3-70b-8192"
    created_at: Optional[float] = None


@dataclass
class UrgencyFlag:
    flag_id: str
    call_id: str
    urgency_level: str  # 'red' | 'amber' | 'green'
    reasons: list[str] = field(default_factory=list)
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[float] = None
    created_at: Optional[float] = None


@dataclass
class ScheduledCall:
    scheduled_call_id: str
    patient_name: str
    nhs_number: str
    phone_number: str
    scheduled_at: float
    patient_id: Optional[str] = None
    status: str = "pending"
    dispatched_call_id: Optional[str] = None
    created_at: Optional[float] = None

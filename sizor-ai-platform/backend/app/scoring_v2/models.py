"""
Pydantic models defining the contract between extraction (LLM) and scoring (deterministic).

Keep these rigid. Any change to these schemas is a scoring version bump and must be
logged for DCB0129 audit purposes.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, confloat, conint


# --- Enums ---

class RiskBand(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class RedFlagType(str, Enum):
    CHEST_PAIN = "chest_pain"
    ACUTE_SOB = "acute_shortness_of_breath"
    SUICIDAL_IDEATION = "suicidal_ideation"
    SEPSIS_SIGNS = "sepsis_signs"
    HAEMORRHAGE = "haemorrhage"
    NEW_FOCAL_NEURO = "new_focal_neuro"
    ANAPHYLAXIS = "anaphylaxis"
    PATHWAY_SPECIFIC = "pathway_specific"


# --- Extraction layer output (LLM produces this) ---

class DomainObservation(BaseModel):
    """One domain's extracted clinical signal from a single call."""
    domain: str  # e.g. "pain", "breathlessness", "wound", "mood", "adherence"
    raw_score: conint(ge=0, le=4)  # the 0-4 anchored score
    instrument_value: float | None = None  # e.g. NRS pain = 7, PHQ-2 = 3
    instrument_name: str | None = None  # "NRS", "MRC_Dyspnoea", "PHQ-2"
    evidence_quote: str  # verbatim transcript snippet supporting the score
    confidence: confloat(ge=0, le=1)  # LLM's self-reported confidence


class RedFlag(BaseModel):
    type: RedFlagType
    evidence_quote: str
    detail: str | None = None


class AdherenceStatus(BaseModel):
    medication_taken_as_prescribed: bool
    missed_doses_reported: int = 0
    critical_medication: bool = False  # anticoagulant, insulin, immunosuppressant etc.
    evidence_quote: str | None = None


class SocialFactors(BaseModel):
    lives_alone: bool = False
    has_support_contact: bool = True
    missed_previous_call: bool = False


class CallExtraction(BaseModel):
    """Everything the LLM extracts from one call. Feed this to the scorer."""
    patient_id: str
    call_id: str
    call_timestamp: datetime
    pathway: str  # e.g. "post_cardiac_surgery", "copd", "depression"
    day_post_discharge: conint(ge=0)
    domain_observations: list[DomainObservation]
    red_flags: list[RedFlag] = Field(default_factory=list)
    adherence: AdherenceStatus
    social: SocialFactors = Field(default_factory=SocialFactors)
    extraction_model: str  # e.g. "claude-sonnet-4.5"
    extraction_schema_version: str


# --- Scoring layer output (deterministic module produces this) ---

class ScoringBreakdown(BaseModel):
    """Full transparency on how a score was computed. This IS the audit trail."""
    state_score: confloat(ge=0, le=100)
    trajectory_score: confloat(ge=0, le=100)
    modifier_total: confloat(ge=0, le=25)
    modifier_detail: dict[str, float]  # {"missed_meds": 10, "social": 5}
    w_state: float
    w_trajectory: float
    ewma_lambda: float
    expected_score_at_day: float
    smoothed_state: float  # the EWMA value post-update
    red_flag_override: bool
    red_flags_triggered: list[RedFlagType]
    rubric_version: str
    scoring_engine_version: str


class RiskScore(BaseModel):
    patient_id: str
    call_id: str
    call_timestamp: datetime
    pathway: str
    day_post_discharge: int
    final_score: confloat(ge=0, le=100)
    band: RiskBand
    breakdown: ScoringBreakdown
    recommended_action: str  # derived, clinician-facing
    next_call_interval_hours: int  # what the system will DO


class PatientHistory(BaseModel):
    """Prior scoring state needed to compute trajectory. Load from Postgres."""
    patient_id: str
    pathway: str
    prior_smoothed_state: float | None = None  # None on first call
    prior_call_count: int = 0

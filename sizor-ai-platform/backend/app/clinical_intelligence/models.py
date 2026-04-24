"""Pydantic v2 models for the clinical intelligence module.

Two categories:
  1. Clinical-content models — authored, reviewed, versioned. Every instance
     carries a validation_status that must pass clinician review before the
     content is considered production-signed-off. Default is draft.
  2. Computed / runtime models — derived from call data by deterministic
     functions. No validation_status (there's nothing to author).

SOCRATES probes split across two model shapes per PLAN.md §6A.2:
  - SocratesProbeTemplate for domains where SOCRATES applies clinically
    (pain, breathlessness/chest, wound, swelling).
  - DomainProbeSet for domains where SOCRATES doesn't fit (mood, mobility,
    appetite, bowels, fatigue, medication).

See PLAN.md §2 and §6A for the full spec.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Self, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ======================================================================
# Shared enums / aliases
# ======================================================================

ValidationStatus = Literal[
    "draft_awaiting_clinical_review",
    "clinician_reviewed",
    "production_signed_off",
]


class RiskBand(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class RedFlagCategory(str, Enum):
    CHEST_PAIN = "chest_pain"
    ACUTE_SOB = "acute_shortness_of_breath"
    SUICIDAL_IDEATION = "suicidal_ideation"
    SEPSIS_SIGNS = "sepsis_signs"
    HAEMORRHAGE = "haemorrhage"
    NEW_FOCAL_NEURO = "new_focal_neuro"
    ANAPHYLAXIS = "anaphylaxis"
    PATHWAY_SPECIFIC = "pathway_specific"


class DomainTrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"
    INSUFFICIENT_DATA = "insufficient_data"


class EscalationTier(str, Enum):
    NONE = "none"
    NEXT_CALL = "next_call"
    URGENT_GP = "urgent_gp"
    SAME_DAY = "same_day"
    EMERGENCY_999 = "999"


# ======================================================================
# SOCRATES-specific types
# ======================================================================

class SocratesDimension(str, Enum):
    SITE = "site"
    ONSET = "onset"
    CHARACTER = "character"
    RADIATION = "radiation"
    ASSOCIATIONS = "associations"
    TIME_COURSE = "time_course"
    EXACERBATING_RELIEVING = "exacerbating_relieving"
    SEVERITY = "severity"


class FieldState(str, Enum):
    """Outcome of an attempt to collect a probe dimension on one call."""
    COLLECTED = "collected"
    ASKED_PATIENT_DECLINED = "asked_patient_declined"
    ASKED_PATIENT_UNSURE = "asked_patient_unsure"
    NOT_ASKED = "not_asked"


class ConfidenceLevel(str, Enum):
    """Categorical confidence in a collected value. Deliberately not numeric
    — clinicians reason about certainty in buckets, and a 0.73 number
    implies precision the assessment doesn't have."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ======================================================================
# Clinical-content models (carry validation_status)
# ======================================================================

class DomainTrajectoryEntry(BaseModel):
    """One NICE-sourced trajectory row: per pathway, per domain, per day range.
    Clinician-authored. Phase 3 populates for the 7 missing pathways."""
    opcs_code: str
    domain: str
    day_range_start: Annotated[int, Field(ge=0)]
    day_range_end: Annotated[int, Field(ge=0)]
    expected_score: Annotated[int, Field(ge=0, le=4)]
    upper_bound_score: Annotated[int, Field(ge=0, le=4)]
    expected_state: str | None = None
    nice_source: str
    nice_quote: str | None = None
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _day_range_ordered(self) -> Self:
        if self.day_range_end < self.day_range_start:
            raise ValueError("day_range_end must be >= day_range_start")
        if self.upper_bound_score < self.expected_score:
            raise ValueError("upper_bound_score must be >= expected_score")
        return self


class PathwayPlaybook(BaseModel):
    """Per-pathway prompt script structure. Phase 4 will extend with
    per-domain prompt snippets and Restricted Mode overrides."""
    opcs_code: str
    label: str
    category: str
    nice_ids: list[str]
    monitoring_window_days: Annotated[int, Field(gt=0)]
    call_days: list[int]
    domains: list[str]
    red_flag_codes: list[str]
    socrates_trigger_policy: Literal["conditional_on_deterioration"] = (
        "conditional_on_deterioration"
    )
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")


class RequiredQuestion(BaseModel):
    """One entry in the Required Questions Manifest (Phase 3). Populated
    minimally here as a stub so the type exists for downstream imports."""
    opcs_code: str
    domain: str
    question_text: str
    required: bool = True
    day_ranges: list[tuple[int, int]] = Field(default_factory=list)
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")


class RedFlagProbe(BaseModel):
    """Patient-facing probe for one red flag. Phase 4 populates the
    patient-facing question wordings; Phase 2 defines the shape only."""
    flag_code: str
    category: RedFlagCategory
    nice_basis: str
    patient_facing_question: str
    follow_up_escalation: EscalationTier
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")


class SocratesDimensionEntry(BaseModel):
    """One dimension within a SOCRATES probe template. Carries the template
    wording (what to ask) and the collection outcome for a given call (what
    happened when we asked)."""
    dimension: SocratesDimension
    probe_wording: list[str] = Field(min_length=1)
    state: FieldState = FieldState.NOT_ASKED
    collected_value: str | None = None
    confidence: ConfidenceLevel | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _state_value_confidence_consistent(self) -> Self:
        if self.state == FieldState.COLLECTED:
            if self.collected_value is None:
                raise ValueError(
                    "collected_value is required when state == COLLECTED"
                )
            if self.confidence is None:
                raise ValueError(
                    "confidence is required when state == COLLECTED"
                )
        else:
            if self.collected_value is not None:
                raise ValueError(
                    f"collected_value must be None when state == {self.state.value}"
                )
            if self.confidence is not None:
                raise ValueError(
                    f"confidence must be None when state == {self.state.value}"
                )
        return self


class SocratesProbeTemplate(BaseModel):
    """Template + collection record for a SOCRATES-applicable domain on one
    pathway. Only includes the dimensions that clinically apply — there are
    no empty-string placeholders. Use DomainProbeSet for domains where
    SOCRATES doesn't fit."""
    pathway_opcs: str
    domain: str
    entries: list[SocratesDimensionEntry] = Field(min_length=1)
    nice_source: str
    review_notes: str | None = None
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _dimensions_unique(self) -> Self:
        seen = [e.dimension for e in self.entries]
        if len(seen) != len(set(seen)):
            raise ValueError("dimensions in entries must be unique")
        return self


class DomainProbeEntry(BaseModel):
    """A single probe for a non-SOCRATES domain. Flat — no dimension
    tagging because the framework doesn't apply."""
    probe_wording: str
    state: FieldState = FieldState.NOT_ASKED
    collected_value: str | None = None
    confidence: ConfidenceLevel | None = None
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _state_value_confidence_consistent(self) -> Self:
        if self.state == FieldState.COLLECTED:
            if self.collected_value is None:
                raise ValueError(
                    "collected_value is required when state == COLLECTED"
                )
            if self.confidence is None:
                raise ValueError(
                    "confidence is required when state == COLLECTED"
                )
        else:
            if self.collected_value is not None or self.confidence is not None:
                raise ValueError(
                    "collected_value and confidence must be None unless "
                    "state == COLLECTED"
                )
        return self


class DomainProbeSet(BaseModel):
    """Set of open-ended probes for a non-SOCRATES domain (mood, mobility,
    appetite, bowels, fatigue, adherence). The rationale field must explain
    why SOCRATES doesn't fit this domain — reviewers can't approve a
    non-SOCRATES shape without understanding why it was chosen."""
    pathway_opcs: str
    domain: str
    probes: list[DomainProbeEntry] = Field(min_length=1)
    rationale: str
    nice_source: str
    review_notes: str | None = None
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")


ProbeSet = Union[SocratesProbeTemplate, DomainProbeSet]


# ======================================================================
# Computed / runtime models (no validation_status)
# ======================================================================

class DomainScore(BaseModel):
    """One domain's extracted 0-4 score for one call. Produced by the LLM
    extraction layer; consumed by scoring. Replaces the scoring_v2
    DomainObservation with a slimmer field set (instrument_value /
    instrument_name were never populated)."""
    domain: str
    raw_score: Annotated[int, Field(ge=0, le=4)]
    scale_input: Annotated[int, Field(ge=0, le=10)] | None = None
    evidence_quote: str
    confidence: ConfidenceLevel
    model_config = ConfigDict(extra="forbid", frozen=True)


class SmoothedScore(BaseModel):
    """EWMA output per-domain. Replaces the SmoothedScores dataclass in
    app/clinical/smoothing.py. Phase 5 will add asymmetric smoothing and
    hard pass-throughs; this Pydantic shape is the stable interface."""
    pain: float | None = None
    breathlessness: float | None = None
    mobility: float | None = None
    appetite: float | None = None
    mood: float | None = None
    max_smoothed: Annotated[float, Field(ge=0)]
    modifier_total: Annotated[float, Field(ge=0)]
    modifier_detail: dict[str, float] = Field(default_factory=dict)
    lam: Annotated[float, Field(ge=0, le=1)]
    model_config = ConfigDict(extra="forbid")


class DomainClassification(BaseModel):
    """Output of score_patient_domain — per-domain classification used by
    compute_overall_call_status. Phase 2 replaces the old ScoreResult
    dataclass with this Pydantic shape."""
    domain: str
    score: Annotated[int, Field(ge=0, le=4)]
    expected: Annotated[int, Field(ge=0, le=4)]
    upper_bound: Annotated[int, Field(ge=0, le=4)]
    above_upper_bound: bool
    trajectory: DomainTrend
    ftp_flag: bool
    escalation_flag: bool
    escalation_tier: EscalationTier
    nice_basis: str | None = None
    model_config = ConfigDict(extra="forbid")


class CallRiskAssessment(BaseModel):
    """Pydantic surface over app/clinical/risk_score.py's RiskScoreBreakdown
    dataclass. Wraps the live scorer's output. Fields mirror the dataclass
    so the existing compute_risk_score can be adapted without behaviour
    change — see PLAN.md §PY3."""
    final_score: Annotated[float, Field(ge=0, le=100)]
    band: RiskBand
    worst_symptom_component: Annotated[float, Field(ge=0, le=100)]
    mood_component: Annotated[float, Field(ge=0, le=100)]
    ftp_component: Annotated[float, Field(ge=0, le=100)]
    modifier_component: Annotated[float, Field(ge=0, le=100)]
    day_factor_component: Annotated[float, Field(ge=0, le=100)]
    weighted_worst_symptom: float
    weighted_mood: float
    weighted_ftp: float
    weighted_modifiers: float
    weighted_day_factor: float
    red_flag_floor_applied: bool
    acute_symptom_floor_applied: bool
    dominant_driver: str
    model_config = ConfigDict(extra="forbid")


class OverallCallStatus(BaseModel):
    """Output of compute_overall_call_status — the single GREEN/AMBER/RED
    status for one call, combining Red Flag override, Double-Amber rule,
    and the live CallRiskAssessment band. primary_reason identifies which
    rule fired; contributing lists the domains that drove it."""
    band: RiskBand
    primary_reason: Literal[
        "red_flag_override",
        "double_amber",
        "call_risk_assessment_band",
    ]
    contributing: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class CoverageReport(BaseModel):
    """Phase 3: result of comparing a transcript against the Required
    Questions Manifest. Stub fields defined here so the shape exists for
    downstream imports; Phase 3 extends with more detail."""
    opcs_code: str
    call_id: str
    asked: list[str] = Field(default_factory=list)
    missed: list[str] = Field(default_factory=list)
    asked_but_unanswered: list[str] = Field(default_factory=list)
    coverage_pct: Annotated[float, Field(ge=0, le=100)] = 0.0
    model_config = ConfigDict(extra="forbid")


class ValidationWarning(BaseModel):
    """One warning from validate_extraction_plausibility. Non-blocking —
    the caller chooses what to do (log, store, surface to clinician).

    codes are a closed Literal (no open-ended "..." per approved Q3 —
    the validation module is deliberately TIGHT in Phase 2: exactly the
    two named detectors, no generalisation. Extending this Literal is
    a PLAN-level scope decision, not a drive-by edit."""
    code: Literal[
        "first_call_all_fours",
        "all_domains_dropped_to_empty",
    ]
    severity: Literal["info", "warn"]
    detail: str
    affected_domains: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class PromptContext(BaseModel):
    """Phase 4/6: the full bundle assembled before each call, consumed by
    the prompt builder. Stub shape defined here; Phase 4/6 populates. The
    restricted_mode flag drives the PII-stripped prompt path when identity
    verification fails."""
    patient_id: str
    nhs_number: str
    playbook: PathwayPlaybook
    recent_call_summaries: list[dict] = Field(default_factory=list)
    smoothed_state: SmoothedScore | None = None
    active_red_flags: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    restricted_mode: bool = False
    model_config = ConfigDict(extra="forbid")

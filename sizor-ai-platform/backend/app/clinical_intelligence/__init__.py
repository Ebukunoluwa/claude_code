"""Sizor clinical intelligence — consolidated module.

Replaces the split app/clinical/ and app/scoring_v2/ packages. Owns:
  - Pydantic models for clinical content and computed runtime objects.
  - The categorical 0-10 -> 0-4 mapping.
  - Per-domain and overall call scoring.
  - Plausibility validation.
  - Pathway registry (domains, trajectories, probes, playbooks).
  - Coverage enforcement (Phase 3).
  - Prompt builder (Phase 4+).

Public API is re-exported here for stable imports. Module-private helpers
live in prefixed files (e.g. pathways/_probes.py) and are not re-exported.
"""
from .models import (
    CallRiskAssessment,
    ConfidenceLevel,
    CoverageReport,
    DomainClassification,
    DomainProbeEntry,
    DomainProbeSet,
    DomainScore,
    DomainTrajectoryEntry,
    DomainTrend,
    EscalationTier,
    FieldState,
    OverallCallStatus,
    PathwayPlaybook,
    PromptContext,
    RedFlagCategory,
    RedFlagProbe,
    RequiredQuestion,
    RiskBand,
    SmoothedScore,
    SocratesDimension,
    SocratesDimensionEntry,
    SocratesProbeTemplate,
    ValidationStatus,
)
from .scoring import (
    compute_overall_call_status,
    score_0_10_to_0_4,
    score_patient_domain,
)

__all__ = [
    # Models
    "CallRiskAssessment",
    "ConfidenceLevel",
    "CoverageReport",
    "DomainClassification",
    "DomainProbeEntry",
    "DomainProbeSet",
    "DomainScore",
    "DomainTrajectoryEntry",
    "DomainTrend",
    "EscalationTier",
    "FieldState",
    "OverallCallStatus",
    "PathwayPlaybook",
    "PromptContext",
    "RedFlagCategory",
    "RedFlagProbe",
    "RequiredQuestion",
    "RiskBand",
    "SmoothedScore",
    "SocratesDimension",
    "SocratesDimensionEntry",
    "SocratesProbeTemplate",
    "ValidationStatus",
    # Scoring
    "compute_overall_call_status",
    "score_0_10_to_0_4",
    "score_patient_domain",
]

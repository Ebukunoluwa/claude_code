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

__all__ = [
    "CallRiskAssessment",
    "ConfidenceLevel",
    "CoverageReport",
    "DomainClassification",
    "DomainProbeEntry",
    "DomainProbeSet",
    "DomainScore",
    "DomainTrajectoryEntry",
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
]

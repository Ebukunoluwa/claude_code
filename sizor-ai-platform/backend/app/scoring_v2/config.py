"""
Pathway configuration: domain weights, expected recovery curves, rubric versions.

Configs live in YAML so clinical reviewers can edit without code changes.
Every config load captures a version hash for audit.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, confloat


class DomainWeight(BaseModel):
    domain: str
    weight: confloat(ge=0, le=1)


class ExpectedCurvePoint(BaseModel):
    day: int
    expected_score: confloat(ge=0, le=100)


class PathwayConfig(BaseModel):
    name: str
    display_name: str
    domains: list[DomainWeight]
    expected_curve: list[ExpectedCurvePoint]
    rubric_version: str
    # Pathway-specific red flag combinations
    # Each rule: list of (domain, min_score) tuples that if ALL true -> RED
    compound_red_flags: list[list[tuple[str, int]]] = Field(default_factory=list)


class ScoringConfig(BaseModel):
    w_state: float = 0.6
    w_trajectory: float = 0.4
    ewma_lambda: float = 0.3
    modifier_cap: float = 25.0
    band_amber_threshold: float = 40.0
    band_red_threshold: float = 70.0
    engine_version: str = "1.0.0"
    pathways: dict[str, PathwayConfig]


def _validate_weights_sum_to_one(pathway: PathwayConfig) -> None:
    total = sum(d.weight for d in pathway.domains)
    if not (0.99 <= total <= 1.01):
        raise ValueError(
            f"Pathway '{pathway.name}' domain weights sum to {total}, must be 1.0"
        )


def load_config(path: Path | str) -> ScoringConfig:
    path = Path(path)
    with path.open() as f:
        raw = yaml.safe_load(f)

    pathways = {
        name: PathwayConfig(**cfg) for name, cfg in raw["pathways"].items()
    }
    for p in pathways.values():
        _validate_weights_sum_to_one(p)

    config = ScoringConfig(**{**raw["scoring"], "pathways": pathways})
    return config


def config_hash(config: ScoringConfig) -> str:
    """Stable hash of the full config. Store this with every scoring result."""
    payload = config.model_dump_json(indent=None).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def expected_score_at_day(pathway: PathwayConfig, day: int) -> float:
    """Linear interpolation between defined curve points."""
    curve = sorted(pathway.expected_curve, key=lambda p: p.day)
    if day <= curve[0].day:
        return curve[0].expected_score
    if day >= curve[-1].day:
        return curve[-1].expected_score

    for i in range(len(curve) - 1):
        a, b = curve[i], curve[i + 1]
        if a.day <= day <= b.day:
            frac = (day - a.day) / (b.day - a.day)
            return a.expected_score + frac * (b.expected_score - a.expected_score)
    return curve[-1].expected_score

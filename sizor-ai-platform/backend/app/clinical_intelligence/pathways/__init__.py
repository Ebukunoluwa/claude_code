"""Per-pathway clinical content modules.

Phase 3 end-state: 15 pathways across 6 cluster modules. This
`__init__.py` aggregates the per-cluster PATHWAYS / TRAJECTORIES /
REQUIRED_QUESTIONS / RED_FLAG_PROBES registries into module-level
dicts keyed by OPCS code, so callers can look up a pathway without
needing to know which cluster it lives in.

Clusters (modules):
  obstetric.py     R17, R18
  orthopaedic.py   W37, W38, W40, W43
  respiratory.py   J44
  surgical.py      H01, H04
  cardiac.py       K40, K40_CABG, K57, K60
  neurological.py  S01
  mental_health.py Z03_MH (SCAFFOLD ONLY — see that module's
                    CONTENT_BLOCK sentinel; no patient-facing
                    content until mental-health clinician sign-off)

Shared probe bank:
  _probes.py — generic SOCRATES / domain probe bank. Keyed by
  (pathway_opcs, domain); pathway_opcs='*' denotes the pathway-
  agnostic baseline. Per-pathway files may override entries where
  the generic baseline isn't clinically correct (no overrides
  present yet in Phase 3). Z03_MH explicitly does NOT inherit the
  generic mood DomainProbeSet.

Usage:
  from app.clinical_intelligence.pathways import (
      PATHWAYS, TRAJECTORIES, REQUIRED_QUESTIONS, RED_FLAG_PROBES,
  )
  playbook = PATHWAYS['W40']
  probes = RED_FLAG_PROBES['H01']
"""
from ..models import (
    DomainTrajectoryEntry,
    PathwayPlaybook,
    RedFlagProbe,
    RequiredQuestion,
)
from . import (
    cardiac,
    mental_health,
    neurological,
    obstetric,
    orthopaedic,
    respiratory,
    surgical,
)


# Ordered list of cluster modules. Listed in the same order as the
# docstring for predictable iteration.
_CLUSTER_MODULES = (
    obstetric,
    orthopaedic,
    respiratory,
    surgical,
    cardiac,
    neurological,
    mental_health,
)


def _merge(attr: str) -> dict:
    """Merge a per-cluster dict attribute into a single flat dict.
    Raises if two clusters claim the same OPCS code."""
    merged: dict = {}
    for mod in _CLUSTER_MODULES:
        for key, value in getattr(mod, attr).items():
            if key in merged:
                raise RuntimeError(
                    f"Duplicate OPCS code {key!r} in cluster "
                    f"{mod.__name__} — already registered by another "
                    f"cluster module. Each pathway lives in exactly one "
                    f"cluster."
                )
            merged[key] = value
    return merged


PATHWAYS: dict[str, PathwayPlaybook] = _merge("PATHWAYS")
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = _merge("TRAJECTORIES")
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = _merge("REQUIRED_QUESTIONS")
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = _merge("RED_FLAG_PROBES")


__all__ = [
    "PATHWAYS",
    "TRAJECTORIES",
    "REQUIRED_QUESTIONS",
    "RED_FLAG_PROBES",
]

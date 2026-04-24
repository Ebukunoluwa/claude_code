"""Mental health pathways — Z03_MH (scaffold only).

Phase 3 scaffold. All probe text and trajectory values are
TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF. The pathway
deliberately refuses to build content until the mental-health
clinician review completes.

Why scaffold-only:
  Mental-health content carries higher risk than any other pathway.
  Poorly-worded suicidality probes can harm; poorly-worded
  medication probes can trigger avoidance of care; probe wording
  for this cohort requires explicit mental-health clinician sign-off
  before ANY draft content is written. The generic mood DomainProbeSet
  in _probes.py is explicitly NOT inherited here (see
  pathways/__init__.py docstring).

What IS in place:
  - PathwayPlaybook registration with full domain list and red flag
    codes from upstream pathway_map.
  - Module-level PATHWAYS / TRAJECTORIES / REQUIRED_QUESTIONS /
    RED_FLAG_PROBES registries registered so the aggregator sees the
    pathway exists.
  - Empty trajectory/RQ/RFP lists + explicit TODO_AWAITING_MENTAL_
    HEALTH_CLINICIAN_SIGNOFF markers on the playbook validation
    status so no caller mistakes this for production-ready content.

What is NOT in place:
  - Trajectory values (need per-domain psychiatric baselines +
    recovery curves from a mental-health clinician).
  - Required questions (need trauma-informed wording review).
  - Red flag probes (suicidality probes in particular need explicit
    non-judgmental phrasing sign-off; Zero Suicide framework
    awareness).
  - Generic mood probe inheritance — Z03_MH explicitly does NOT
    import the generic DomainProbeSet for mood.

Primary NICE sources: CG136 (service user experience in adult mental
health), NG10 (violence and aggression), QS80 (mental-health
crisis). Reviewer specialty: Mental-health clinician (psychiatrist
or senior CMHT nurse) — explicit sign-off required before any
content added to this file.
"""
from ..models import (
    DomainTrajectoryEntry,
    PathwayPlaybook,
    RedFlagProbe,
    RequiredQuestion,
)


# Module-level content-block sentinel. The PathwayPlaybook validation_
# status field is a strict Pydantic Literal that does not accept this
# sentinel; we therefore use "draft_awaiting_clinical_review" on the
# playbook itself (the weakest of three permitted values) and mark
# the stronger content-block state here. Any caller that iterates
# PATHWAYS and sees Z03_MH MUST additionally check for this sentinel
# before consuming Z03_MH content downstream.
CONTENT_BLOCK = "TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF"

# Used on the PathwayPlaybook validation_status (Pydantic Literal
# constraint — accepts only the three enum values).
_DRAFT = "draft_awaiting_clinical_review"


# ═══════════════════════════════════════════════════════════════════════
# Z03_MH — Acute Psychiatric Admission (SCAFFOLD ONLY)
# ═══════════════════════════════════════════════════════════════════════
# No patient-facing content below this point. All fields requiring
# clinical sign-off are empty. Content is blocked by the module-level
# CONTENT_BLOCK sentinel above.

Z03_MH_PLAYBOOK = PathwayPlaybook(
    opcs_code="Z03_MH",
    label="Acute Psychiatric Admission",
    category="mental_health",
    nice_ids=["CG136", "NG10", "QS80"],
    monitoring_window_days=90,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60, 90],
    domains=[
        "medication_concordance",
        "mood_and_mental_state",
        "safety_and_safeguarding",
        "community_team_engagement",
        "crisis_plan_awareness",
        "social_support_and_daily_living",
        "substance_use_screen",
    ],
    red_flag_codes=[
        "suicidal_ideation_active",
        "medication_stopped_abruptly",
        "psychotic_relapse",
        "risk_to_others",
        "safeguarding_concern",
        "missing_from_contact",
    ],
    validation_status=_DRAFT,
)


# Trajectory values intentionally absent — trajectory expected-score /
# upper-bound curves for psychiatric recovery require specialty
# clinical sign-off. A callable that tries to resolve a benchmark for
# Z03_MH should raise or return TODO, not silently produce a number.
Z03_MH_TRAJECTORIES: list[DomainTrajectoryEntry] = []


# Required questions intentionally absent — trauma-informed wording
# review required before drafting. The generic mood DomainProbeSet in
# _probes.py is explicitly NOT inherited.
Z03_MH_REQUIRED_QUESTIONS: list[RequiredQuestion] = []


# Red flag probes intentionally absent — suicidality probes in
# particular require explicit non-judgmental wording sign-off under
# the Zero Suicide framework. No draft content.
Z03_MH_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {}


# ─── Module-level registries ───────────────────────────────────────────
# Registered with empty content so the aggregator can enumerate
# Z03_MH alongside the 14 active pathways without special-casing.

PATHWAYS: dict[str, PathwayPlaybook] = {
    "Z03_MH": Z03_MH_PLAYBOOK,
}
TRAJECTORIES: dict[str, list[DomainTrajectoryEntry]] = {
    "Z03_MH": Z03_MH_TRAJECTORIES,
}
REQUIRED_QUESTIONS: dict[str, list[RequiredQuestion]] = {
    "Z03_MH": Z03_MH_REQUIRED_QUESTIONS,
}
RED_FLAG_PROBES: dict[str, dict[str, RedFlagProbe]] = {
    "Z03_MH": Z03_MH_RED_FLAG_PROBES,
}

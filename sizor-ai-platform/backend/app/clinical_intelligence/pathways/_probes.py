"""Generic pathway-agnostic probe bank.

Ported from healthcare-voice-agent/agent/system_prompt.py::_socrates_probes
(see git blame of that file for authorship). Applied the two-model split
from PLAN.md §6A.2:

  - SOCRATES-applicable domains (symptom assessment): pain, breathlessness/
    chest, wound, swelling — built as SocratesProbeTemplate with only the
    dimensions that clinically apply.
  - Non-SOCRATES domains (functional / behavioural / mood): mobility,
    appetite, bowels/bladder, mood, fatigue, medication, generic fallback
    — built as DomainProbeSet with flat probe lists.

Every entry carries validation_status='draft_awaiting_clinical_review'
and a review_notes field flagging what the reviewer should check. See
PLAN.md §6A.3 for per-family CLINICAL_REVIEW_NEEDED detail.

Z03_MH carve-out: the generic mood DomainProbeSet (pathway_opcs='*') is
intentionally available. When mental_health.py is built in Phase 3, it
MUST NOT import or inherit this generic mood content — Z03_MH mood
probes require explicit mental-health clinician sign-off and are
TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF until then.

Access: PROBE_REGISTRY keyed by (pathway_opcs, domain). Use
get_probe_set(pathway, domain) for lookup with pathway-agnostic fallback.
"""
from __future__ import annotations

from ..models import (
    DomainProbeEntry,
    DomainProbeSet,
    ProbeSet,
    SocratesDimension,
    SocratesDimensionEntry,
    SocratesProbeTemplate,
)


NICE_GENERIC = "post-discharge general assessment (pre-Phase 3 baseline)"


# ======================================================================
# SOCRATES-applicable families
# ======================================================================

PAIN_PROBE = SocratesProbeTemplate(
    pathway_opcs="*",
    domain="pain",
    nice_source=NICE_GENERIC,
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: original content covered S/C/T/R/E/Severity "
        "informally. Mapping to dimensions is a first-pass interpretation. "
        "Onset dimension is absent — confirm whether that's intentional for "
        "the post-discharge context or whether an Onset probe should be added."
    ),
    entries=[
        SocratesDimensionEntry(
            dimension=SocratesDimension.SITE,
            probe_wording=[
                "Whereabouts exactly — can you point to the area or describe where it is?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.CHARACTER,
            probe_wording=[
                "What does it feel like — sharp, dull, burning, throbbing, or something else?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.TIME_COURSE,
            probe_wording=[
                "Is it there all the time, or does it come and go?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.RADIATION,
            probe_wording=[
                "Does it spread anywhere — like down your arm, into your back, or anywhere else?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.EXACERBATING_RELIEVING,
            probe_wording=[
                "What makes it better, and what makes it worse?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.SEVERITY,
            probe_wording=[
                "How is it affecting what you can do — is it stopping you from sleeping, moving, or doing things around the house?",
            ],
        ),
    ],
)


BREATHLESSNESS_PROBE = SocratesProbeTemplate(
    pathway_opcs="*",
    domain="breathlessness",
    nice_source=NICE_GENERIC,
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: original content bundles breathlessness and "
        "chest symptoms together. Clinically these may want separate templates "
        "— confirm whether to split chest symptoms into its own entry in Phase 3."
    ),
    entries=[
        SocratesDimensionEntry(
            dimension=SocratesDimension.ONSET,
            probe_wording=[
                "When does it come on — at rest, or when you're moving around?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.SEVERITY,
            probe_wording=[
                "How far can you walk before you notice it?",
                "Are you able to hold a conversation comfortably, or do you need to stop and catch your breath?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.TIME_COURSE,
            probe_wording=[
                "Is it getting worse, staying the same, or improving since you left hospital?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.ASSOCIATIONS,
            probe_wording=[
                "Any chest tightness, pain, or a cough alongside it?",
            ],
        ),
    ],
)


WOUND_PROBE = SocratesProbeTemplate(
    pathway_opcs="*",
    domain="wound",
    nice_source=NICE_GENERIC,
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: wound assessment is inspection-style rather "
        "than symptom-assessment. SOCRATES framing is a reach — confirm with "
        "reviewers whether a dedicated WoundInspectionProbe shape is preferred, "
        "or whether continuing with SocratesProbeTemplate here is acceptable."
    ),
    entries=[
        SocratesDimensionEntry(
            dimension=SocratesDimension.CHARACTER,
            probe_wording=[
                "How does it look — is the skin closed, and what colour is it around the area?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.ASSOCIATIONS,
            probe_wording=[
                "Any redness, swelling, or warmth around it?",
                "Is there any discharge or fluid coming from it — and if so, what does it look like?",
                "Any fever or chills alongside it?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.TIME_COURSE,
            probe_wording=[
                "Has the appearance changed at all since your last dressing check?",
            ],
        ),
    ],
)


SWELLING_PROBE = SocratesProbeTemplate(
    pathway_opcs="*",
    domain="swelling",
    nice_source=NICE_GENERIC,
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: covers Site, Time, Character, Associations. "
        "Severity dimension missing — confirm whether a functional-impact probe "
        "should be added."
    ),
    entries=[
        SocratesDimensionEntry(
            dimension=SocratesDimension.SITE,
            probe_wording=[
                "Whereabouts is the swelling — one leg, both legs, your ankles, or somewhere else?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.TIME_COURSE,
            probe_wording=[
                "Is it worse at a particular time of day — like in the evening?",
                "Has it changed since you left hospital — better, worse, or the same?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.CHARACTER,
            probe_wording=[
                "Is the skin tight or shiny over the swollen area?",
            ],
        ),
        SocratesDimensionEntry(
            dimension=SocratesDimension.ASSOCIATIONS,
            probe_wording=[
                "Any redness, pain, or warmth in the swollen area?",
            ],
        ),
    ],
)


# ======================================================================
# Non-SOCRATES families (DomainProbeSet with rationale)
# ======================================================================

MOBILITY_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="mobility",
    nice_source=NICE_GENERIC,
    rationale=(
        "Mobility is a functional-status inventory, not a symptom complaint. "
        "SOCRATES dimensions (Site / Onset / Character / Radiation) don't "
        "apply. Probes ask about what the patient can currently manage, "
        "support needs, and comparison to pre-admission baseline."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: confirm fall-risk framing stays as a probe "
        "vs. promotion to a red flag trigger in Phase 4."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "What can you manage at the moment — are you able to get around "
            "the house on your own?"
        )),
        DomainProbeEntry(probe_wording=(
            "Do you need any support — like a walking frame, stick, or "
            "someone to help you?"
        )),
        DomainProbeEntry(probe_wording=(
            "Have you had any falls or near-misses since you got home?"
        )),
        DomainProbeEntry(probe_wording=(
            "How does it compare to before you went into hospital — is it improving?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is anything stopping you from doing your exercises or moving more?"
        )),
    ],
)


APPETITE_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="appetite",
    nice_source=NICE_GENERIC,
    rationale=(
        "Appetite/nutrition is a behavioural and observational domain. "
        "SOCRATES Site/Radiation don't apply. Nausea and vomiting arguably "
        "belong to a symptom-assessment template; this bundle keeps them "
        "alongside nutrition for call efficiency."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: consider splitting nausea/vomiting into a "
        "SocratesProbeTemplate entry (Onset, Time-course, Associations, "
        "Severity) separate from appetite/nutrition in Phase 3."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "Are you managing to eat regular meals, or is food feeling difficult?"
        )),
        DomainProbeEntry(probe_wording=(
            "Has your appetite changed compared to before you went into hospital?"
        )),
        DomainProbeEntry(probe_wording=(
            "Any nausea or sickness — and if so, how often?"
        )),
        DomainProbeEntry(probe_wording=(
            "Are you managing to drink enough — does your mouth feel dry?"
        )),
        DomainProbeEntry(probe_wording=(
            "Have you noticed any weight loss or your clothes feeling looser?"
        )),
    ],
)


BOWEL_BLADDER_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="bowel_bladder",
    nice_source=NICE_GENERIC,
    rationale=(
        "Bowel and bladder symptoms are observational and often red-flag-gated "
        "(blood, pain on urination). SOCRATES framing applies weakly. Probes "
        "cover function, associations, and change from baseline."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: catheter-specific probes may need their own "
        "domain entry for catheter-carrying pathways."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "Have you been able to use the toilet normally — any difficulties?"
        )),
        DomainProbeEntry(probe_wording=(
            "Any pain, burning, or discomfort when you pass urine?"
        )),
        DomainProbeEntry(probe_wording=(
            "Have your bowels opened since you left hospital?"
        )),
        DomainProbeEntry(probe_wording=(
            "Any blood in your urine or stools?"
        )),
        DomainProbeEntry(probe_wording=(
            "Any unexpected changes compared to what's normal for you?"
        )),
    ],
)


MOOD_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="mood",
    nice_source=NICE_GENERIC,
    rationale=(
        "Mood does not SOCRATES — it has no Site, Character, Radiation, or "
        "Exacerbating/Relieving in the symptom-assessment sense. Probes are "
        "open-ended, informed by PHQ-2/PHQ-9 style wellbeing check-in, and "
        "calibrated for post-surgical/post-discharge recovery."
    ),
    review_notes=(
        "CRITICAL CLINICAL_REVIEW_NEEDED: Z03_MH (Acute Psychiatric Admission) "
        "MUST NOT inherit this generic mood content. Z03_MH-specific mood "
        "probes require explicit mental-health clinician sign-off and are "
        "TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF until then. Phase 3's "
        "pathways/mental_health.py must override with an empty or TODO probe "
        "set for mood domain rather than using this '*' baseline."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "How have you been feeling in yourself — in your mood and spirits?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is there anything that's been worrying you or weighing on your mind?"
        )),
        DomainProbeEntry(probe_wording=(
            "How has your sleep been — are you managing to rest?"
        )),
        DomainProbeEntry(probe_wording=(
            "Do you feel you have enough support around you at home?"
        )),
        DomainProbeEntry(probe_wording=(
            "Are you enjoying any of the things you normally would, or has "
            "that been difficult?"
        )),
    ],
)


FATIGUE_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="fatigue",
    nice_source=NICE_GENERIC,
    rationale=(
        "Fatigue is a global symptom whose SOCRATES dimensions (Site, "
        "Radiation) don't apply. Time-course and Severity (as functional "
        "impact) are implicit in the open probes."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED is low-priority here — content is short and "
        "well-bounded. Safe to port as-is for pilot."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "How would you describe your energy levels compared to before "
            "you went into hospital?"
        )),
        DomainProbeEntry(probe_wording=(
            "Are you able to get through the day, or do you need to rest a lot?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is the tiredness improving, staying the same, or getting worse?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is it affecting your ability to eat, move around, or do things "
            "for yourself?"
        )),
    ],
)


MEDICATION_PROBE = DomainProbeSet(
    pathway_opcs="*",
    domain="medication",
    nice_source=NICE_GENERIC,
    rationale=(
        "Medication adherence is a behaviour inventory, not a symptom. "
        "SOCRATES doesn't apply at all. Probes cover adherence, barriers, "
        "and supply."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED is low-priority. Content is short and factual."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "Are you managing to take all your medications at the right times?"
        )),
        DomainProbeEntry(probe_wording=(
            "Has anything made it difficult — side effects, forgetting, or "
            "anything else?"
        )),
        DomainProbeEntry(probe_wording=(
            "Do you have enough of your medications at home, or are any "
            "running low?"
        )),
    ],
)


GENERIC_FALLBACK = DomainProbeSet(
    pathway_opcs="*",
    domain="generic",
    nice_source=NICE_GENERIC,
    rationale=(
        "Fallback for any domain not explicitly mapped above. Open-ended "
        "and SOCRATES-lite — covers Onset, Time-course, Exacerbating, and "
        "functional impact without committing to symptom framing."
    ),
    review_notes=(
        "CLINICAL_REVIEW_NEEDED: the existence of a generic fallback hides "
        "pathway+domain pairs that should have dedicated content. Phase 3 "
        "audit task — identify which pathway/domain combinations fall "
        "through to this bucket and triage."
    ),
    probes=[
        DomainProbeEntry(probe_wording=(
            "Can you describe what you've been experiencing?"
        )),
        DomainProbeEntry(probe_wording=(
            "When did you first notice it — was it before you left hospital "
            "or since you got home?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is it getting better, staying the same, or getting worse?"
        )),
        DomainProbeEntry(probe_wording=(
            "How is it affecting your day-to-day life — what can't you do "
            "because of it?"
        )),
        DomainProbeEntry(probe_wording=(
            "Is there anything that makes it better or worse?"
        )),
    ],
)


# ======================================================================
# Registry — keyed by (pathway_opcs, domain)
# ======================================================================

PROBE_REGISTRY: dict[tuple[str, str], ProbeSet] = {
    ("*", "pain"):          PAIN_PROBE,
    ("*", "breathlessness"): BREATHLESSNESS_PROBE,
    ("*", "wound"):         WOUND_PROBE,
    ("*", "swelling"):      SWELLING_PROBE,
    ("*", "mobility"):      MOBILITY_PROBE,
    ("*", "appetite"):      APPETITE_PROBE,
    ("*", "bowel_bladder"): BOWEL_BLADDER_PROBE,
    ("*", "mood"):          MOOD_PROBE,
    ("*", "fatigue"):       FATIGUE_PROBE,
    ("*", "medication"):    MEDICATION_PROBE,
    ("*", "generic"):       GENERIC_FALLBACK,
}


def get_probe_set(pathway_opcs: str, domain: str) -> ProbeSet | None:
    """Resolve a probe set for a given (pathway, domain).

    Phase 3 per-pathway files may register overrides at specific OPCS codes;
    this function checks the pathway-specific key first and falls back to
    the '*' baseline. Returns None if no baseline exists for the domain
    (caller must handle — notably for Z03_MH:mood where the baseline is
    intentionally not inherited).
    """
    # Pathway-specific overrides (populated by Phase 3 per-pathway files).
    specific = PROBE_REGISTRY.get((pathway_opcs, domain))
    if specific is not None:
        return specific
    # Z03_MH carve-out — explicitly do NOT fall back to generic mood.
    # Phase 3's mental_health.py will register its own entry (or register
    # a TODO stub). Phase 2 enforces the policy here so the generic mood
    # baseline cannot accidentally leak into a Z03_MH call.
    if pathway_opcs == "Z03_MH" and domain == "mood":
        return None
    return PROBE_REGISTRY.get(("*", domain))

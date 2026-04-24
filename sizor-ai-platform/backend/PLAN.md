# Sizor Clinical Intelligence Refactor — Plan

**Scope:** `sizor-ai-platform/backend/` only.

**Current phase:** **Phase 3** — clinical content drafting. Phases 1, 2, 2.5, and the orphan-drop all merged to `main`; `main` HEAD at `7b7ba8e` (Phase 2.5 merge commit). Previous phases archived below.

**Gate:** no clinical content gets drafted until the Phase 3 plan below is approved. Same pattern as Phase 1, Phase 2, Phase 2.5.

---

## Phase 3 — Clinical content (7 items of plan + 3 Qs)

**Branch:** `phase-3-clinical-content`
**Base:** `main` at `7b7ba8e` (post Phase 2.5 merge).

### Framing correction — "7 missing pathways" is imprecise

The original brief framed seven pathways (W38, K40_CABG, K57, S01, H04, H01, Z03_MH) as lacking NICE trajectory data. Verified on disk:

- `app/clinical_intelligence/benchmarks.py` already has per-day trajectory tuples `(expected, upper_bound, label, nice_source)` for **all 15** active pathways plus 10 others. No pathway is missing trajectory content.
- The legacy `PLAYBOOKS` dict (in the voice-agent monolith at `healthcare-voice-agent/agent/clinical_intelligence.py`) has metadata (`label`, `category`, `nice_ids`, `monitoring_window_days`, `call_days`, `domains`, `red_flags`) for all 15.

**What is genuinely missing:**

1. **Required Questions Manifest** — a per-pathway, per-day-band list of questions Sarah MUST cover. New concept introduced by this refactor. Zero content anywhere today.
2. **Patient-facing red flag probe wording** — the machine-readable `red_flags` codes exist (e.g. `wound_dehiscence`, `postpartum_haemorrhage`), but there is no patient-plain-English question phrasing stored. Zero content today.
3. **The per-cluster Python file structure** in `app/clinical_intelligence/pathways/` — the content exists in two separate sources (benchmarks.py + monolith) but isn't organised into the per-cluster `cardiac.py` / `obstetric.py` / etc. files that the brief's target architecture calls for.
4. **`validation_status` tagging** on every piece of clinical content — existing trajectories have no review status. Per the Phase 2 Pydantic models, every clinical-content entry must carry `validation_status="draft_awaiting_clinical_review"` by default.
5. **Thin or suspicious entries that need CLINICAL_REVIEW_NEEDED flags** — a subset of existing trajectory rows are likely stubs or rough guesses. These need explicit flags so the reviewing clinician knows to check them first, rather than treating the draft as equally confident across all rows.

Phase 3 therefore **ports + restructures + annotates** existing content (not "creates from scratch for 7 pathways"), and **drafts net-new** Required Questions Manifests and Red Flag Probes for all 15.

### 1. Per-pathway sourcing + reviewer specialty + known uncertainty

Ordered by clinical cluster. The "estimated trajectory rows" count is approximate based on the existing benchmarks data structure (domains × call_days).

| OPCS | Label | Primary NICE | Reviewer specialty | Est. trajectory rows | Known CLINICAL_REVIEW_NEEDED areas |
|---|---|---|---|---|---|
| W37 | Total Hip Replacement | NG226, TA455, QS48, QS89 | Orthopaedic surgeon | ~48 | VTE duration (28d vs 35d); mobility timeline day 14-21. |
| W38 | Hip Fracture / Hemiarthroplasty | NG124, NG226, QS16 | Orthopaedic surgeon / geriatrician | ~48 | Delirium screening cadence; falls-risk trajectory day 28+; VTE post-op duration. |
| W40 | Total Knee Replacement | NG226, TA304, QS48, QS89 | Orthopaedic surgeon | ~48 | Physio compliance expected curve; knee ROM timeline. |
| W43 | Unicompartmental Knee Replacement | NG226, QS48, QS89 | Orthopaedic surgeon | ~40 | Recovery timeline — generally faster than W40; existing trajectory may be too conservative. |
| K40 | Myocardial Infarction / ACS | NG185, QS99, CG172 | Cardiologist | ~54 | Dual antiplatelet duration; exercise tolerance day 14-28. |
| K40_CABG | Coronary Artery Bypass Graft | NG185, CG172, QS99, NG238 | Cardiothoracic surgeon | ~63 | Sternal precautions window; wound healing (sternal + leg harvest); arrhythmia monitoring. |
| K57 | Atrial Fibrillation | NG196, QS93, TA249 | Cardiologist | ~40 | Anticoagulation adherence; rate-control symptoms; stroke risk if non-adherent. |
| K60 | Heart Failure | CG187, NG106, QS9 | Cardiologist / HF specialist nurse | ~56 | Fluid balance; weight monitoring cadence; diuretic titration. |
| R17 | Elective Caesarean Section | NG192, QS32, NG194, NG89 | Obstetrician / community midwife | ~56 | Lochia duration outliers; postnatal depression screen timing (day 10-14 vs 6wk). |
| R18 | Emergency Caesarean Section | NG192, NG194, QS32 | Obstetrician / community midwife | ~56 | Emotional recovery trajectory (PTSD screen); same as R17 plus trauma-aware items. |
| J44 | COPD Exacerbation | NG115, QS10 | Respiratory physician / COPD nurse | ~42 | Oxygen saturation trigger thresholds; antibiotic/steroid adherence. |
| S01 | Stroke / Ischaemic | NG128, CG162, QS2, NG185 | Stroke physician / neurologist | ~72 | Speech/language timeline; mood trajectory post-stroke; secondary prevention adherence. |
| H04 | Colectomy / Bowel Surgery | NG147, QS48, NG89 | Colorectal surgeon | ~48 | Stoma care (if present); bowel function return; ERAS pathway adherence. |
| H01 | Appendectomy | NG61, QS48 | General surgeon | ~28 | Fast recovery — existing benchmarks may be too cautious; confirm day-14 expected=0. |
| Z03_MH | Acute Psychiatric Admission | CG136, NG10, QS80 | Psychiatrist (sign-off required) | N/A — scaffold only | **All content** — trajectories deliberately not ported, see §2. |

### 2. Z03_MH scaffold-only confirmation

Per original brief and user's Phase 3 direction. Confirmed file structure for `app/clinical_intelligence/pathways/mental_health.py`:

```python
"""Z03_MH — Acute Psychiatric Admission.

SCAFFOLD ONLY. All clinical probe content, trajectories, and red flag
wording are deliberately absent pending explicit sign-off from a
mental-health clinician. Importing this module must not raise, but any
function that would render a patient-facing prompt for Z03_MH must
refuse until the TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF markers
are resolved by clinical content substitution.
"""
from ..models import PathwayPlaybook, ValidationStatus

Z03_MH_PLAYBOOK = PathwayPlaybook(
    opcs_code="Z03_MH",
    label="Acute Psychiatric Admission",
    category="mental_health",
    nice_ids=["CG136", "NG10", "QS80"],
    monitoring_window_days=90,
    call_days=[1, 3, 7, 14, 21, 28, 42, 60, 90],
    domains=[
        "medication_adherence",
        "mood_and_mental_state",
        "safety_and_safeguarding",
        "community_team_engagement",
        "crisis_plan_awareness",
        "social_support_and_daily_living",
        "substance_use_screen",
    ],
    red_flag_codes=[
        "suicidal_ideation",
        "psychotic_relapse",
        "safeguarding_concern",
        "medication_non_adherence_critical",
    ],
    validation_status="draft_awaiting_clinical_review",
)

TRAJECTORIES: dict = {}        # TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF
REQUIRED_QUESTIONS: list = []  # TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF
RED_FLAG_PROBES: dict = {}     # TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF


def build_prompt(*args, **kwargs):
    raise NotImplementedError(
        "Z03_MH prompts are unavailable until clinical content sign-off "
        "replaces the TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF markers."
    )
```

Existing `benchmarks.py` Z03_MH trajectory rows are **not** deleted (they're referenced for historical audit), but `mental_health.py` **does not import them**. Phase 3's per-cluster Python structure treats Z03_MH as content-free by design.

### 3. Required Questions Manifest plan

**Structure — one `RequiredQuestion` per (pathway, domain, day-band, question) tuple.** Standard day bands:

- Day 1-3 (immediate post-discharge — safety/red-flag-heavy)
- Day 4-7 (early recovery — function + adherence)
- Day 8-14 (consolidation — any persisting concerns)
- Day 15-30 (longer-term — psychosocial + secondary prevention)
- Day 31+ (routine check / closeout — pathway-dependent end point)

Some pathways end their monitoring window before 31 — omit the later bands there (H01 ends at day 28; R17/R18 at day 42; others at 60 or 90). Day bands align with pathway `call_days` lists — a manifest row is only `required=True` for bands that overlap with actual call days.

**Worked example — R17 (Elective Caesarean Section):**

```python
# app/clinical_intelligence/pathways/obstetric.py (partial — R17 Required Questions)
R17_REQUIRED_QUESTIONS = [
    # ──────────── Day 1-3 ────────────
    RequiredQuestion(
        opcs_code="R17",
        domain="wound_healing",
        question_text="How is the wound site looking — any redness, swelling, or discharge?",
        required=True,
        day_ranges=[(1, 3), (4, 7)],
        nice_basis="NG192 §1.5.3",
        validation_status="draft_awaiting_clinical_review",
    ),
    RequiredQuestion(
        opcs_code="R17",
        domain="lochia_monitoring",
        question_text="How is your bleeding — how much are you losing, what colour, any clots?",
        required=True,
        day_ranges=[(1, 3), (4, 7), (8, 14)],
        nice_basis="NG192 §1.5.8",
        validation_status="draft_awaiting_clinical_review",
    ),
    RequiredQuestion(
        opcs_code="R17",
        domain="pain_management",
        question_text="How are you managing pain — are the painkillers helping enough to move around and care for the baby?",
        required=True,
        day_ranges=[(1, 3), (4, 7)],
        nice_basis="NG192 §1.6",
        validation_status="draft_awaiting_clinical_review",
    ),
    RequiredQuestion(
        opcs_code="R17",
        domain="vte_prophylaxis",
        question_text="Are you taking the anticoagulant injections each day, and how is the injection site?",
        required=True,
        day_ranges=[(1, 3), (4, 7), (8, 14)],
        nice_basis="NG89 §1.3",
        validation_status="draft_awaiting_clinical_review",
    ),
    RequiredQuestion(
        opcs_code="R17",
        domain="urinary_function",
        question_text="Are you passing urine normally — any pain, difficulty, or change in amount?",
        required=True,
        day_ranges=[(1, 3)],
        nice_basis="NG192 §1.5.9",
        validation_status="draft_awaiting_clinical_review",
    ),
    # ──────────── Day 4-7 ────────────
    RequiredQuestion(
        opcs_code="R17",
        domain="infant_feeding",
        question_text="How is feeding going — breast, bottle, or both, and is the baby settling?",
        required=True,
        day_ranges=[(4, 7), (8, 14)],
        nice_basis="NG194 §1.4",
        validation_status="draft_awaiting_clinical_review",
    ),
    RequiredQuestion(
        opcs_code="R17",
        domain="mood_and_emotional_wellbeing",
        question_text="How are you feeling in yourself — beyond the tiredness, any low mood or worry that's been hard to shake?",
        required=True,
        day_ranges=[(4, 7), (8, 14), (15, 30), (31, 42)],
        nice_basis="NG192 §1.6 / NG194 §1.7",
        validation_status="draft_awaiting_clinical_review",
    ),
    # ──────────── Day 15-30 ────────────
    RequiredQuestion(
        opcs_code="R17",
        domain="contraception_and_sexual_health",
        question_text="Has anyone talked with you about contraception since discharge?",
        required=True,
        day_ranges=[(15, 30), (31, 42)],
        nice_basis="NG194 §1.8",
        validation_status="draft_awaiting_clinical_review",
    ),
    # CLINICAL_REVIEW_NEEDED: postnatal depression screen timing —
    # some NICE/RCOG sources favour day 10-14 Edinburgh scale, others
    # defer to 6-week GP check. This draft places mood screen at every
    # band from day 4 onwards; reviewer should decide which call formally
    # administers the EPDS.
]
```

Notes for the reviewer:
- Every entry has `validation_status="draft_awaiting_clinical_review"` per brief non-negotiable.
- Every entry cites a NICE section so the reviewer can validate the source.
- `day_ranges` is a list of `(start, end)` tuples — a question can be required on multiple bands (e.g. mood runs across all bands from day 4).
- One `CLINICAL_REVIEW_NEEDED` comment per genuine uncertainty, with the specific question posed to the reviewer.

**Estimated manifest sizes** (per pathway, rough count of required-question rows):
- Obstetric (R17, R18): 15-20 each
- Orthopaedic (W37, W38, W40, W43): 12-15 each
- Cardiac (K40, K40_CABG, K57, K60): 15-20 each
- Surgical (H01, H04): 10-12 each
- Respiratory (J44): 15-18
- Neurological (S01): 20-25 (complex)
- Mental health (Z03_MH): 0 (scaffold only)

### 4. Red flag probe plan

**Template principle (approved by reviewer, applies across all 15 pathways):**

> **Red Flag Probes are strictly one observation per probe.** One probe asks exactly one clinical question — no compound "or" phrasing that bundles multiple independent observations. A compound question forces the patient to parse intent and often yields a single ambiguous yes/no covering distinct clinical events.
>
> **Required Questions can be multi-part but each part must be independently scoreable.** A Required Question that says "How is your wound — any redness, swelling, or discharge?" is acceptable because the transcript will capture each finding separately and the clinician reads the full answer. Red Flag Probes are the trigger for escalation and must have a clean 1:1 mapping to a specific clinical event.
>
> When a single upstream machine-readable `flag_code` (e.g. `postpartum_haemorrhage`) covers multiple distinct observations, split it into multiple probes with suffixes (`_volume`, `_clots`, `_haemodynamic`), carrying the upstream code in `parent_flag_code` so escalation logic and dashboards can aggregate back to the clinical entity.
>
> Both tone and this principle must hold across all 15 pathways.

**Structure — one `RedFlagProbe` per single-observation clinical question.** Each probe contains:
- `flag_code` — the specific probe identifier, usually a suffix variant of the upstream clinical-entity code.
- `parent_flag_code` — the upstream machine-readable `red_flags` list entry from the monolith PLAYBOOK (or `None` if 1:1 with a flag_code).
- `category` — maps to `RedFlagCategory` enum from Phase 2 models.
- `nice_basis` — citation for the clinical trigger.
- `patient_facing_question` — plain English the voice agent can read aloud. One observation.
- `follow_up_escalation` — maps to `EscalationTier` enum (999 / same_day / urgent_gp / next_call / none).

**Note on the Pydantic model:** Phase 3 adds `parent_flag_code: str | None = None` to `RedFlagProbe` in `clinical_intelligence/models.py` to support the upstream-code aggregation. This is a strictly additive change (nullable, defaults to `None` for 1:1 probes).

**Worked example — R17:**

R17 upstream red flag codes (from monolith PLAYBOOK): `wound_dehiscence`, `postpartum_haemorrhage`, `pe_symptoms`, `pre_eclampsia_signs`, `postnatal_depression_severe`, `infant_feeding_failure`. Each splits into 2–3 single-observation probes per the principle above. Total: ~14 probes.

```python
# app/clinical_intelligence/pathways/obstetric.py (partial — R17 Red Flag Probes)
R17_RED_FLAG_PROBES = {
    # ── postpartum_haemorrhage (3 probes, all 999) ──
    "postpartum_haemorrhage_volume": RedFlagProbe(
        flag_code="postpartum_haemorrhage_volume",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you been soaking through a maternity pad in less than an hour?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status="draft_awaiting_clinical_review",
    ),
    "postpartum_haemorrhage_clots": RedFlagProbe(
        flag_code="postpartum_haemorrhage_clots",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you passed any clots that were bigger than a 50p coin?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status="draft_awaiting_clinical_review",
    ),
    "postpartum_haemorrhage_haemodynamic": RedFlagProbe(
        flag_code="postpartum_haemorrhage_haemodynamic",
        parent_flag_code="postpartum_haemorrhage",
        category=RedFlagCategory.HAEMORRHAGE,
        nice_basis="NG192 §1.5.8",
        patient_facing_question=(
            "Have you felt faint, dizzy, or lightheaded — especially when you stand up?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status="draft_awaiting_clinical_review",
    ),

    # ── postnatal_depression_severe (2 probes, differentiated escalation) ──
    "postnatal_depression_passive_ideation": RedFlagProbe(
        flag_code="postnatal_depression_passive_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192",
        patient_facing_question=(
            "Have you had any thoughts that you or your family would be better "
            "off without you?"
        ),
        follow_up_escalation=EscalationTier.SAME_DAY,
        validation_status="draft_awaiting_clinical_review",
        # CLINICAL_REVIEW_NEEDED: reviewer to confirm SAME_DAY for passive
        # ideation vs EMERGENCY_999. Current draft differentiates from active.
    ),
    "postnatal_depression_active_ideation": RedFlagProbe(
        flag_code="postnatal_depression_active_ideation",
        parent_flag_code="postnatal_depression_severe",
        category=RedFlagCategory.SUICIDAL_IDEATION,
        nice_basis="NG192 §1.6 / CG192",
        patient_facing_question=(
            "Have you had any thoughts about harming yourself, or about ending "
            "your own life?"
        ),
        follow_up_escalation=EscalationTier.EMERGENCY_999,
        validation_status="draft_awaiting_clinical_review",
    ),

    # ... (further 9 probes for wound_dehiscence, pe_symptoms,
    # pre_eclampsia_signs, infant_feeding_failure — each split into
    # single-observation probes per the principle. Full content in
    # the actual obstetric.py file.)
}
```

**Tone / wording principles (applied throughout):**
- NHS-plain language, no clinical jargon (no "puerperal pyrexia", no "dyspnoea").
- Specific physical-sign anchors the patient can evaluate ("maternity pad in less than an hour", "bigger than a 50p coin").
- Invite disclosure without judgment, especially for mental-health probes.
- **One observation per probe** — the template principle above is non-negotiable across all 15 pathways.

**Scale across 15 pathways:** post-splitting, ~10-18 red flag probes per pathway (up from the pre-split ~4-8), ~150-200 total Red Flag Probe entries for Phase 3. The split increases volume but reduces ambiguity at trigger time.

### 5. Output file structure

```
app/clinical_intelligence/pathways/
  __init__.py               # registry — aggregates PATHWAYS, TRAJECTORIES,
                            #   REQUIRED_QUESTIONS, RED_FLAG_PROBES across
                            #   all cluster files; provides lookup helpers.
  _probes.py                # (existing from Phase 2) — generic SOCRATES probes.
  obstetric.py              # R17, R18 — ported first, template for the rest.
  orthopaedic.py            # W37, W38, W40, W43
  cardiac.py                # K40, K40_CABG, K57, K60
  surgical.py               # H01, H04
  respiratory.py            # J44
  neurological.py           # S01
  mental_health.py          # Z03_MH (scaffold only, §2)
```

**Per-cluster file module layout (exemplar):**

```python
"""Obstetric pathways — R17 (elective C-section), R18 (emergency C-section).

Ported from:
  - app/clinical_intelligence/benchmarks.py (DOMAIN_TRAJECTORIES)
  - healthcare-voice-agent/agent/clinical_intelligence.py (PLAYBOOKS)
with draft_awaiting_clinical_review flags and CLINICAL_REVIEW_NEEDED
annotations on uncertain entries.

NEW in this module:
  - Required Questions manifests (Phase 3 net content).
  - Patient-facing red flag probes (Phase 3 net content).
"""
from ..models import (
    DomainTrajectoryEntry, PathwayPlaybook, RedFlagCategory,
    RedFlagProbe, RequiredQuestion, EscalationTier,
)

# ── Playbook metadata ─────────────────────────────────────────────────
R17_PLAYBOOK = PathwayPlaybook(...)
R18_PLAYBOOK = PathwayPlaybook(...)

# ── Trajectories (ported from benchmarks.py, re-shaped into Pydantic) ─
R17_TRAJECTORIES: list[DomainTrajectoryEntry] = [...]
R18_TRAJECTORIES: list[DomainTrajectoryEntry] = [...]

# ── Required Questions (new content — Phase 3) ────────────────────────
R17_REQUIRED_QUESTIONS: list[RequiredQuestion] = [...]
R18_REQUIRED_QUESTIONS: list[RequiredQuestion] = [...]

# ── Red Flag Probes (new content — Phase 3) ───────────────────────────
R17_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {...}
R18_RED_FLAG_PROBES: dict[str, RedFlagProbe] = {...}

# ── Module-level registries (consumed by pathways/__init__.py) ────────
PATHWAYS = {"R17": R17_PLAYBOOK, "R18": R18_PLAYBOOK}
TRAJECTORIES = {"R17": R17_TRAJECTORIES, "R18": R18_TRAJECTORIES}
REQUIRED_QUESTIONS = {"R17": R17_REQUIRED_QUESTIONS, "R18": R18_REQUIRED_QUESTIONS}
RED_FLAG_PROBES = {"R17": R17_RED_FLAG_PROBES, "R18": R18_RED_FLAG_PROBES}
```

**`__init__.py` aggregates:**

```python
from . import cardiac, mental_health, neurological, obstetric
from . import orthopaedic, respiratory, surgical

PATHWAYS, TRAJECTORIES, REQUIRED_QUESTIONS, RED_FLAG_PROBES = {}, {}, {}, {}
for mod in (obstetric, orthopaedic, cardiac, surgical,
            respiratory, neurological, mental_health):
    PATHWAYS.update(mod.PATHWAYS)
    TRAJECTORIES.update(mod.TRAJECTORIES)
    REQUIRED_QUESTIONS.update(mod.REQUIRED_QUESTIONS)
    RED_FLAG_PROBES.update(mod.RED_FLAG_PROBES)
```

### 6. Clinician review `.md` export format

Generated programmatically from each per-cluster module via a new script: `backend/scripts/export_pathway_review.py <opcs_code>`. Output lands in `backend/docs/clinical_review/<opcs_code>.md` (new path, gitignored initially, regenerated on demand).

**Partial example output — `R17.md`:**

```markdown
# R17 — Elective Caesarean Section — Clinical Review Draft

| Field | Value |
|---|---|
| **Status** | draft_awaiting_clinical_review |
| **Primary reviewer** | Obstetrician and/or community midwifery lead |
| **NICE sources** | NG192 (postnatal care), QS32, NG194 (maternity services), NG89 (VTE) |
| **Monitoring window** | 42 days |
| **Call days** | 1, 3, 5, 7, 10, 14, 21, 28 |
| **Domains** | wound_healing, pain_management, lochia_monitoring, vte_prophylaxis, infection_signs, infant_feeding, mood_and_emotional_wellbeing, urinary_function |

## Domain trajectories

### wound_healing — NG192 §1.5.3

| Day | Expected | Upper bound | Expected state |
|---:|---:|---:|---|
| 1  | 2 | 3 | Wound intact, bruising expected |
| 3  | 2 | 3 | Healing — clips/sutures in place |
| 5  | 1 | 2 | Healing well |
| 7  | 1 | 2 | Healing well |
| 14 | 0 | 1 | Clips out, closed |
| 28 | 0 | 1 | Scar forming |
| 42 | 0 | 0 | Healed |

### lochia_monitoring — NG192 §1.5.8
(similar table)

(... other domains ...)

## Required Questions Manifest

### Day 1-3
| Domain | Question | NICE |
|---|---|---|
| wound_healing | How is the wound site looking — any redness, swelling, or discharge? | NG192 §1.5.3 |
| lochia_monitoring | How is your bleeding — how much are you losing, what colour, any clots? | NG192 §1.5.8 |
| pain_management | How are you managing pain — are the painkillers helping enough to move around and care for the baby? | NG192 §1.6 |
| vte_prophylaxis | Are you taking the anticoagulant injections each day, and how is the injection site? | NG89 §1.3 |
| urinary_function | Are you passing urine normally — any pain, difficulty, or change in amount? | NG192 §1.5.9 |

### Day 4-7
(similar table)

## Red Flag Probes

### postpartum_haemorrhage (HAEMORRHAGE → 999)
> Have you had any heavy bleeding — like soaking through a pad in less than an hour, passing clots bigger than a 50p coin, or suddenly feeling faint, dizzy, or lightheaded when you stand up?

**NICE basis:** NG192 §1.5.8

(...)

## Reviewer checklist

### Trajectory values
- [ ] Expected/upper-bound values clinically reasonable for each day+domain?
- [ ] Day-range gaps filled? (e.g. if call_days says day 10 but trajectory stops at day 7.)
- [ ] Any values that feel too conservative or too permissive?

### Required questions
- [ ] Every question covered is clinically necessary (no fluff)?
- [ ] Any missing questions the reviewer would consider essential?
- [ ] Day-band placement appropriate?
- [ ] Wording acceptable for a voice agent to read aloud?

### Red flag probes
- [ ] Patient-facing wording free of clinical jargon?
- [ ] Escalation tier (999 / same_day / urgent_gp / next_call) appropriate?
- [ ] No compound questions (one probe = one clinical question)?
- [ ] Non-judgmental framing for mental-health items?

### CLINICAL_REVIEW_NEEDED flags
(Auto-listed from the source file. Reviewer addresses each before sign-off.)
- [ ] Postnatal depression screen timing — reviewer to confirm whether EPDS is administered at day 10-14 or deferred to 6-week GP check.
- [ ] postnatal_depression_severe escalation tier — should active ideation with intent split into a separate probe with EMERGENCY_999?

## Sign-off
- Reviewer name:
- Review date:
- Revised validation_status (circle one): clinician_reviewed / production_signed_off / remains_draft_with_notes
- Comments:
```

### 7. Order of execution within Phase 3

**R17 first** — confirming your recommendation. Rationale:

- R17 is the most clinically mature in the codebase (well-developed domain list, trajectory data already scrutinised in the existing benchmarks.py entries).
- R17 exercises every piece of Phase 3 work in one pathway: trajectories to port, Required Questions to draft, red flag probes to write, CLINICAL_REVIEW_NEEDED flags to place, and `.md` export to generate.
- Once R17 is approved, R18 is a close follow — obstetric cluster is complete.
- The other clusters then follow roughly in order of clinical data maturity: respiratory (J44, single pathway, mostly ported), orthopaedic (4 pathways, existing data solid), cardiac (4, more nuance), surgical (2, straightforward), neurological (1, most complex), mental_health (scaffold only).

**Proposed commit sequence:**

1. **obstetric.py** (R17 + R18) + R17 `.md` export — gate for your review of the shape.
2. **respiratory.py** (J44) — small, fast port after R17 validation.
3. **orthopaedic.py** (W37, W38, W40, W43).
4. **surgical.py** (H01, H04).
5. **cardiac.py** (K40, K40_CABG, K57, K60).
6. **neurological.py** (S01).
7. **mental_health.py** (Z03_MH scaffold).
8. **pathways/__init__.py** aggregator + `scripts/export_pathway_review.py` exporter.

One commit per cluster. Tests green at each commit boundary. `.md` exports regenerated for every commit so reviewers see current state.

### Pre-work questions (answered)

**Q1 — Overlapping domains (wound_healing across clusters).**

**Cluster-specific.** Wound_healing in orthopaedic (hip replacement incision) has a materially different trajectory from obstetric (Pfannenstiel c-section scar) or surgical (colectomy laparotomy or laparoscopic ports). Same-name, different-clinical-reality domains:
- Different expected healing timelines (days vs weeks).
- Different red flag thresholds (wound_dehiscence on a c-section is a different presentation to hip-replacement dehiscence).
- Different NICE sources.

A "shared base" would force averaging across unlike wounds and lose clinically meaningful specificity. Cluster-specific costs more data duplication (same domain name, different entries) but is clinically correct.

**Q2 — NICE precedence rule.**

Documented as a comment at the top of each per-cluster file:

1. **NG (NICE Guideline)** is the primary source. Use the most recent NG that covers the topic.
2. **CG (Clinical Guideline)** — the legacy name for NGs; precedence follows date. If an NG has explicitly replaced a CG, the NG wins. If the NG references or defers to an older CG, cite both.
3. **QS (Quality Standard)** — evidence-ranked summary; cite alongside the primary NG but never as the sole source.
4. **TA (Technology Appraisal)** — specific to drug/device approvals; cite when the pathway explicitly hinges on an appraised technology (e.g. TA249 for AF rivaroxaban).
5. When two NGs cover overlapping territory (e.g. NG192 postnatal + NG194 maternity services), cite both in `nice_basis` with section numbers — the reviewer confirms which governs the specific question.
6. Date precedence: newer wins unless older is explicitly referenced by the newer.

**Q3 — `.md` export: one file per pathway or per cluster?**

**One file per pathway** — 14 files for the real pathways + 1 for the Z03_MH scaffold notice (confirms the reviewer doesn't need to send Mental Health content to a psychiatrist because there isn't any).

Rationale:
- A cardiologist reviewing K40 should not have to wade through K40_CABG, K57, K60 content — their review attention is a finite resource.
- File-per-pathway makes the reviewer sign-off traceable: one file, one reviewer, one timestamp, one status change.
- Generating 15 files from the same Python data structure is trivial — same script, different OPCS code argument.
- Per cluster would be cheaper to manage (7 files instead of 15), but review experience is the bottleneck, not file count.

### Estimated diff

- Per-cluster Python files: ~300-500 lines each × 7 clusters = ~2500-3500 lines.
- Pathway `__init__.py` aggregator: ~40 lines.
- `scripts/export_pathway_review.py` exporter: ~200 lines.
- 15 generated `.md` files (in `backend/docs/clinical_review/`, gitignored initially): 15 × ~150 lines = ~2250 lines generated, not reviewed as code.
- Tests (schema validation, manifest completeness, probe coverage): ~400 lines.
- **Total: ~3500-4300 lines of Python (code + data)**, plus generated `.md` exports.

Review surface is heavy on data review, not code review — this is by design. Clinical content is what's being Phase-3'd; the Python scaffolding is Phase 2 and stable.

---

## Phase 2.5 — Trajectory integrity (scope add)

**Branch:** `phase-2-5-trajectory-integrity`
**Base:** `main` at `43dfd94` (Phase 2 merge commit).
**Motivation:** three fixes surfaced by the Phase 2 `CALL_HANDLING_AUDIT.md`. All three are about keeping the longitudinal trajectory signal honest when the pipeline sees calls that shouldn't contribute (probes), priors that shouldn't be trusted (`failed` / `empty` extraction_status), or same-day noise (retry / continuation / runaway-scheduler clusters).

**Non-goals (explicit):**
- Continuation de-dup (latent, not firing in dev).
- `call_type` enum constraint at DB level (cosmetic — separate cleanup PR).
- Read-time dedup cleanup in `patients.py` (no-op post-Phase 1).
- Coverage Option A vs B (Phase 4 decision).
- `"outbound"` / `"follow-up"` drift in `call_schedule.call_type` (frontend ticket).
- Full transcript-to-ProbeAnswer extraction (Phase 4 scope).

### Pre-work answers (Q1 / Q2 / Q3)

**Q1 — Should probe calls' own risk_score still be computed?**

**Yes, but FOCUSED** over only the domains the probe asked about, not a full-domain score. Corrected per your review. The rule is two-part:

**Read / write asymmetry (unchanged):** probes **read** the trajectory but don't **write** to it.

- When scoring a probe call: load priors from the chain of non-probe extractions (retry / continuation / routine). Compute EWMA seeded by that chain's most recent smoothed state.
- When scoring any subsequent call (probe or not): the probe's row is **invisible** as a prior — the "load most recent prior" query filters it out. The chain stays unbroken through the probe.

**Focused computation (new):** the probe's `risk_score` is computed only over the domains the probe actually asked about. A probe asking only about chest pain on an otherwise stable patient must not score `risk=12` because mood/mobility/appetite were silent — it must produce a score that reflects the chest pain severity in isolation.

Mechanics:
- `ClinicalExtraction` gains a new column `scoring_scope: VARCHAR(20) NOT NULL DEFAULT 'full'`, enum-like with values `'full'` / `'probe_focused'`. The pipeline sets it per-call: `'probe_focused'` when `CallRecord.trigger_type == 'probe'`, else `'full'`.
- `compute_risk_score` gains a `scoring_scope` keyword argument.
  - `'full'`: existing behaviour — all five components (worst_symptom, mood, ftp, modifier, day_factor) weighted at their fixed weights (0.55 / 0.15 / 0.15 / 0.10 / 0.05).
  - `'probe_focused'`: only symptom-observation components (worst_symptom + mood) participate, weights **renormalised over components present**. Missing domains are EXCLUDED from the calculation, not treated as zero. `ftp`, `modifier`, and `day_factor` are skipped entirely — they are longitudinal-context features that the probe did not ask about.
  - Safety floors (red_flag_floor at 70, acute_symptom_floor at 65) still apply in both modes.
- Worked example: probe asks about pain, smoothed pain=7 → `worst_symptom = ~80`. In focused mode with only `worst_symptom` present, weights renormalise so `final_score ≈ 80`. In full mode with everything else absent/zero, `final_score = 0.55 × 80 = 44` — which under-represents the signal and is wrong for a probe.
- Dashboard rendering of the distinction (separate label, colour, etc.) is **out of Phase 2.5 scope** — the data model now carries enough metadata (`scoring_scope`) for the frontend to render it distinctly when the frontend team picks it up.

**Domain-source question (scoped for Phase 2.5):** the user's spec names `ProbeCall.questions_list` as the source of "which domains the probe asked about". Phase 2.5 uses a pragmatic proxy instead: whichever of the five scalar score fields (`pain_score`, `breathlessness_score`, `mobility_score`, `appetite_score`, `mood_score`) are non-None on the `ClinicalExtraction` are the "asked" domains. The LLM extraction pipeline populates these only for domains with transcript evidence, so this lines up with what the probe actually covered. An explicit `ProbeCall.focused_domains: list[str]` field keyed to questions_list tags is deferred to Phase 4, when the frontend UI can populate it at probe creation time. Flagged: LLM hallucination producing a false positive score on an un-asked domain would not be filtered by this Phase 2.5 proxy; Phase 4's explicit tagging closes that gap.

**Q2 — Timezone for same-day FTP collapse.**

**Europe/London.** Flagged as a platform-wide implicit assumption that should become an explicit `Patient.timezone` or `Hospital.timezone` field in a later phase. Rationale: NHS product, UK patients, BST/GMT is the clinical day boundary clinicians actually think in. The audit's own same-day grouping used `DATE(started_at)` which is UTC — this Phase 2.5 fix switches to `DATE(started_at AT TIME ZONE 'Europe/London')`.

Edge cases:
- A 23:50 UTC call in summer is 00:50 the following day in London time (BST offset). The FTP collapse groups it with the next day, not the preceding day.
- A cluster straddling midnight London-time (e.g. cut-off at 23:50 London, continuation at 00:05 London) is correctly counted as two separate clinical days under this rule. The continuation rule's 5-minute scheduling doesn't respect day boundaries, so this edge does occur.

**Q3 — Backfill window for `CallRecord.started_at` ↔ `CallSchedule.scheduled_for`.**

**±15 minutes.** Defense:

- `fire_scheduled_call` runs at ETA; Celery delivers within seconds in a healthy system. Queue backlog under load stretches this to minutes, not tens of minutes.
- The two known deliberate delay patterns are the 2h retry and the 5min continuation, both of which produce a CallSchedule at the new ETA — there's no legitimate reason the CallRecord would fire far from its matching schedule's `scheduled_for`.
- Tighter windows (e.g. ±2min) risk excluding legitimate matches during queue backlog.
- Wider windows (e.g. ±60min) risk matching a call to the wrong schedule when two schedules exist for the same patient within the same hour (possible under the retry path).

**Tie-breaking and edge cases:**
- Multiple `CallSchedule` rows within ±15min for the same patient: pick the closest by absolute time delta. Log the ambiguity.
- No `CallSchedule` within ±15min: leave `CallRecord.call_type` NULL. Log the unmatched row. Report aggregate unmatched count at migration end.
- `probe_call_id IS NOT NULL` or `trigger_type = 'probe'`: set `call_type = 'probe'` directly without needing a CallSchedule match. Probes bypass CallSchedule by design (fired via `fire_probe_call` from the `ProbeCall` table).

### Scope — three fixes

#### Fix 1 — Probe isolation (trajectory + focused scoring + probe_answers scaffolding)

**Exclusions (the core fix):**
- EWMA prior loader (`pipeline_tasks.py:303-316`): add `JOIN call_records cr ON cr.call_id = ClinicalExtraction.call_id WHERE cr.trigger_type != 'probe'` to the most-recent-prior query.
- Domain-score carry-forward loader (`pipeline_tasks.py:119-131`): same filter.
- FTP detector input (when Fix 2 collapses same-day): exclude probe rows before counting.

**Probe's own scoring stays live, but focused:**
- `ClinicalExtraction.scoring_scope` column added (`VARCHAR(20) NOT NULL DEFAULT 'full'`). Values: `'full'` / `'probe_focused'`.
- Pipeline sets `scoring_scope='probe_focused'` when `CallRecord.trigger_type == 'probe'`, else `'full'`.
- `compute_risk_score(smoothed, *, scoring_scope='full', ...)` signature gains the flag. Focused mode: only worst_symptom + mood participate, weights renormalised over components whose smoothed value is not None. Missing domains EXCLUDED, not treated as zero. `ftp`, `modifier`, `day_factor` skipped entirely in focused mode (they're longitudinal-context features the probe didn't ask about). Safety floors (red_flag, acute_symptom) still apply in both modes.
- Carry-forward interaction: even though the probe reads the non-probe chain's domain-score carry-forward as its prior, the focused mode only scores on domains where the probe itself produced a signal (via the scalar-column non-None proxy). This avoids a carried-forward pain from a previous routine showing up in a mood-only probe's focused score.

**New `probe_answers` table** (scaffolding only — transcript extraction is Phase 4):

```
probe_answers
  probe_answer_id       UUID PK
  probe_call_id         UUID FK -> probe_calls.probe_call_id, NOT NULL
  prompt_question       TEXT NOT NULL
  patient_answer        TEXT NULL                  (populated in Phase 4)
  confidence            VARCHAR(10) NULL           (enum: high/medium/low, Phase 4)
  asked_at              TIMESTAMPTZ NULL           (when in the transcript; Phase 4)
  extraction_status     VARCHAR(20) NOT NULL DEFAULT 'pending'
                        (enum: pending / extracted / failed)
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Plus one new JSONB column on `ProbeCall`: `questions_list: list[str]`. Populated at `POST /probe-calls` time from the clinician's input (naive newline-split for Phase 2.5; Phase 4 refines with LLM parsing).

**At call ingest (when `probe_call_id` is set):**
- Load the ProbeCall, read `questions_list`.
- Write one `probe_answers` row per question with `prompt_question=<question>`, `extraction_status='pending'`, everything else null.
- Proceed with normal ingest (creates CallRecord, queues `process_call`).

**Tests (in `tests/test_probe_isolation.py` and `tests/test_focused_risk_score.py`):**
1. Two routine calls with a probe between them: EWMA state after the second routine is identical whether the probe existed or not. Byte-for-byte identical on `smoothed_scores`.
2. Probe's own `risk_score` is computed and persisted (not null), with `scoring_scope='probe_focused'`.
3. Domain carry-forward skips probes — a routine call after a probe loads the pre-probe routine's domain scores, not the probe's.
4. `probe_answers` rows created at ingest match the count of questions in `ProbeCall.questions_list`.
5. All `probe_answers` rows at ingest time have `extraction_status='pending'` and nulls elsewhere.
6. **Focused scoring — pain only**: probe with smoothed pain=7, all others None → `final_score ≈ 80`, dominant_driver='worst_symptom', `scoring_scope='probe_focused'` persisted on the row.
7. **Focused scoring — pain + mood**: probe with smoothed pain=7 and mood=3 → final ≈ `(0.55·80 + 0.15·70) / (0.55+0.15) ≈ 78`.
8. **Focused scoring — no data**: probe with all five scalars None → `final_score=0.0`, no acute-symptom floor fires.
9. **Safety floors still apply in focused mode**: probe with `has_active_red_flag=True` → `final_score ≥ 70` even if symptom signal is low; probe with `raw_pain=9` → `final_score ≥ 65`.
10. **Full-mode regression**: identical inputs between old (implicit `full`) and new (`scoring_scope='full'`) produce identical `RiskScoreBreakdown` — the existing 18 tests in `test_risk_score.py` stay green.

#### Fix 2 — Bad-prior guard + same-day FTP collapse

**Bad-prior guard (EWMA + carry-forward):**

Both loaders in `pipeline_tasks.py` change from "most-recent other extraction, limit 1" to "most-recent other extraction with `extraction_status='extracted'`, walk back up to N=5 rows". If none found, fall through to first-call seeding (no prior).

The N=5 cap prevents pathological patients (all 50 extractions failed) from scanning the full history on every call. 5 is a defensible soft floor — it catches one or two bad priors without opening a vector for scan-all-history attacks.

Same filter applies to both the domain-score carry-forward loader and the EWMA prior loader.

**Same-day FTP collapse:**

New helper `_collapse_same_day_observations(patient_id, domain) -> list[dict]` in `clinical_intelligence/ftp_detector.py` (or wherever the Phase 4 re-port lands). For each calendar day (Europe/London) with ≥1 extraction for the patient+domain, produce a single synthetic observation with the day's MAX score. The FTP detector then counts "2+ consecutive calendar days above upper_bound" on this collapsed sequence, not on the raw extraction rows.

Existing `clinical_intelligence/ftp_detector.py` is currently dead code (zero callers — flagged in CALL_HANDLING_AUDIT.md). The Phase 4 re-port gets the collapsed-by-day logic baked in from the start. For Phase 2.5, the collapse helper is added and wired into `pipeline_tasks.py`'s FTP computation (`services/ftp_service::compute_ftp`).

**Tests (in `tests/test_ewma_bad_prior_guard.py` and `tests/test_ftp_same_day_collapse.py`):**
1. Prior row with `extraction_status='failed'` and populated smoothed_scores → skipped. Prior-2 is used.
2. All 5 most-recent priors `failed` → current call treated as first-call seeding.
3. 11 extractions in 90 minutes all with score ≥ upper_bound → FTP does NOT fire (only one calendar day).
4. Day 1 max=3 (upper=2), day 2 max=3 → FTP fires (2 consecutive calendar days).
5. Midnight-crossing: extraction at 23:50 BST and 00:05 BST counted as two separate days.
6. FTP collapse excludes probes (links Fix 1 and Fix 2).

#### Fix 3 — call_type propagation onto CallRecord

**Schema change:**

New Alembic migration: `ALTER TABLE call_records ADD COLUMN call_type VARCHAR(20) NULL`.

Nullable for legacy rows. Future rows get populated at ingest.

**Ingest logic** (`app/api/calls.py::ingest`):

```
if probe_call_id:
    call_type = 'probe'
else:
    sched = <most-recent dispatched CallSchedule for this patient>
    call_type = sched.call_type if sched else None
# CallRecord(call_type=call_type, ...)
```

Note: this reuses the existing lookup at `calls.py:90-99` that already finds the dispatched CallSchedule to mark it `completed`/`missed`. Small edit — capture the `call_type` at the same time.

**Backfill migration:**

Separate data migration (not a schema migration) — runs in the same Alembic revision as the column add. For each existing CallRecord with `call_type IS NULL`:

1. If `call_records.probe_call_id IS NOT NULL` OR `trigger_type = 'probe'` (cross-reference via a JOIN to `probe_calls`): set `call_type = 'probe'`.
2. Else: find the CallSchedule for this patient where `ABS(call_schedule.scheduled_for - call_records.started_at) <= INTERVAL '15 minutes'`, ordered by delta ascending. Set `call_type` from the closest match.
3. Else: leave NULL. Log the unmatched count in the migration output.

Emit the match/unmatched summary as migration log output so the runner can see coverage at upgrade time.

**ORM model update:** `CallRecord.call_type: Mapped[str | None] = mapped_column(String(20), nullable=True)`.

**Tests (in `tests/test_call_type_propagation.py` and updates to the parity test):**
1. Ingest with `probe_call_id` set → `call_type='probe'` on the new CallRecord.
2. Ingest matching a `CallSchedule(call_type='retry')` → `call_type='retry'`.
3. Ingest with no matching CallSchedule and no probe_call_id → `call_type=None`.
4. Backfill: synthetic CallRecord + CallSchedule at exact same time → matched.
5. Backfill: synthetic CallRecord 14 minutes off → matched; 16 minutes off → unmatched.
6. Backfill: two CallSchedules within ±15min → closest wins.
7. `test_orm_db_schema_parity.py` still passes with the new column declared on both sides.

### Deliverable order

1. **Commit 0 — docs.** This PLAN.md update. No code changes.
2. **Commit 1 — Fix 1.** Probe exclusion in `pipeline_tasks.py` + new `probe_answers` table + `questions_list` on `ProbeCall` + ingest hook + ORM models + Alembic migration + tests.
3. **Commit 2 — Fix 2.** Bad-prior guard in EWMA + carry-forward loaders + same-day FTP collapse helper + tests. No schema changes.
4. **Commit 3 — Fix 3.** `call_type` column on `CallRecord` + ingest-time population + backfill migration + tests.

Tests green between every commit. Stop after Commit 3 — user reviews diffs before merge to main.

### Estimated diff

- Fix 1: ~250 lines (new table + ORM + ingest + ProbeCall column + tests)
- Fix 2: ~150 lines (two small loader changes + FTP helper + tests)
- Fix 3: ~200 lines (migration + ingest edit + ORM + tests)
- PLAN.md addition: ~200 lines (this section)
- **Total: ~800 lines**, moderate review surface

---



### PY1 — Pydantic version
**Pydantic 2.9.2** (confirmed via `docker compose exec backend python -c 'import pydantic; print(pydantic.VERSION)'`).

Models will use v2 syntax: `model_validate`, `model_dump`, `field_validator`, `model_config = ConfigDict(...)`, `@computed_field`. Existing scoring_v2/models.py uses `confloat`/`conint` shortcuts — these still work in v2 but are deprecated. New models will use `Annotated[float, Field(ge=0, le=1)]`.

### PY2 — Strict type checking
No `mypy.ini`, `pyrightconfig.json`, `pyproject.toml`, or `setup.cfg`. The project does **not** enforce static type checking. Models will use full type hints for readability but won't rely on external checker enforcement.

### PY3 — Scoring behavioural diff (THIS IS IMPORTANT)

Your request was for a diff of `scoring.py` vs `scoring_v2/engine.py`. The real landscape is different and requires correcting first:

| Function | File | Status | Called from |
|---|---|---|---|
| `score_domain` / `ScoreResult` | `app/clinical/scoring.py` | **Dead code** | **Zero production callers** (grep confirms). Only exists as a dataclass + helper that nothing imports. |
| `score_0_10_to_0_4` | `app/clinical/scoring.py` | Live (Phase 1) | `pipeline_tasks.py`, `patients.py`, reprocess, tests |
| `score_call` (scoring_v2) | `app/scoring_v2/engine.py` | **Never shadow-run** | Only `demo.py` and `tests/test_engine.py`. The README's "shadow" framing was aspirational — this function has never run against real call data. |
| `compute_risk_score` | `app/clinical/risk_score.py` | **LIVE production scorer** | `pipeline_tasks.py:370`, `scripts/backfill_risk_scores.py`, `scripts/reprocess_stale_extractions.py`, `tests/test_risk_score.py` |

**So the behavioural diff you actually want is `scoring_v2::score_call` vs `clinical/risk_score::compute_risk_score`** — the shadow rebuild vs the live scorer. Both take similar inputs (per-domain 0-4 / 0-10 scalars, day, red flags) and produce 0-100 bands. They diverge on:

| Aspect | `scoring_v2::score_call` (shadow) | `clinical/risk_score::compute_risk_score` (live) |
|---|---|---|
| Input contract | `CallExtraction` Pydantic (per-domain 0-4 + structured adherence/social) | `SmoothedScores` dataclass (five 0-10 scalars + modifier total from smoothing) |
| State computation | `State = 25·Σ α_i·d_i` over pathway-weighted 0-4 domains | `worst_symptom = 0.55·_curve(max(pain,breath,mob,app))` + `0.15·mood + 0.15·ftp + 0.10·modifier + 0.05·day_factor` |
| Smoothing | EWMA applied inside the engine as `smoothed = λ·State + (1-λ)·prior` | EWMA applied **outside** in `smoothing.py` before the scorer is called |
| Trajectory | `max(0, smoothed - expected_curve(day))` from YAML pathway curve | No trajectory term; uses FTP status enum (`on_track`/`behind`/`significantly_behind`) from `ftp_detector.py` as a proxy |
| Red flag response | Final = 100, band = RED (absolute override) | Additive `+30` bump AND floor at `70` (preserves severity ordering between RED patients) |
| Acute symptom floor | None | Floor at `65` if raw pain or breathlessness ≥ 8 |
| Day factor | Not modelled | Linear uplift days 0–3, zero thereafter |
| Modifier cap | 25 (on a 0-100 scale) | 2.5 (on 0-10, scaled to 100 via `*40`) |
| Pathway awareness | Per-pathway weights + compound red flags from YAML | Pathway-agnostic; same formula regardless of condition |
| Config pathways defined | 2 (`post_cardiac_surgery`, `depression`) | N/A — pathway-agnostic |

**The most important consequence: the two produce materially different scores for the same input.** Worked example — smoothed pain=6, mood=7, no FTP, day=10, no red flag:

- `compute_risk_score` live: `_worst_curve(6)=65` · 0.55 + `(10-7)·10=30` · 0.15 + 0 + 0 + 0 = **40.25 / AMBER**
- `score_call` shadow: assumes 0-4 input so pain=6 is out of domain; even scaled, State depends on pathway weights — without a pathway defined, it refuses to compute. For `post_cardiac_surgery` with pain=2 (the categorical of 6): State = 25·(0.15·2) = 7.5 (on 0-100), EWMA ≈ 7.5 first call, trajectory = max(0, 7.5-15) = 0, modifiers = 0 → **4.5 / GREEN**.

These don't reconcile by tuning — they encode different clinical theories. **Decision required: which scoring theory does the consolidated `clinical_intelligence/` adopt?** My strong recommendation is **the live scorer's theory** (`compute_risk_score`) because (a) it has real calls behind it, (b) it's already producing the numbers on clinicians' dashboards, and (c) the scoring_v2 theory was never validated. The scoring_v2 Pydantic schemas are worth keeping as the **input contract** (CallExtraction, DomainObservation) even when the engine itself is discarded. See §3.2.

### PY4 — Drift-prevention mechanism recommendation

The drift bug has fired **five times** in this codebase:
1–4. Four orphan tables in `db/schema.sql` with no ORM models (`domain_scores`, `patient_pathways`, `patient_red_flags`, `pathway_soap_notes`).
5. The Phase 1 `extraction_status`/`extraction_status_reason` columns added by migration but not declared on `ClinicalExtraction` — broke the reprocess script at runtime.

**Recommendation: a single pytest integration test** (`tests/test_orm_db_schema_parity.py`) that:

1. Connects to the live dev DB.
2. For every class inheriting `Base`, reflects the actual table via `information_schema.columns`.
3. Diffs the ORM-declared column set against the DB column set.
4. Fails with a list of missing/extra columns per table.

This is the cheapest mechanism that catches all five bugs:

- Every CI run exercises it (no new infra).
- Every test invocation exercises it locally.
- No way to add a migration without the test noticing.
- Covers both directions: missing-on-model (the Phase 1 bug) and missing-on-migration (hypothetical).

**Alternatives considered and rejected:**
- **Alembic hook:** requires developer discipline to run, trivially bypassed.
- **FastAPI startup assertion:** catches it in staging/prod but not in PR review — too late.
- **Runtime assertion in every query path:** high noise, performance cost.

**Belt-and-braces option:** add the startup assertion too, guarded by `DEBUG=True` so it only fires in dev/staging. This catches the test-skipped case (DB unavailable during test run). Flagging as optional; the pytest test alone gets us 95% of the way.

---

## Phase 2 scope

**Goal:** consolidate `app/clinical/` + `app/scoring_v2/` into `app/clinical_intelligence/`. Define the Pydantic model vocabulary the rest of the refactor (Phases 3-5) will build on. Add the `score_patient_domain` + `compute_overall_call_status` scoring functions. Add `validation.py` with non-blocking plausibility checks. Fix the ORM drift class of bug.

**Non-goals (explicitly out of Phase 2):**
- The seven missing pathway trajectories (Phase 3).
- Required Questions Manifest + coverage enforcement (Phase 3).
- Patient-facing red-flag probes (Phase 4).
- Restricted Mode prompt builder (Phase 4).
- Asymmetric smoother rewrite (Phase 5).
- Critical-medication adherence weighting (Phase 5 — see §6 D3).
- Fixing the three stranded pre-cutover patients' pathway links (deferred product decision — see §6 D1).

---

## 1. Consolidation map — every file, every disposition

### 1.1 Scoring_v2 → clinical_intelligence/

| `app/scoring_v2/…` | Destination | Disposition | Why |
|---|---|---|---|
| `__init__.py` | — | **Delete** | Re-exports move to `clinical_intelligence/__init__.py`. |
| `README.md` | — | **Delete** | Scoring-theory framing is superseded (§PY3). Relevant content re-homed in `clinical_intelligence/__init__.py` docstring or a short `docs/clinical_intelligence.md`. |
| `models.py::RedFlagType` enum | `clinical_intelligence/models.py` | **Keep, rename** to `RedFlagCategory` | Salvageable. The live code uses string flag_type (e.g. `"red"` severity) — this enum gives typed values worth preserving. |
| `models.py::DomainObservation` | `clinical_intelligence/models.py::DomainScore` | **Keep, refactor** | Repurposed as the Phase 2 `DomainScore` Pydantic model (per your B list). Drops `instrument_value`/`instrument_name` fields that aren't populated today. |
| `models.py::RedFlag` | `clinical_intelligence/models.py::RedFlagProbe` (scaffolding only) | **Keep, extend in Phase 4** | The structure is right; Phase 4 extends with `patient_facing_question: str`. |
| `models.py::AdherenceStatus` | `clinical_intelligence/models.py` | **Keep as-is** | Already structured. |
| `models.py::SocialFactors` | `clinical_intelligence/models.py` | **Keep as-is** | Same. |
| `models.py::CallExtraction` | `clinical_intelligence/models.py` | **Keep, refactor** | The LLM/engine input contract. Drops `extraction_schema_version` string in favour of a class constant. |
| `models.py::ScoringBreakdown`, `RiskScore`, `PatientHistory` | — | **Delete** | Tied to the abandoned scoring theory. Replaced by `CallRiskAssessment` + `SmoothedScore` (see §2). |
| `models.py::RiskBand` | `clinical_intelligence/models.py` | **Keep** | Used in `CallRiskAssessment`. |
| `engine.py::score_call` and all helpers | — | **Delete** | Abandoned scoring theory (§PY3). Never wired to production. |
| `config.py::DomainWeight`, `ExpectedCurvePoint`, `PathwayConfig`, `ScoringConfig` | — | **Delete** | Pathway config stays with `pathway_map.py` (the OPCS-keyed live source); the YAML only defines 2 of 20+ pathways. |
| `config.py::load_config`, `config_hash`, `expected_score_at_day` | — | **Delete** | No callers outside scoring_v2. |
| `config/pathways.yaml` | — | **Delete** | Superseded by the Python pathway modules introduced in Phase 3. |

### 1.2 Clinical → clinical_intelligence/

| `app/clinical/…` | Destination | Disposition | Why |
|---|---|---|---|
| `__init__.py` (empty) | — | **Delete** | Replaced by `clinical_intelligence/__init__.py` with the public API. |
| `benchmarks.py` (1696 lines) | `clinical_intelligence/benchmarks.py` | **Move, content unchanged** | NICE trajectory tables. Phase 3 extends with the 7 missing pathways. |
| `pathway_map.py` (641 lines) | `clinical_intelligence/pathway_map.py` | **Move, content unchanged** | Live OPCS→NICE source. 20+ pathways. Phase 3 refines. |
| `playbook.py` (267 lines) | `clinical_intelligence/playbook.py` | **Move, content unchanged** | LLM-assisted generator. Phase 4 refactors the prompt builder out into `prompts.py`. |
| `red_flags.py` (68 lines) | `clinical_intelligence/red_flags.py` | **Move, content unchanged** | `evaluate_flags` is live. Phase 4 extends with patient-facing probes. |
| `ftp_detector.py` (32 lines) | `clinical_intelligence/ftp_detector.py` | **Move, content unchanged** | Tiny, works, used by `compute_risk_score`. |
| `risk_score.py` (258 lines) | `clinical_intelligence/risk_score.py` | **Move, content unchanged** | **The live scorer.** Keeps its worst/mood/ftp/modifier/day decomposition. Phase 5 may recalibrate weights against clinician-labelled data. |
| `smoothing.py` (157 lines) | `clinical_intelligence/smoothing.py` | **Move, content unchanged in Phase 2** | Phase 5 rewrites with asymmetric smoothing + hard pass-throughs. |
| `scoring.py::score_0_10_to_0_4` | `clinical_intelligence/scoring.py` | **Move** | Phase 1 categorical mapping. Live. |
| `scoring.py::score_domain` + `ScoreResult` | — | **Delete** | **Dead code, zero callers.** Confirmed via grep. Replaced by the Phase 2 `score_patient_domain` (your list §C) which is a full rewrite keyed to the new `DomainScore` model. |

### 1.3 Net-new files in Phase 2

| New file | Purpose |
|---|---|
| `clinical_intelligence/__init__.py` | Public API re-exports: scoring functions, models, coverage (stubs for Phase 3). |
| `clinical_intelligence/models.py` | All Pydantic models — see §2. |
| `clinical_intelligence/scoring.py` (rewritten) | `score_0_10_to_0_4` (moved), `score_patient_domain` (net-new), `compute_overall_call_status` (net-new, Double-Amber + Red Flag override). |
| `clinical_intelligence/validation.py` | `validate_extraction_plausibility` — flags first-call-all-4s and all-domains-dropped-to-empty. Non-blocking warnings. |
| `clinical_intelligence/coverage.py` (**STUB**) | Empty module with a TODO docstring pointing to Phase 3. Created so the `__init__.py` structure matches the brief's target. |
| `clinical_intelligence/prompts.py` (**STUB**) | Same — Phase 4. |
| `clinical_intelligence/pathways/__init__.py` (**STUB**) | Phase 3 will populate. |
| `tests/test_orm_db_schema_parity.py` | Drift-prevention test (§PY4). |
| `tests/test_models.py` | Pydantic schema tests — validation_status defaults, required fields, serialisation round-trip. |
| `tests/test_call_status.py` | `compute_overall_call_status` tests covering Double-Amber + Red Flag override. |
| `tests/test_validation.py` | `validate_extraction_plausibility` unit tests. |

### 1.4 Call-site rewrites (Phase 2 PR)

All of these are mechanical imports changes. Tracking explicitly so the PR review can spot-check:

- `app/tasks/pipeline_tasks.py` — `from ..clinical.pathway_map import` → `from ..clinical_intelligence.pathway_map import` (5 sites); same for `risk_score`, `smoothing`, `scoring`.
- `app/api/patients.py` — same pattern (categorical helper + pathway map).
- `app/api/internal.py` — pathway_map only.
- `app/tasks/probe_tasks.py` — pathway_map only.
- `scripts/backfill_risk_scores.py` — `smoothing`, `risk_score`.
- `scripts/reprocess_stale_extractions.py` — `smoothing`, `risk_score`, `scoring` (4 imports).
- All existing tests — `tests/test_engine.py` is **deleted** (scoring_v2 gone); `tests/test_smoothing.py` and `tests/test_risk_score.py` have imports rewritten.
- `backend/demo.py` — **deleted** (only exists to demo scoring_v2).

### 1.5 Files not touched in Phase 2

- `backfill_risk_scores.py` — remains uncommitted / dormant. Phase 5 will re-run it under the new smoother.
- The migration `b1c3d5e7f91a` and all Phase 1 artefacts.
- The orphan tables — decision in §6 D2, execution deferred where "drop" isn't a Phase 2 action.

---

## 2. Pydantic model definitions (§B of your spec)

All models live in `app/clinical_intelligence/models.py`. Pydantic v2 syntax. `validation_status` is a **`Literal` field** with three values and a default of `draft`:

```python
ValidationStatus = Literal[
    "draft_awaiting_clinical_review",
    "clinician_reviewed",
    "production_signed_off",
]
```

**Models that carry `validation_status` (clinician-authored content):**

| Model | Represents | New or salvaged | Key fields |
|---|---|---|---|
| `DomainTrajectoryEntry` | One NICE trajectory row: per-pathway, per-domain, per-day-range expected/upper-bound score | New | `opcs_code`, `domain`, `day_range_start`, `day_range_end`, `expected_score`, `upper_bound_score`, `nice_source`, `nice_quote`, `validation_status` |
| `PathwayPlaybook` | Per-pathway prompt script structure | New | `opcs_code`, `nice_ids`, `monitoring_window_days`, `call_days: list[int]`, `domains: list[str]`, `red_flags: list[str]`, `validation_status` |
| `RequiredQuestion` (**stub — populated Phase 3**) | One entry in the Required Questions Manifest | New | `opcs_code`, `domain`, `question_text`, `required: bool`, `day_ranges`, `validation_status` |
| `RedFlagProbe` (**stub — populated Phase 4**) | Patient-facing probe for a red flag | New | `flag_code`, `nice_basis`, `patient_facing_question`, `follow_up_escalation`, `validation_status` |

**Models that do NOT carry `validation_status` (computed/derived):**

| Model | Represents | New or salvaged | Key fields |
|---|---|---|---|
| `DomainScore` | One domain's extracted 0-4 score for one call | Salvaged (was `DomainObservation`) | `domain`, `raw_score: 0-4`, `scale_input: 0-10` (optional), `evidence_quote`, `confidence: 0-1`, `extracted_at` |
| `SmoothedScore` | EWMA output per domain | Salvaged (was `SmoothedScores` dataclass) | `pain`, `breathlessness`, `mobility`, `appetite`, `mood`, `max_smoothed`, `modifier_total`, `modifier_detail`, `lam` |
| `CallRiskAssessment` | Output of the live `compute_risk_score` | Replaces `RiskScoreBreakdown` dataclass | All fields from the existing dataclass, unified under Pydantic. `band: RiskBand`, `final_score: 0-100`, full breakdown. |
| `CoverageReport` (**stub — populated Phase 3**) | Result of checking a transcript against the Required Questions Manifest | New | `opcs_code`, `call_id`, `asked: list[str]`, `missed: list[str]`, `asked_but_unanswered: list[str]`, `coverage_pct: 0-100` |
| `PromptContext` (**stub — fleshed out Phase 4**) | The bundle fetched before each call to build the system prompt | New | `patient_id`, `nhs_number`, `playbook: PathwayPlaybook`, `recent_calls: list[CallSummary]`, `smoothed_state: SmoothedScore`, `active_red_flags: list[str]`, `meds: list[str]`, `restricted_mode: bool` |

**Shared enums / aliases:**

```python
class RiskBand(str, Enum): GREEN, AMBER, RED
class RedFlagCategory(str, Enum): CHEST_PAIN, ACUTE_SOB, SUICIDAL_IDEATION, SEPSIS_SIGNS,
                                   HAEMORRHAGE, NEW_FOCAL_NEURO, ANAPHYLAXIS, PATHWAY_SPECIFIC
```

**Field conventions (Pydantic v2):**

- `raw_score: Annotated[int, Field(ge=0, le=4)]` — not `conint(ge=0, le=4)`.
- `confidence: Annotated[float, Field(ge=0, le=1)]`.
- `model_config = ConfigDict(frozen=True, extra="forbid")` on input-contract models (CallExtraction, DomainScore).
- JSON serialisation uses `model_dump(mode="json")` for DB JSONB writes.

**Tests (in `tests/test_models.py`):**

1. Default `validation_status` on clinical-content models is `"draft_awaiting_clinical_review"`.
2. Each model rejects unknown fields (where `extra="forbid"`).
3. `model_dump_json()` → `model_validate_json()` round-trip for each model.
4. Numeric bounds enforced (raw_score outside 0-4 raises).
5. `validation_status` enum refuses invalid values.

---

## 3. Scoring refactor (§C of your spec)

### 3.1 `score_0_10_to_0_4` — already done in Phase 1

Moves into `clinical_intelligence/scoring.py` unchanged. Confirmed no other `* 0.4` clinical-scoring sites exist (grep: only `report_service.py` PDF column widths remain, unrelated).

### 3.2 `score_patient_domain` — net-new, replaces dead `score_domain`

Takes a `DomainScore` + prior-call history + pathway trajectory entry, returns a classification bundle. The old `score_domain`'s logic (trajectory / FTP / escalation tier) is re-implemented against the new Pydantic types rather than a bare dataclass, and hooked into `CallRiskAssessment`.

```python
def score_patient_domain(
    current: DomainScore,
    prior_scores: list[DomainScore],  # chronological
    trajectory: DomainTrajectoryEntry,  # for the patient's pathway+day
) -> DomainClassification:
    ...
```

`DomainClassification` is a new Pydantic model (add to §2): `{domain, score, expected, upper_bound, above_upper_bound, trajectory: improving|stable|deteriorating|insufficient_data, ftp_flag, escalation_flag, escalation_tier, nice_basis}`.

### 3.3 `compute_overall_call_status` — net-new

**This is the function that decides whether a whole call is GREEN / AMBER / RED.** Two rules, in order of precedence:

1. **Red Flag override**: if *any* `DomainClassification.escalation_flag` is true OR any item in `CallExtraction.red_flags` is populated, return `RED`. No downstream logic.
2. **Double-Amber rule**: if two or more domains each have `trajectory == "deteriorating"` AND `above_upper_bound == True`, return `AMBER` with reason `"double_amber"`.
3. **Default**: return the band from `CallRiskAssessment.band` (the live `compute_risk_score` output).

The Double-Amber rule is deliberately stricter than the live scorer — it will sometimes promote to AMBER where `compute_risk_score` would return GREEN. This is a conservative addition that reflects "two domains trending wrong in the same call" being a clinical concern worth a closer look, even when no single symptom is severe.

Return type: `OverallCallStatus { band: RiskBand, primary_reason: str, contributing: list[str] }`.

**Tests (in `tests/test_call_status.py`):**

1. Any single escalation_flag → RED regardless of everything else.
2. Two domains deteriorating + above_upper → AMBER with reason "double_amber".
3. One domain deteriorating + above_upper → falls through to `CallRiskAssessment.band`.
4. Two domains deteriorating but none above_upper → falls through.
5. Red flag override beats Double-Amber (order matters).
6. Empty prior history → trajectory is `insufficient_data`, no Double-Amber possible.

### 3.4 Integration with the live scorer

`compute_risk_score` keeps its current interface. `compute_overall_call_status` wraps it:

```
CallExtraction ──► per-domain score_patient_domain ──► list[DomainClassification]
                                   ▼
SmoothedScore + FTP + day ──► compute_risk_score ──► CallRiskAssessment
                                   ▼
       [all of the above]  ──► compute_overall_call_status ──► OverallCallStatus
```

Only `compute_overall_call_status` is new logic; everything downstream of it is existing.

---

## 4. Validation module (§D of your spec)

`app/clinical_intelligence/validation.py::validate_extraction_plausibility` — pure function, non-blocking. Returns `list[ValidationWarning]`; caller chooses what to do.

```python
class ValidationWarning(BaseModel):
    code: Literal["first_call_all_fours", "all_domains_dropped_to_empty", ...]
    severity: Literal["info", "warn"]
    detail: str
    affected_domains: list[str]

def validate_extraction_plausibility(
    current: CallExtraction,
    prior_extractions: list[CallExtraction],  # chronological, most recent last
) -> list[ValidationWarning]: ...
```

**Rules implemented in Phase 2:**

1. **`first_call_all_fours`** — if `prior_extractions` is empty AND ≥3 domains have `raw_score == 4`. Suggests LLM hallucination or transcript misread; clinicians should review before escalation.
2. **`all_domains_dropped_to_empty`** — if previous call had ≥2 domains with `raw_score > 0` AND current call has every domain as `None` or missing. Suggests extraction failure masquerading as silence.

Both return `severity="warn"`. Caller (pipeline_tasks) logs and stores in `condition_specific_flags.validation_warnings` but does **not** halt processing. Clinicians see warnings in the dashboard.

Rules *out of scope* for Phase 2 (noted for future): implausible jumps (pain 0→10 in one call), NICE-inconsistent combinations (e.g. afebrile + sepsis_signs red flag), pathway-specific impossibilities.

**Tests (in `tests/test_validation.py`):**

1. First call with 3 fours → warning fires.
2. First call with 2 fours → no warning.
3. Mid-history call with 3 fours → no warning (not first call).
4. Drop-to-empty after populated history → warning.
5. Drop-to-empty after already-empty history → no warning.
6. Mixed: drop + first-call don't overlap (first call has no history to drop from).

---

## 5. Drift-prevention (§F of your spec)

### 5.1 The test

`tests/test_orm_db_schema_parity.py` — runs under normal pytest. Skips cleanly if dev DB unreachable (same pattern as `test_extraction_status_model.py`).

Pseudocode:
```python
def test_every_orm_table_matches_db():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        actual_tables = await conn.run_sync(_reflect_all_tables)

    declared = {cls.__tablename__: cls.__table__ for cls in Base.__subclasses__()}

    mismatches = []
    for tablename, declared_table in declared.items():
        actual = actual_tables.get(tablename)
        if actual is None:
            mismatches.append(f"Table {tablename} declared in ORM but missing in DB")
            continue
        declared_cols = {c.name for c in declared_table.columns}
        actual_cols = {c["column_name"] for c in actual}
        missing_on_model = actual_cols - declared_cols
        missing_on_db    = declared_cols - actual_cols
        if missing_on_model:
            mismatches.append(f"{tablename}: columns in DB not declared on model: {sorted(missing_on_model)}")
        if missing_on_db:
            mismatches.append(f"{tablename}: columns on model not in DB: {sorted(missing_on_db)}")

    assert not mismatches, "\n".join(mismatches)
```

Run in CI as part of the normal suite. Also exercisable locally.

### 5.2 What it catches by design

- The Phase 1 bug (migration adds column, model not updated) — YES, `missing_on_model` fires.
- Reverse drift (model adds column, no migration) — YES, `missing_on_db` fires.
- **Does NOT catch** orphan tables (DB tables with no ORM model at all) — that's an intentional product decision (see §6 D2) rather than drift.

### 5.3 Complementary: per-class reflection test

The pattern established in `test_extraction_status_model.py::test_extraction_status_attribute_is_declared` (static attribute assertion) is kept and generalised — one such test per clinical-content table, asserting the presence of each column by name. These are the "what did we expect to exist" guards; §5.1 is the "does the DB agree" guard. Together they pincer the drift.

### 5.4 Out of scope for Phase 2, flagged for later

- FastAPI startup assertion (runs same check at app boot, fails fast in prod/staging). Low-cost addition, valuable for catching emergency-hotfix drift that bypassed CI. Propose adding in Phase 5 when the smoother work will be heavily exercised.

---

## 6. D1 / D2 / D3 decisions (§E of your spec)

### D1 — Stranded pre-cutover patients (James, Doris, Robert)

**Your preliminary read accepted:** leave as-is in `stale_pre_calibration`; surface them in the clinician dashboard as a "review queue". Not a Phase 2 code task.

PLAN.md carries this forward as an **open product decision** for the dashboard team. The reprocess script's `skipped_no_pathway` warning already flags the count in its summary; no further runtime work needed in Phase 2.

Flagging only: whenever the Phase 5 smoother ships, re-running the reprocess script will still surface these three patients unchanged. If "review queue" is not live by Phase 5, they remain invisible to the risk engine. Phase 5 must verify status before running.

### D2 — Orphan tables: per-table recommendation

| Table | Recommendation | Reasoning |
|---|---|---|
| `domain_scores` | **DROP** (remove from `db/schema.sql`, add migration to drop from DB) | Never written by any code. Duplicates `condition_specific_flags.domain_scores` JSONB. Promotion would require refactoring 30+ JSON-key access sites. No clinical requirement is gated on tabular access vs. JSON access. |
| `pathway_soap_notes` | **KEEP (defer to Phase 4) — revised from "DROP"** | **Revision note:** originally recommended DROP here. The Phase 2 addendum on SOCRATES probes (§6A.6) changes the analysis: the addendum commits to per-domain structured clinical findings, which is exactly what `pathway_soap_notes` was designed for. For Phase 2 we take **Path A** (JSONB `socrates_findings` on `soap_notes`) as the cheap interim, but we KEEP `pathway_soap_notes` in the schema and revisit in Phase 4 alongside `patient_red_flags` (both are per-domain-per-call tables that move together). |
| `patient_red_flags` | **KEEP (defer promotion to Phase 4)** | Different shape from `urgency_flags`: per-domain + explicit resolution tracking (`resolved`, `resolved_call_id`, `resolved_at`). Phase 4's patient-facing probing needs resolution state that `urgency_flags` doesn't cleanly express. Phase 2 leaves the table in `schema.sql`, creates no ORM model. Phase 4 writes the model + wires it. |

**Phase 2 execution for D2 (revised post §6A):**
- `domain_scores`: add Alembic migration that `DROP TABLE IF EXISTS domain_scores`. Remove from `db/schema.sql` in the same PR.
- `pathway_soap_notes`: untouched in Phase 2 (revised from "drop"). Comment added in `schema.sql` marking "deferred promotion, Phase 4 — candidate relational home for per-domain SOCRATES findings if the JSONB approach in soap_notes.socrates_findings proves insufficient".
- `patient_red_flags`: untouched in Phase 2. Comment added in `schema.sql` marking "deferred promotion, Phase 4 — moves together with pathway_soap_notes".
- **New in the same Phase 2 migration:** `ALTER TABLE soap_notes ADD COLUMN socrates_findings JSONB NOT NULL DEFAULT '{}'::jsonb`. See §6A.6 Path A.

### D3 — Critical-medication adherence weighting

**Confirmed: out of Phase 2 scope.** This is a **Phase 5 concern**.

Reasoning: the hardcoded `critical_medication=False` in `backfill_risk_scores.py:83` and `reprocess_stale_extractions.py` causes anticoagulants/insulin/immunosuppressants to get the non-critical bump. The fix is wiring `critical_medication` from the patient's medication profile, which Phase 5 does as part of calibrating the asymmetric smoother against clinician-labelled data. Touching it in Phase 2 would calibrate against uncalibrated weights.

**Action in Phase 2:** add a `# TODO(phase-5): wire critical_medication from PatientMedicalProfile` comment at both sites. Nothing else.

---

## 6A. SOCRATES probes (added per Phase 2 addendum)

### 6A.1 Factual corrections to the addendum text

The addendum stated that `_socrates_probes(domain)` lives in `checkin_agent.py`. It does not. It lives in `healthcare-voice-agent/agent/system_prompt.py:4` — the **voice-agent runtime**, which is out of scope per Phase 0 (§8 of original plan flagged the whole `healthcare-voice-agent/` tree as dead code from the *platform's* perspective; but `system_prompt.py` is clearly used by the live voice agent via `checkin_agent.py::build_system_prompt`). Porting SOCRATES probes to the platform is therefore a **cross-repo move**, not a local refactor. Flagging this explicitly so it's understood as a net migration of clinical content from the voice-agent repo into the platform.

The addendum also hinted the existing content might be "thin or generic". It is **neither**. It covers 10 domain families with 3–6 well-formed NHS-plain probes each, plus a generic fallback. The *structural* problems are real, but the content quality is fine to port.

### 6A.2 Architectural observation — SOCRATES is not the right frame for every domain

SOCRATES (Site / Onset / Character / Radiation / Associations / Time-course / Exacerbating-Relieving / Severity) is a **symptom-assessment framework for pain-like complaints**. Forcing its shape onto every domain is clinically incorrect:

| Domain family | SOCRATES applicability |
|---|---|
| Pain / ache / discomfort | **Full** — the canonical use case |
| Breathlessness / chest | **Partial** — Onset, Character, Time, Associations, Severity apply. Site/Radiation often don't. |
| Wound / incision | **Partial** — Site, Character, Associations, Time apply. Onset/Radiation/Exacerbating-Relieving rarely apply. |
| Swelling / oedema | **Partial** — Site, Time, Character, Associations apply. |
| Appetite / eating | **Minimal** — Time, Associations. Not really SOCRATES. |
| Mobility / mobility_progress | **Minimal** — essentially a functional-status inventory, not symptom assessment. |
| Bowel / bladder / urinary | **Minimal** — mostly Associations. |
| Mood / mental health | **Not applicable** — you don't site-and-character a mood. |
| Fatigue / energy | **Minimal** — Time, Severity (as functional impact). |
| Medication adherence | **Not applicable** — this is a behaviour inventory, not symptom assessment. |

**Consequence for the data model:** a single `SocratesProbe` Pydantic model with S/O/C/R/A/T/E/S fields would be right for pain (and partially right for breathlessness, wound, swelling) but actively misleading for mood, mobility, adherence, bowels. The addendum's framing — "not every dimension applies to every domain; the model must allow dimensions to be omitted" — catches half the problem but not this half: for some domains NO SOCRATES dimensions apply, and using an omission-tolerant `SocratesProbe` on them would imply the framework is relevant when it isn't.

**Proposed model shape (two models, not one):**

```python
class SocratesDimension(str, Enum):
    SITE = "site"
    ONSET = "onset"
    CHARACTER = "character"
    RADIATION = "radiation"
    ASSOCIATIONS = "associations"
    TIME_COURSE = "time_course"
    EXACERBATING_RELIEVING = "exacerbating_relieving"
    SEVERITY = "severity"


class SocratesProbeTemplate(BaseModel):
    """For symptom-assessment domains where SOCRATES genuinely applies:
    pain, breath/chest, wound, swelling. One template per (pathway, domain).
    Dimensions list only the ones that apply — no empty-string placeholders."""
    pathway_opcs: str
    domain: str
    dimensions: dict[SocratesDimension, list[str]]  # dimension → probe wordings
    nice_source: str
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")


class DomainProbeSet(BaseModel):
    """For domains where SOCRATES doesn't apply — mood, mobility, appetite,
    bowels, fatigue, adherence. A flat list of open-ended probes with no
    SOCRATES structure. Clinician notes explain why this shape, not SOCRATES."""
    pathway_opcs: str
    domain: str
    probes: list[str]
    rationale: str  # short note on why SOCRATES doesn't fit this domain
    nice_source: str
    validation_status: ValidationStatus = "draft_awaiting_clinical_review"
    model_config = ConfigDict(extra="forbid")
```

Every domain that needs probes has **exactly one** of the two; never both, never neither. The code chooses which to instantiate based on the domain type.

### 6A.3 Port disposition per domain family

Faithful port of `system_prompt.py::_socrates_probes` into the new shape:

| Existing family (keyword) | Destination model | Action | CLINICAL_REVIEW_NEEDED? |
|---|---|---|---|
| pain / ache / discomfort / sore | `SocratesProbeTemplate` | Port 6 probes into S/C/T/R/E/Severity dimensions | **Yes** — review which probe maps to which dimension. Also: Onset is missing from the existing content; confirm with clinicians. |
| breath / chest / respir / lung / cough | `SocratesProbeTemplate` (chest+breath split?) | Port 5 probes; flag chest-vs-breath separation | **Yes** — chest symptoms and breathlessness are often distinct domains clinically; current helper bundles them. |
| wound / incis / site / heal / infect / dressing | `SocratesProbeTemplate` | Port 5 probes across Site/Character/Associations/Time | **Yes** — wound assessment is inspection-style; confirm SOCRATES framing is preferred or whether a `WoundInspectionProbe` variant is needed. |
| mobil / walk / move / gait / balance / fall / physio | `DomainProbeSet` | Port 5 probes as flat list; rationale = "functional status, not SOCRATES" | **Yes** — Phase 3 will need to confirm fall-risk framing stays as a probe, not promoted to a red flag. |
| swell / oedema / fluid / bloat / ankl / leg | `SocratesProbeTemplate` | Port 5 probes | **Yes** — confirm dimension mapping. |
| appetit / eat / food / nausea / vomit / weight / nutrition | `DomainProbeSet` | Port 5 probes as flat list | **Yes** — nausea + vomiting are arguably symptom-assessment SOCRATES candidates; confirm whether to split from nutrition. |
| bowel / stool / urine / bladder / catheter / toilet / constip / diarr | `DomainProbeSet` | Port 5 probes | **Yes** — catheter-specific probes probably need their own domain; confirm. |
| mood / mental / anxiet / depress / sleep / emotion / worry / stress / psycho | `DomainProbeSet` | Port 5 probes | **Critical — links to Z03_MH policy.** Z03_MH pathway is scaffold-only. Mood probes used for non-Z03 pathways (e.g. post-op mood screening) are fine to port *as a Phase 2 draft*, but escalation paths from those probes must not duplicate the Z03_MH content Phase 2 is deliberately not building. |
| fatig / tired / energy / exhaust / weak | `DomainProbeSet` | Port 4 probes | Low-risk port. Clinical review nice-to-have, not blocking. |
| medic / tablet / drug / prescription / adherence / dose | `DomainProbeSet` | Port 3 probes | Low-risk port. |
| Generic fallback (no match) | `DomainProbeSet` | Port 5 probes, pathway_opcs="*" | **Yes** — the existence of a generic fallback hides pathway-domain pairs that should have dedicated content. Phase 3 should surface which pathway+domain pairs are currently falling through to generic and triage. |

### 6A.4 Trigger rule — WHEN SOCRATES fires (documentation only, not code)

Phase 2 encodes the rule in the data model and in `__init__.py` docstring. No enforcement logic. Phase 4/6 consumes it.

A `SocratesProbeTemplate` or `DomainProbeSet` fires for a (patient, call, domain) combination if **any** of:

1. **Domain is above expected trajectory** for pathway+day (`domain_score > DomainTrajectoryEntry.expected_score` for that pathway and day range). "Above upper_bound" is not required — being above expected is sufficient trigger; being above upper_bound is a stronger trigger that also fires coverage-enforcement and escalation tier logic.
2. **Domain is deteriorating per the smoother** (`DomainClassification.trajectory == "deteriorating"`). Deteriorating domain always gets probed, even if still within expected band.
3. **Patient volunteers a symptom in the domain.** This is handled in the prompt builder (Phase 6) via "if patient raises X, probe with the domain's template" rather than by upfront domain inclusion. Phase 2 documents the intent; Phase 6 implements.
4. **A red flag is positive in this domain.** Any active `patient_red_flags` row (once that table is promoted in Phase 4) in the domain fires the probe.

Explicitly: probes do **NOT** fire when the domain is on-track and stable. This is the key behavioural rule — SOCRATES probing is conditional clinical follow-up, not a call-completion checklist. (The call-completion checklist is the Required Questions Manifest in Phase 3, which is a separate concept.)

**Data-structure encoding:** each `PathwayPlaybook` has a `socrates_trigger_policy` field referencing the rule. Phase 4/6 reads this field and applies the trigger logic; Phase 2 fixes the policy name to `"conditional_on_deterioration"` as a string literal.

### 6A.5 Cross-reference to §1 (consolidation map)

Phase 2 file additions expand:

- `clinical_intelligence/models.py` — add `SocratesDimension`, `SocratesProbeTemplate`, `DomainProbeSet`, `ProbeSet = SocratesProbeTemplate | DomainProbeSet` union alias.
- `clinical_intelligence/pathways/_probes.py` — new module, holds the ported content keyed by (opcs_code, domain). Per-pathway files in `pathways/` reference it.
- `tests/test_socrates_probes.py` — new test file: every ported family round-trips (model validate → model dump → model validate), every domain listed in a `PathwayPlaybook` has an associated probe set, union aliasing works under Pydantic v2 discriminated unions.

Estimated Phase 2 diff grows by ~250 lines (model + content port + tests).

### 6A.6 Answer to Q7 — SOCRATES output on the SOAP note

**Your recommendation: structured per-dimension, not prose. My answer: structured *for SOCRATES-applicable domains only*, with prose retained for the rest.** This is the only honest answer given §6A.2.

**Concrete proposal:**

1. Existing `soap_notes` table (modelled as `SOAPNote` in `app/models/call.py`) gains a new JSONB column `socrates_findings` via a Phase 2 migration. Shape:
   ```json
   {
     "pain": {
       "site": "left lower abdomen, localised",
       "onset": "yesterday evening, gradual",
       "character": "sharp",
       "time_course": "constant since onset",
       "severity": "6/10, interfering with sleep"
     },
     "wound": { "site": "c-section incision", "associations": "slight redness noted" }
   }
   ```
   Only populated dimensions are present. Empty dict when no SOCRATES-applicable findings captured.
2. The existing `subjective` Text column continues to carry prose for:
   - SOCRATES dimensions that are free-form enough to resist structure (clinician's own synthesis).
   - Non-SOCRATES-domain findings (mood, mobility, appetite, adherence, bowels, fatigue).
3. Both are populated by the post-call pipeline. Dashboard reads `socrates_findings` for the at-a-glance view; `subjective` for the full narrative.

**Downstream implications — THIS IS IMPORTANT:**

- **Direct impact on D2 (§6 orphan tables).** My Phase 2 recommendation was to DROP `pathway_soap_notes`. **I now want to revise that.** `pathway_soap_notes` is a per-domain SOAP table — the *exact* shape `socrates_findings` expresses. If we're committing to per-domain structured clinical findings, `pathway_soap_notes` is the natural relational home for them (one row per call+domain with S/O/A/P fields) and the JSONB approach is a cheaper interim.

  Two defensible paths:
  - **Path A (cheap, Phase 2)**: add `socrates_findings JSONB` to `soap_notes`. Keep `pathway_soap_notes` deferred. Easy to migrate away if we later want relational per-domain.
  - **Path B (structural, Phase 2)**: promote `pathway_soap_notes` now — model it in `app/models/clinical.py`, wire it up, write SOCRATES findings as one row per (call, domain) instead of a JSONB blob. More work; stronger foundation for Phase 4's per-domain red-flag tracking (which `patient_red_flags` also wants).

  **My rec: Path A for Phase 2, revisit promotion of `pathway_soap_notes` in Phase 4** alongside `patient_red_flags` (they move together — both are per-domain per-call tables). This matches the "keep deferred" recommendation for `patient_red_flags` in D2 and keeps Phase 2 scope tight.

- **Migration in Phase 2:** single Alembic revision that (a) drops `domain_scores` table, (b) adds `soap_notes.socrates_findings JSONB NOT NULL DEFAULT '{}'::jsonb`. Does **NOT** drop `pathway_soap_notes` anymore (revised from §6 D2). `pathway_soap_notes` stays in place, unused, with a `-- Deferred promotion — Phase 4 candidate; structural decision depends on socrates_findings JSONB approach proving insufficient` comment.

- **Dashboard work:** the "at-a-glance SOCRATES view" the addendum describes is a frontend task (new component reading `soap_notes.socrates_findings`). Out of Phase 2 scope but flagged for the dashboard team — their schema assumptions need updating.

- **Clinician review workflow:** the addendum's structured view only shines if SOCRATES findings are populated per dimension. The LLM extraction prompt in `post_call_pipeline.py` currently produces prose-only SOAP. Phase 2 does **not** change that prompt; a follow-up ticket adds a structured-SOCRATES extraction step. Flagging — if the prompt isn't updated, `socrates_findings` stays empty and the dashboard component has nothing to render.

---

## 7. Testing strategy

Following Phase 1's pattern — pure-function unit tests by default, DB-touching tests skipped when the dev DB is unavailable.

| New test file | Coverage | DB required? |
|---|---|---|
| `tests/test_models.py` | Pydantic defaults, bounds, serialisation | No |
| `tests/test_call_status.py` | Red Flag override, Double-Amber, fallthrough | No |
| `tests/test_validation.py` | `validate_extraction_plausibility` rules | No |
| `tests/test_orm_db_schema_parity.py` | Every ORM table matches DB | Yes |
| `tests/test_scoring_domain.py` | `score_patient_domain` behaviour | No |
| `tests/test_socrates_probes.py` | Port round-trip + model validation + union discriminator | No |

Existing tests rewritten for import paths:
- `tests/test_smoothing.py` — imports change; content unchanged.
- `tests/test_risk_score.py` — imports change; content unchanged.
- `tests/test_categorical_mapping.py` — imports change.
- `tests/test_reprocess.py` — imports change.
- `tests/test_extraction_status_model.py` — unchanged.

Deleted:
- `tests/test_engine.py` — scoring_v2 engine gone.

Target: full suite green before Phase 2 PR opens. Current Phase 1 baseline is 93 tests passing.

---

## 8. Open questions for Phase 2 (answer before code)

1. **Scoring theory call (from §PY3).** Confirm we keep the live `compute_risk_score` theory and discard `scoring_v2::score_call`? My strong rec is yes. If no, I need direction on how to reconcile (calibration exercise? A/B? vote among clinicians?).

2. **Double-Amber rule strictness.** My proposed rule is "≥2 domains with `deteriorating` AND `above_upper_bound`". Clinically tighter alternative: "≥2 domains with `deteriorating` only" (doesn't require above_upper). Looser: "≥2 domains with `above_upper_bound` only" (doesn't require trend). Which encoding matches your clinical intent? The stub is already the strictest of the three — confirm or relax.

3. **Validation module scope.** I've scoped two rules (first-call-all-4s, drop-to-empty). The brief hints at more (`e.g. validation.py — Pre-scoring sanity checks`). Are there other rules you want in Phase 2, or does this pair cover the pilot-blocking cases? If more, name them — I won't invent them.

4. **Orphan table drops (§6 D2, revised by §6A).** Approving the revised plan: DROP `domain_scores` only; KEEP `pathway_soap_notes` (as a candidate Phase 4 relational home for SOCRATES findings); KEEP `patient_red_flags`. Conservative alternative: PLAN the `domain_scores` drop in Phase 2, execute it in a separate dedicated cleanup PR. Preference?

5. **Branch strategy.** Phase 1 shipped on `main` (I assume, since I didn't see a branch rename). Should Phase 2 go on a feature branch given the consolidation diff size (~15 files moved, ~5 created, ~3 deleted)? My instinct is yes — estimate 800-1200 lines of diff, hard to review in a single commit.

---

## 9. Estimated diff size for Phase 2 (revised post §6A)

- File moves (git mv): 9 files
- File deletions: scoring_v2 (3 files) + demo.py + tests/test_engine.py + dead helpers = 7 deletions
- Net-new: models.py (~400 lines incl. SOCRATES models), scoring.py additions (~120 lines), validation.py (~90 lines), `pathways/_probes.py` (~180 lines of ported probe content), 5 new test files (~520 lines combined incl. test_socrates_probes.py), stubs (~30 lines)
- Call-site rewrites: ~12 import statement changes
- Alembic migration (revised): drop `domain_scores` + add `soap_notes.socrates_findings` ~35 lines
- **Total: ~1300 lines of net diff**, heavy on moves-plus-imports which read fast in a PR
- Of which **~250 lines are SOCRATES-related** (models + ported content + tests)

Rough time-to-review: 60-80 minutes for a diligent reviewer who already knows Phase 1.

**Cross-repo note:** SOCRATES probe content is being ported FROM `healthcare-voice-agent/agent/system_prompt.py` INTO `sizor-ai-platform/backend/app/clinical_intelligence/pathways/_probes.py`. The voice-agent still imports its local copy at Phase 2 completion — the voice-agent refactor to consume probes via the platform API is a separate follow-up PR, out of Phase 2 scope. This means Phase 2 leaves both copies live temporarily; they don't diverge because voice-agent doesn't modify its copy. A follow-up ticket (tracked in the CHANGELOG) removes the voice-agent copy once the API wiring lands.

---

## Phase 1 — archive (complete; applied to dev 2026-04-24)

Migration `b1c3d5e7f91a` applied. Distribution: 47 extracted / 49 stale_pre_calibration / 52 empty. ORM drift fix landed. 4 alignment tests added. 93 tests passing. Backup retained at `~/sizor_dev_backup_20260424_104233.sql`.

Three forward-looking items landed as decisions carried into Phase 2 (now addressed in §6 above):
- D1 (stranded patients — James 25 ext, Doris Patel 21 ext, Robert Davies 3 ext)
- D2 (orphan tables — `domain_scores`, `pathway_soap_notes`, `patient_red_flags`)
- D3 (critical-medication weighting)

One finding carried from Phase 1 closeout:
- The four-patient validation cohort (Khegis, Bukayo, Tinu, Tayo) are **post-cutover**. Their data-quality issues (miscalibrated vte=4, pre-calibration all-4s, drop-to-empty, duplicates) are a **different class of problem** than Phase 1 addressed. Phase 1 fixed *pre-cutover* data gaps; *post-cutover mis-extracted rows* need a separate repair path. **Flagged for Phase 2 or Phase 3 decision: which phase owns the repair path for post-cutover mis-extracted rows?** My preliminary read is Phase 3 — once the Required Questions Manifest exists, a coverage-driven re-extraction under Phase 3 pathway content naturally subsumes per-row repair. But that depends on whether re-running extraction against the transcript is on the table. Confirm in Q6 below.

---

**Q6 (added):** Post-cutover mis-extracted rows — Phase 2 (include in consolidation, with a dedicated repair script) or Phase 3 (subsumed by Required Questions Manifest-driven re-extraction)? My rec is Phase 3.

# Sizor Clinical Intelligence Refactor — Plan

**Scope:** `sizor-ai-platform/backend/` only.

**Current phase:** **Phase 2** — consolidation. Phase 1 (data integrity) is complete and applied to dev; its record is archived at the bottom of this document.

**Gate:** no code until this plan is approved. Same pattern as Phase 1.

---

## Pre-work answers (questions you told me to ask, not guess at)

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

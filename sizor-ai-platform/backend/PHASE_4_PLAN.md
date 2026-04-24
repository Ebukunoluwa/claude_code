# Phase 4 — Coverage Enforcement

**Status: DONE** (2026-04-24). 7 commits on `phase-4-coverage-enforcement`
(from `8051887` Phase 3 merge). 175 → 315 tests, all green. Alembic head
at `f5a7b9c1d3e4`. Ready for review + merge to `main`.

**Branch:** `phase-4-coverage-enforcement`
**Base:** `main` at `8051887` (Phase 3 merge, already pushed)
**Scope:** `sizor-ai-platform/backend/` only

### Commits landed

| SHA | Subject |
|---|---|
| `e8498a0` | D1: CoverageReport Pydantic + CallCoverageReport ORM |
| `16ea2b9` | D6: Alembic migration `f5a7b9c1d3e4` |
| `629a461` | D2+D3: build_required_questions + build_red_flag_probes |
| `59b6a43` | D5: get_mandatory_call_checklist |
| `c3eda88` | D4: validate_call_coverage LLM classifier |
| `34a59e1` | D8: coverage_enforcement_enabled + coverage_threshold |
| `0dc3c6c` | D7: pipeline wire-in (Task 1b) + integration test |

### Decisions locked in with reviewer

1. **Insertion point** — Task 1b between extraction upsert and SOAP
   generation. Approved.
2. **Coverage threshold default** — 0.80. Approved. `CLINICAL_REVIEW_NEEDED`
   comment at definition: "default for v1; clinician to confirm per pathway
   risk profile; may fork by pathway in Phase 6."
3. **Decline-as-asked semantics** — approved. Declined items count as
   covered; listed separately in `required_questions_patient_declined`
   for dashboard visibility.
4. **Branch base** — Phase 3 merged to main first (`7b7ba8e..8051887`
   pushed to origin), Phase 4 branched from fresh main.
5. **FAIL-OPEN guarantee** — explicit for D7: Task 1b wrapped in two
   layered try/except blocks. Never crashes the pipeline. Extraction +
   SOAP always run regardless of coverage outcome. Failed coverage
   persists as a NULL-coverage row.

---

## What this phase does

Phase 3 produced the clinical content — 107 Required Questions and 167 Red Flag Probes across 14 active pathways. Nothing today forces Sarah (the voice agent) to actually ask those items, and nothing records which ones were covered vs silently skipped. Phase 4 builds:

1. A per-call **Coverage Report** — what was asked, what the patient answered, what was silently skipped, whether every red-flag probe was asked.
2. The **structured checklist** the prompt builder will embed in Phase 6.
3. Post-call **LLM-based coverage classification** against the transcript.
4. **Pipeline wiring** to run coverage after extraction and persist the report.
5. **Dashboard signal** when coverage is incomplete or a red-flag probe was missed.

Phase 4 **consumes Phase 3 content verbatim**. It makes no clinical-content judgements and modifies no Phase 3 files.

---

## Current state — read before approving

### Pipeline flow (pre-Phase-4)

`pipeline_tasks.py::process_call` is 574 lines. Flow:

1. `CallRecord` + `Patient` load.
2. Voicemail detection via lexical match against answerphone phrases; skip pipeline if ≥60% of patient lines match.
3. Active pathway lookup via raw SQL on `patient_pathways`.
4. **Task 1**: `extract_clinical_scores(transcript, domains)` → LLM → 0-4 domain scores + 0-10 generic scores + `condition_specific_flags`.
5. Domain → generic bridge + carry-forward from prior non-probe `extraction_status='extracted'` rows (5-step walkback per Phase 2.5).
6. `ClinicalExtraction` upsert.
7. **Task 2**: SOAP note generation.
8. **Task 3**: FTP assessment.
9. **Task 4**: flag evaluation + current EWMA smoothing + risk score.
10. **Task 5**: longitudinal summary (version bump).
11. **Task 6**: playbook regeneration for next call.

### LLM pattern (to match)

```python
llm = LLMClient()
resp = await llm.complete(system_prompt, user_prompt)
result = _parse_json(resp)  # from services/post_call_pipeline.py
```

- `LLMClient.complete(system, user)` → `str` via LiteLLM.
- Temperature 0.3.
- Model from `settings.llm_model`.
- `_parse_json` handles raw JSON, markdown-fenced JSON, and first-brace-to-last-brace fallback.

### Phase 3 registries available

`from app.clinical_intelligence.pathways import (PATHWAYS, REQUIRED_QUESTIONS, RED_FLAG_PROBES)`

- `REQUIRED_QUESTIONS[opcs]` → `list[RequiredQuestion]` (each has `domain`, `question_text`, `day_ranges: list[tuple[int, int]]`).
- `RED_FLAG_PROBES[opcs]` → `dict[flag_code, RedFlagProbe]` (each has `patient_facing_question`, `parent_flag_code`, `follow_up_escalation`, `category`).

Z03_MH scaffold has empty lists/dicts — coverage for Z03_MH will legitimately be 0% / 0 probes-asked until mental-health clinician sign-off.

---

## Proposed insertion point in `pipeline_tasks.py`

**New Task 1b, inserted between current Task 1 (extraction upsert) and Task 2 (SOAP).**

Rationale:

- Reads same input (transcript) as extraction; no ordering dependency on SOAP / FTP / flags / smoothing.
- Orthogonal output (new table); never mutates `ClinicalExtraction` or downstream state.
- Failure-isolated: its own `try/except` logs error and stores `coverage_percentage=NULL`, pipeline continues.
- After extraction is stored, so the coverage row can FK to extraction later if we decide to join them. Keeping it a sibling of extraction (both FK to `call_id`) is simpler for now.

**Insertion sketch**:

```python
# ── Task 1b: Coverage enforcement (Phase 4) ──────────────────────
try:
    coverage_report = await validate_call_coverage(
        transcript=transcript,
        opcs_code=_opcs_code,
        call_day=day,
    )
    db.add(CallCoverageReport(
        call_id=call.call_id,
        patient_id=call.patient_id,
        **coverage_report.model_dump(),
    ))
    await db.flush()
    if coverage_report.incomplete_items or \
       coverage_report.coverage_percentage < settings.coverage_threshold:
        logger.warning(
            "Call %s coverage below threshold (%.1f%%) — %d items incomplete",
            call_id, coverage_report.coverage_percentage,
            len(coverage_report.incomplete_items),
        )
except Exception as exc:
    logger.error("Coverage validation failed for call %s: %s", call_id, exc, exc_info=True)
    # Do not fail the pipeline.
```

**Approve / adjust / reject** this insertion point before I code it.

---

## Deliverables (one commit per numbered item, tests green between)

### D1. `CoverageReport` Pydantic model + `CallCoverageReport` ORM model

**File**: `app/clinical_intelligence/models.py` (Pydantic) + `app/models/call.py` (ORM).

Pydantic `CoverageReport` fields (per spec):

```
required_questions_expected: list[str]   # question_text entries
required_questions_asked: list[str]
required_questions_patient_declined: list[str]
red_flag_probes_expected: list[str]      # flag_codes
red_flag_probes_asked: list[str]
red_flag_probes_positive: list[str]
socrates_probes_triggered: list[str]     # domain names that scored ≥2
socrates_probes_completed: list[str]
coverage_percentage: float               # 0-100
incomplete_items: list[str]
created_at: datetime = Field(default_factory=datetime.utcnow)
```

ORM `CallCoverageReport`:

- `coverage_report_id` (UUID PK)
- `call_id` FK → `call_records.call_id`
- `patient_id` FK → `patients.patient_id`
- `opcs_code` String(20) — so the report is interpretable without rejoining pathways
- `day_in_recovery` Integer — day-band at time of call
- All `CoverageReport` fields stored:
  - list fields → JSONB
  - `coverage_percentage` → Float (nullable — NULL when LLM classification fails)
  - `created_at` → DateTime(tz=True)
- `raw_classifier_output` JSONB — the full LLM response for audit, never consumed downstream.
- Index on `(patient_id, created_at DESC)` for dashboard queries.

**Test**: Pydantic round-trip + ORM ↔ DB parity test (extend `test_orm_db_schema_parity.py`).

### D2. `build_required_questions(opcs_code, call_day) -> list[RequiredQuestion]`

**File**: `app/clinical_intelligence/coverage.py` (new module).

- Filter `REQUIRED_QUESTIONS[opcs_code]` by day-band match.
- Day-band match: `any(bs <= call_day <= be for (bs, be) in q.day_ranges)`.
- Handle `opcs_code` not in registry → return `[]` + log warning (matches existing defensive style).

**Test**: `test_coverage_build.py`. Assert counts per pathway match Phase 3 totals for each day-band boundary (day 1, day 3, day 14, day 28, day 60, day 90). 14 active pathways × multiple days.

### D3. `build_red_flag_probes(opcs_code) -> list[RedFlagProbe]`

Same module. No day filtering — red flags apply on every call regardless of day.

**Test**: assert counts match Phase 3 totals (167 probes across 14 active pathways; Z03_MH returns `[]`).

### D4. `validate_call_coverage(transcript, opcs_code, call_day) -> CoverageReport`

**Module**: `app/clinical_intelligence/coverage.py`.

LLM-based classifier. Same `LLMClient` pattern as `extract_clinical_scores`:

```python
llm = LLMClient()
system = _build_coverage_system_prompt(expected_rqs, expected_rfps)
user = f"TRANSCRIPT:\n{transcript}"
resp = await llm.complete(system, user)
parsed = _parse_json(resp)
```

System prompt structure:

1. Role statement: "You are a clinical audit reviewer. A post-discharge phone call was conducted. Determine for each required question and red-flag probe below whether the voice agent covered the topic, and whether the patient answered, declined, or the topic was silently skipped."
2. Lists the expected RQs (domain + question_text) + RFPs (flag_code + patient_facing_question).
3. Definitions: **asked** = agent raised the topic; **declined** = patient explicitly said they didn't want to discuss; **silently skipped** = agent moved on without raising; **positive** = patient reported the red-flag symptom.
4. Output JSON schema matching `CoverageReport` list fields — returns `asked` / `declined` / `positive` membership per item.
5. `coverage_percentage = round(100 * asked_count / expected_count, 1)` — computed in Python, not by LLM.

Robustness:

- If JSON parse fails, return a CoverageReport with all `expected` populated from the inputs, empty `asked` lists, `coverage_percentage=0.0`, `incomplete_items=all_expected`, and log the raw response.
- If `opcs_code` is None or unrecognised, return an empty CoverageReport with `coverage_percentage=None` (ORM column is nullable) and log a warning.

**Test**: `test_coverage_validate.py` — five golden transcripts fixture covering the five scenarios from the spec:

1. Perfect call: all RQs asked + answered, all RFPs asked, coverage = 100%.
2. Incomplete call: 2 of 8 RQs silently skipped; coverage ~75%.
3. Patient-declined items: one RQ declined, counted as "asked" for coverage but listed in `patient_declined`.
4. Red-flag positive: one RFP returns positive, appears in `red_flag_probes_positive`.
5. Silent-skip detection: RQ topic never raised in transcript, classifier lists it in `incomplete_items`.

**LLM stub**: tests mock `LLMClient.complete` to return deterministic JSON; not a live LLM call.

### D5. `get_mandatory_call_checklist(opcs_code, call_day) -> str`

Same module. Returns a deterministic string suitable for system-prompt embedding:

```
## MANDATORY CALL CHECKLIST — {pathway_label} (Day {call_day})

You MUST cover every item in the Required Questions list before ending this call.
If the patient explicitly declines to discuss an item, record their decline and
move on. Do not silently skip.

### Required Questions (ask each in this call)
- [{domain}] {question_text}
...

### Red Flag Probes (MUST ASK EVERY CALL regardless of other content)
- [{flag_code}] {patient_facing_question}  (escalation: {follow_up_escalation})
...
```

**Test**: determinism — calling twice with same args returns byte-equal string.

### D6. Alembic migration for `call_coverage_reports` table

**File**: `alembic/versions/f5a7b9c1d3e4_add_call_coverage_reports.py` (or next available hash in linear chain).

- Head-of-chain is `e4f6a8c0b5d2`. New migration parents `e4f6a8c0b5d2`.
- `upgrade()` creates the table with all columns listed in D1.
- `downgrade()` drops the table.
- ORM model parity: extend `test_orm_db_schema_parity.py` to include `call_coverage_reports`.

### D7. Pipeline wire-in

**File**: `app/tasks/pipeline_tasks.py`.

- Insert Task 1b as specified above.
- Add `settings.coverage_threshold: float = 0.80` (CLINICAL_REVIEW_NEEDED — see rules below).
- Add `CallCoverageReport` to `app/models/__init__.py` exports.
- Guard against Z03_MH scaffold: if `REQUIRED_QUESTIONS[opcs_code] == []` and `RED_FLAG_PROBES[opcs_code] == {}`, skip validation (no content to check) and log INFO.

**Test**: end-to-end integration test with a sample transcript + a stubbed LLMClient; assert a `CallCoverageReport` row lands with expected fields.

### D8. Feature flag

**File**: `app/config.py`.

- Add `coverage_enforcement_enabled: bool = True` setting (env-overridable).
- Task 1b short-circuits if flag is False → useful for staged rollout.

---

## Constants flagged `CLINICAL_REVIEW_NEEDED`

1. `coverage_threshold = 0.80` (default). Needs clinician confirmation — 80% means a call is "acceptable" even when missing 20% of required questions. Reviewer may want stricter (e.g. 95%) or to tier (any red-flag-probe missed = non-optional, any RQ missed = soft).
2. Silent-skip-vs-declined distinction — does a patient saying "I don't want to talk about my mood" count against coverage? The spec says no (it's counted as asked). Reviewer to confirm.

These go in the code as `# CLINICAL_REVIEW_NEEDED: ...` comments at definition site.

---

## Testing summary

- `test_coverage_build.py` — per-pathway build against Phase 3 totals.
- `test_coverage_validate.py` — 5 golden-transcript classifier cases with stubbed LLM.
- `test_coverage_checklist.py` — determinism.
- `test_orm_db_schema_parity.py` — extended for `call_coverage_reports`.
- Pipeline integration test — transcript → coverage report row.
- All existing 175 tests still green between every commit.

---

## Open questions — blockers before coding

1. **Insertion point approval** (D7): new Task 1b between extraction and SOAP — approve or relocate?
2. **Coverage threshold value** (80% default): accept or change?
3. **Declined-as-asked semantics**: accept (declined counts toward coverage) or change (declined counts against)?
4. **Branch base**: Phase 3 isn't merged to main locally. Options:
   - (a) Merge Phase 3 to main now, branch Phase 4 from main.
   - (b) Branch Phase 4 from Phase 3 tip (messier but no premature merge to main).
   Preference?

---

## Commit plan (9 commits)

1. D1 — CoverageReport Pydantic + CallCoverageReport ORM
2. D6 — Alembic migration for `call_coverage_reports`
3. D2 + D3 — `build_required_questions` + `build_red_flag_probes` helpers
4. D5 — `get_mandatory_call_checklist`
5. D4 — `validate_call_coverage` (LLM classifier) + golden transcript tests
6. D8 — feature flag in config
7. D7 — pipeline wire-in
8. Integration test — end-to-end with stubbed LLM
9. PHASE_4_PLAN.md status → DONE, summary added

Paste-and-greenlight cadence: summaries every 2-3 commits per your instruction.

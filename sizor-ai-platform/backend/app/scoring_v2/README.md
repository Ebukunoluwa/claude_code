# Sizor Scoring Engine — v1 Rebuild

Deterministic risk scoring for post-discharge patient calls. Replaces the ad-hoc LLM-based scoring with an auditable, testable, clinically defensible module.

## Architectural principle

**The LLM extracts. The engine scores.** These are separate layers with a strict schema contract between them. This is non-negotiable for DCB0129 compliance — you must be able to show exactly how a risk score was computed.

```
transcript ──[Claude Sonnet]──> CallExtraction ──[this engine]──> RiskScore ──> Postgres
              (structured       (JSON schema)    (pure function)   (audit trail)
               extraction)
```

## The maths

```
S_t = w_state · State_t  +  w_trajectory · Trajectory_t  +  Modifiers_t

State_t       = 25 · Σ α_i · d_i                    # weighted 0-4 domain scores, scaled to 0-100
EWMA_t        = λ · State_t + (1-λ) · EWMA_{t-1}    # smoothed call history (λ=0.3 by default)
Trajectory_t  = max(0, EWMA_t - E(pathway, day))    # deviation above expected recovery curve
Modifiers_t   = capped additive bumps (adherence, social, missed calls)

Red flags     → override: final_score = 100, band = RED
```

## Why this fixes the "23 → 82" problem

- **State only** moves on *current symptoms*, not behaviours like missed meds.
- **Trajectory** smooths via EWMA — one bad call doesn't dominate.
- **Adherence** is a *modifier* (capped at +25 total), not a symptom.
- **Red flags** are detected deterministically, not inferred from aggregate scores.

Result: a missed dose on a stable patient nudges ~8–12 points, as verified in `demo.py`. Chest pain immediately jumps to 100/RED. A real deterioration trend climbs steadily across 2–3 calls rather than oscillating.

## File layout

```
sizor_scoring/
  __init__.py
  models.py     # Pydantic contract between LLM and engine
  config.py     # YAML pathway config loader + hashing for audit
  engine.py     # score_call() — pure deterministic function
config/
  pathways.yaml # Per-pathway domain weights, recovery curves, compound red flags
tests/
  test_engine.py # 9 tests covering stability, red flags, trajectory, audit
demo.py          # Walkthrough of canonical scenarios
```

## Integration into the FastAPI backend

Replace whatever currently lives in the post-call reasoning step with:

```python
from sizor_scoring import score_call, load_config
from sizor_scoring.models import CallExtraction, PatientHistory

config = load_config("config/pathways.yaml")  # load once at startup

# 1. LLM (Claude Sonnet) extracts CallExtraction from transcript.
#    Use function calling / structured outputs to enforce the Pydantic schema.
extraction: CallExtraction = await extract_from_transcript(transcript, pathway)

# 2. Load prior smoothed state from Postgres.
history = await load_patient_history(extraction.patient_id, extraction.pathway)

# 3. Score — pure function, no I/O, no randomness.
risk = score_call(extraction, history, config)

# 4. Persist EVERYTHING (inputs, outputs, breakdown, config hash).
await persist_scoring_result(extraction, risk)

# 5. The dashboard reads from the persisted row.
```

## What the LLM prompt should return

Constrain the Sonnet extraction prompt to return a `CallExtraction`-compatible JSON object with:

- One `DomainObservation` per pathway-defined domain, with `raw_score` (0–4), `evidence_quote` from the transcript, and `confidence`.
- Any detected `RedFlag`s from the fixed enum.
- `AdherenceStatus` and `SocialFactors` as structured fields.
- Never ask the LLM to produce the final score or band.

## Clinical safety / audit

Every `RiskScore` includes a `ScoringBreakdown` with:

- All component values (state, trajectory, modifier total + detail)
- The weights and λ used
- Expected score at that pathway/day
- Rubric version + config hash

This is what you show a DCB0129 assessor. The config hash changes any time `pathways.yaml` is edited, making every rubric change traceable.

## Calibration over time

The default weights (`w_state=0.6`, `w_trajectory=0.4`, `λ=0.3`) and the expected recovery curves are starting points. Once you have clinician-labelled call data:

1. Fit λ to minimise false-alarm rate while preserving sensitivity.
2. Fit domain weights α per pathway via logistic regression on "clinician would escalate" labels.
3. Replace the linear expected curve with an empirical percentile curve from recovering cohorts.

## Running

```bash
pip install pydantic pyyaml pytest
pytest tests/ -v
python demo.py
```

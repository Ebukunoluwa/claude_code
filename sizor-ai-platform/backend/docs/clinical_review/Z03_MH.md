# Z03_MH — Acute Psychiatric Admission — Clinical Review Draft

| Field | Value |
|---|---|
| **Status** | draft_awaiting_clinical_review |
| **Primary reviewer** | Mental health clinician (sign-off required) |
| **Category** | mental_health |
| **NICE sources** | CG136, NG10, QS80 |
| **Monitoring window** | 90 days |
| **Call days** | 1, 3, 7, 14, 21, 28, 42, 60, 90 |
| **Domains** | `medication_concordance`, `mood_and_mental_state`, `safety_and_safeguarding`, `community_team_engagement`, `crisis_plan_awareness`, `social_support_and_daily_living`, `substance_use_screen` |
| **Upstream red flag codes** | `suicidal_ideation_active`, `medication_stopped_abruptly`, `psychotic_relapse`, `risk_to_others`, `safeguarding_concern`, `missing_from_contact` |

## Domain trajectories

### `medication_concordance` — _no source_

_(no trajectory rows)_


### `mood_and_mental_state` — _no source_

_(no trajectory rows)_


### `safety_and_safeguarding` — _no source_

_(no trajectory rows)_


### `community_team_engagement` — _no source_

_(no trajectory rows)_


### `crisis_plan_awareness` — _no source_

_(no trajectory rows)_


### `social_support_and_daily_living` — _no source_

_(no trajectory rows)_


### `substance_use_screen` — _no source_

_(no trajectory rows)_


## Required Questions Manifest

_(no required questions)_

## Red Flag Probes

One observation per probe. Where a single upstream flag splits into multiple probes (e.g. `postpartum_haemorrhage` → `_volume` / `_clots` / `_haemodynamic`), all children are listed under the same header with their `parent_flag_code`.

_(no red flag probes)_

## Reviewer checklist

### Trajectory values
- [ ] Expected/upper-bound values clinically reasonable for each day + domain?
- [ ] Day coverage matches the playbook `call_days`?
- [ ] Any values that feel too conservative or too permissive?

### Required questions
- [ ] Every question clinically necessary?
- [ ] Any critical items missing for this pathway?
- [ ] Day-band placement appropriate?
- [ ] Wording acceptable for a voice agent to read aloud?
- [ ] Multi-part phrasings decompose into independently scoreable parts?

### Red flag probes
- [ ] Patient-facing wording free of clinical jargon?
- [ ] Escalation tier (999 / same_day / urgent_gp / next_call) appropriate?
- [ ] Every probe asks ONE clinical question (no compound 'or' phrasing)?
- [ ] Split parent codes cover the clinical entity without gaps?
- [ ] Non-judgmental framing for mental-health items?

### CLINICAL_REVIEW_NEEDED flags

_(no CLINICAL_REVIEW_NEEDED flags in source)_

## Sign-off

- Reviewer name:
- Review date:
- Revised `validation_status` (circle): `clinician_reviewed` / `production_signed_off` / `remains_draft_with_notes`
- Comments:

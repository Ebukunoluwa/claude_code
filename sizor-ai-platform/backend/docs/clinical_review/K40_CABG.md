# K40_CABG — Coronary Artery Bypass Graft — Clinical Review Draft

| Field | Value |
|---|---|
| **Status** | draft_awaiting_clinical_review |
| **Primary reviewer** | Cardiothoracic surgeon |
| **Category** | surgical |
| **NICE sources** | NG185, CG172, QS99, NG238 |
| **Monitoring window** | 90 days |
| **Call days** | 1, 3, 7, 14, 21, 28, 42, 60, 90 |
| **Domains** | `sternal_wound_healing`, `leg_wound_healing`, `chest_pain_recurrence`, `antiplatelet_adherence`, `cardiac_rehab_attendance`, `mood_and_depression`, `mobility_and_fatigue` |
| **Upstream red flag codes** | `chest_pain_at_rest`, `chest_pain_on_minimal_exertion`, `sternal_wound_breakdown`, `pe_symptoms`, `cardiac_arrest_signs`, `sustained_palpitations` |

## Domain trajectories

### `sternal_wound_healing` — NG185

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 2 | 3 | Wound intact, pain expected | NG185 |
| 3 | 2 | 3 | Healing — monitor for clicking or discharge | NG185 |
| 7 | 1 | 2 | Healing, sutures/clips in | NG185 |
| 14 | 1 | 2 | Healing well | NG185 |
| 21 | 1 | 1 | Well healed | NG185 |
| 28 | 0 | 1 | Healed | NG185 |
| 42 | 0 | 1 | Healed | NG185 |
| 60 | 0 | 0 | Fully healed | NG185 |
| 90 | 0 | 0 | Fully healed | NG185 |


### `leg_wound_healing` — NG185

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 2 | 3 | Donor site bruising/swelling expected | NG185 |
| 3 | 2 | 3 | Settling | NG185 |
| 7 | 1 | 2 | Healing | NG185 |
| 14 | 1 | 1 | Well healed | NG185 |
| 21 | 0 | 1 | Healed | NG185 |
| 28 | 0 | 1 | Healed | NG185 |
| 42 | 0 | 0 | Healed | NG185 |
| 60 | 0 | 0 | Healed | NG185 |
| 90 | 0 | 0 | Healed | NG185 |


### `chest_pain_recurrence` — CG172 / NG185

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 2 | 3 | Musculoskeletal chest pain expected | NG185 |
| 3 | 2 | 2 | Reducing sternal pain | NG185 |
| 7 | 1 | 2 | Mild musculoskeletal pain only | NG185 |
| 14 | 1 | 2 | Minimal pain | NG185 |
| 21 | 1 | 1 | Resolving | CG172 |
| 28 | 0 | 1 | Resolved | CG172 |
| 42 | 0 | 1 | Resolved | CG172 |
| 60 | 0 | 0 | Resolved | CG172 |
| 90 | 0 | 0 | Resolved | CG172 |


### `antiplatelet_adherence` — CG172

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 1 | 1 | Aspirin commenced | CG172 |
| 3 | 1 | 1 | Adherent | CG172 |
| 7 | 1 | 1 | Adherent — lifelong | CG172 |
| 14 | 1 | 1 | Adherent | CG172 |
| 21 | 1 | 1 | Adherent | CG172 |
| 28 | 1 | 1 | Adherent | CG172 |
| 42 | 1 | 1 | Adherent | CG172 |
| 60 | 1 | 1 | Adherent | CG172 |
| 90 | 1 | 1 | Adherent — lifelong | CG172 |


### `cardiac_rehab_attendance` — NG238

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 1 | 2 | Referral made | NG238 |
| 3 | 1 | 2 | Awaiting start | NG238 |
| 7 | 1 | 1 | Programme started or imminent | NG238 |
| 14 | 1 | 1 | Attending | NG238 |
| 21 | 1 | 1 | Attending | NG238 |
| 28 | 1 | 1 | Attending | NG238 |
| 42 | 1 | 1 | Ongoing | NG238 |
| 60 | 1 | 1 | Ongoing | NG238 |
| 90 | 0 | 1 | Programme completing | NG238 |


### `mood_and_depression` — CG172

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 1 | 2 | Low mood common post-CABG | CG172 |
| 3 | 1 | 2 | Monitor for depression | CG172 |
| 7 | 1 | 2 | Depression risk peak week 1-4 | CG172 |
| 14 | 1 | 2 | Screen for depression | CG172 |
| 21 | 1 | 1 | Improving mood expected | CG172 |
| 28 | 1 | 1 | Mood stabilising | CG172 |
| 42 | 1 | 1 | Mood improving | CG172 |
| 60 | 0 | 1 | Near-baseline mood | CG172 |
| 90 | 0 | 1 | Near-baseline mood | CG172 |


### `mobility_and_fatigue` — NG185

| Day | Expected | Upper bound | Expected state | NICE |
|---:|---:|---:|---|---|
| 1 | 2 | 3 | Marked fatigue expected | NG185 |
| 3 | 2 | 3 | Fatigue high | NG185 |
| 7 | 2 | 2 | Gradually improving | NG185 |
| 14 | 1 | 2 | Improving | NG185 |
| 21 | 1 | 2 | Walking short distances | NG185 |
| 28 | 1 | 1 | Increasing activity | NG185 |
| 42 | 1 | 1 | Good activity levels | NG185 |
| 60 | 0 | 1 | Near-normal activity | NG185 |
| 90 | 0 | 1 | Near-normal activity | NG185 |


## Required Questions Manifest

### Day 1-3

| Domain | Question |
|---|---|
| `sternal_wound_healing` | How is the scar on your chest looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it? |
| `leg_wound_healing` | How is the scar on your leg looking — the place where they took the vein — any redness, swelling, or fluid from it? |
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `sternal_wound_healing` | Are you keeping to the sternal precautions — not lifting anything over about 5 pounds, not pushing or pulling heavy doors, not reaching both arms out at once, and not driving yet? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 4-7

| Domain | Question |
|---|---|
| `sternal_wound_healing` | How is the scar on your chest looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it? |
| `leg_wound_healing` | How is the scar on your leg looking — the place where they took the vein — any redness, swelling, or fluid from it? |
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `sternal_wound_healing` | Are you keeping to the sternal precautions — not lifting anything over about 5 pounds, not pushing or pulling heavy doors, not reaching both arms out at once, and not driving yet? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mood_and_depression` | How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 8-14

| Domain | Question |
|---|---|
| `sternal_wound_healing` | How is the scar on your chest looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it? |
| `leg_wound_healing` | How is the scar on your leg looking — the place where they took the vein — any redness, swelling, or fluid from it? |
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `sternal_wound_healing` | Are you keeping to the sternal precautions — not lifting anything over about 5 pounds, not pushing or pulling heavy doors, not reaching both arms out at once, and not driving yet? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mood_and_depression` | How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 15-28

| Domain | Question |
|---|---|
| `sternal_wound_healing` | How is the scar on your chest looking — any redness spreading beyond the immediate scar area, any swelling that's worse in the last 24 hours, or fluid coming from it? |
| `leg_wound_healing` | How is the scar on your leg looking — the place where they took the vein — any redness, swelling, or fluid from it? |
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `sternal_wound_healing` | Are you keeping to the sternal precautions — not lifting anything over about 5 pounds, not pushing or pulling heavy doors, not reaching both arms out at once, and not driving yet? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mood_and_depression` | How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 29-42

| Domain | Question |
|---|---|
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mood_and_depression` | How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 43-60

| Domain | Question |
|---|---|
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `antiplatelet_adherence` | Are you taking your aspirin each day as a heart blood-thinner, and any side effects like stomach upset or unusual bruising? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mood_and_depression` | How's your mood been since the operation — any low feelings, worry, or trouble getting motivated to do the things you normally would? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |

### Day 61-90

| Domain | Question |
|---|---|
| `chest_pain_recurrence` | Any chest pain or discomfort in the last 24 hours — including the 'clicking' feeling some people get from the chest bone, and any tight, crushing, or central chest pain? |
| `cardiac_rehab_attendance` | Has the cardiac rehab team been in touch with you — have you started any sessions yet, or do you know when they'll begin? |
| `mobility_and_fatigue` | How's your energy been — can you walk around the house, manage stairs, and are you finding day-to-day tasks getting easier? |


## Red Flag Probes

One observation per probe. Where a single upstream flag splits into multiple probes (e.g. `postpartum_haemorrhage` → `_volume` / `_clots` / `_haemodynamic`), all children are listed under the same header with their `parent_flag_code`.

### `cardiac_arrest_signs` (1 probe)

**`cardiac_arrest_witnessed_collapse`** → pathway_specific / 999
> Has anyone around you — family, carer, or neighbour — found you collapsed and unresponsive in the last few days, or had to call for emergency help for you?

_NICE basis:_ NG185 / CG172

### `chest_pain_at_rest` (1 probe)

**`chest_pain_at_rest`** → chest_pain / 999
> Have you had chest pain that came on at rest — while sitting still, lying down, or not doing anything — and felt tight, crushing, or central rather than a sharp or sternal ache?

_NICE basis:_ NG185 §1.3 / CG172

### `chest_pain_on_minimal_exertion` (1 probe)

**`chest_pain_on_minimal_exertion`** → chest_pain / same_day
> Have you had chest pain come on with a small effort today — like standing up from a chair, walking across a room, or climbing one flight of stairs — and felt tight or crushing rather than a sternal ache?

_NICE basis:_ NG185 §1.3 / CG172

### `pe_symptoms` (split into 2 probes)

**`pe_symptoms_breathing`** → acute_shortness_of_breath / 999
> Have you had any sudden breathlessness today that made you stop what you were doing?

_NICE basis:_ NG89 §1.3 / NG158

**`pe_symptoms_chest_pain`** → chest_pain / 999
> Any sharp chest pain on one side — especially when you breathe in deeply?

_NICE basis:_ NG89 §1.3 / NG158

### `sternal_wound_breakdown` (split into 3 probes)

**`sternal_wound_clicking`** → pathway_specific / same_day
> Can you feel any clicking, grinding, or moving feeling in your breast bone when you cough, take a deep breath, or turn in bed?

_NICE basis:_ NG185 §1.5

**`sternal_wound_discharge`** → pathway_specific / same_day
> Is there any pus or bloody fluid coming from the chest scar?

_NICE basis:_ NG185 §1.5 / QS48

**`sternal_wound_separation`** → pathway_specific / 999
> Has the scar on your chest opened up — with a visible gap between the edges, or can you see the breast bone underneath?

_NICE basis:_ NG185 §1.5

### `sustained_palpitations` (split into 2 probes)

**`palpitations_sustained`** → pathway_specific / same_day
> Have you had any sudden fluttering or racing heartbeat — palpitations — that lasted more than about half an hour, or that kept coming back today?

_NICE basis:_ NG185 / CG172

**`palpitations_with_red_flag_symptoms`** → pathway_specific / 999
> When the fluttering or racing happened, did you also get chest pain, breathlessness, or feel like you might pass out?

_NICE basis:_ NG185 / CG172


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

- [ ] CLINICAL_REVIEW_NEEDED: upstream pathway_map.red_flags for K40 lists only "chest_pain_at_rest". Added "chest_pain_on_minimal_exertion" as a separate parent for the SAME_DAY probe. Reviewer to confirm whether this new parent code should propagate to the upstream map + dashboards, or whether the two probes should share a single parent "chest_pain" with the tier delta resolved at Phase 4.
- [ ] CLINICAL_REVIEW_NEEDED: compound rule for Phase 4 call-status layer — chest_pain_on_minimal_exertion + any breathlessness or syncope probe firing together suggests crescendo angina / re- infarction and should escalate to EMERGENCY_999.
- [ ] CLINICAL_REVIEW_NEEDED: K40_CABG inherits K40's new parent code "chest_pain_on_minimal_exertion". Same upstream-map propagation decision applies — reviewer to confirm once for the whole cardiac cluster rather than per-pathway.
- [ ] CLINICAL_REVIEW_NEEDED: cardiac_arrest_witnessed_collapse uses coverage-check framing because the patient cannot self-report loss of consciousness with no return of pulse. Reviewer to confirm: should this also gate behind an explicit "is anyone with you?" intake flag at the voice-agent layer rather than rely on whoever answers the call?
- [ ] CLINICAL_REVIEW_NEEDED: K60 chest_pain probes use the same parent codes as K40 / K40_CABG (chest_pain_at_rest + chest_pain_ on_minimal_exertion). Reviewer to confirm whether K60-specific compound rule should exist at Phase 4 — chest pain + breathless- ness at rest + weight gain + new oedema is the acute-on-chronic decompensation picture and warrants EMERGENCY_999.
- [ ] CLINICAL_REVIEW_NEEDED: anuric_or_oliguria probe uses 12-hour anuria threshold. Reviewer to confirm this is the correct voice- agent threshold (some NG106 local protocols use 8 hours).
- [ ] CLINICAL_REVIEW_NEEDED: bp_crisis_above_180 probe conditional on home BP monitor. Reviewer to confirm whether the voice agent should offer an in-clinic BP check path for patients without a home monitor (rather than no probe at all).

## Sign-off

- Reviewer name:
- Review date:
- Revised `validation_status` (circle): `clinician_reviewed` / `production_signed_off` / `remains_draft_with_notes`
- Comments:

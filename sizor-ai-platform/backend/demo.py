"""Quick walkthrough: run the engine on the scenarios from our conversation."""
from datetime import datetime
from pathlib import Path

from app.scoring_v2 import (
    CallExtraction, DomainObservation, PatientHistory,
    RedFlag, RedFlagType, score_call, load_config,
)
from app.scoring_v2.models import AdherenceStatus, SocialFactors

cfg = load_config(Path("config/pathways.yaml"))


def ext(scores, meds=True, critical=False, doses=0, flags=None, day=5):
    return CallExtraction(
        patient_id="P001", call_id="c", call_timestamp=datetime.now(),
        pathway="post_cardiac_surgery", day_post_discharge=day,
        domain_observations=[
            DomainObservation(domain=d, raw_score=s, evidence_quote="", confidence=0.9)
            for d, s in scores.items()
        ],
        red_flags=flags or [],
        adherence=AdherenceStatus(
            medication_taken_as_prescribed=meds,
            missed_doses_reported=doses,
            critical_medication=critical,
        ),
        social=SocialFactors(),
        extraction_model="demo", extraction_schema_version="1.0",
    )


BASELINE = {"pain": 1, "breathlessness": 1, "wound": 0,
            "chest_symptoms": 0, "mood": 1, "adherence": 0}


print("SCENARIO 1 — Stable patient, day 5 post-op, recovering on track")
h1 = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                    prior_smoothed_state=20.0, prior_call_count=3)
r = score_call(ext(BASELINE), h1, cfg)
print(f"  state={r.breakdown.state_score:.1f}  traj={r.breakdown.trajectory_score:.1f}  "
      f"mods={r.breakdown.modifier_total:.1f}  →  FINAL={r.final_score:.1f}  {r.band.value}")
print(f"  action: {r.recommended_action}\n")

print("SCENARIO 2 — Same patient, missed ONE non-critical dose")
r = score_call(ext(BASELINE, meds=False, doses=1), h1, cfg)
print(f"  state={r.breakdown.state_score:.1f}  traj={r.breakdown.trajectory_score:.1f}  "
      f"mods={r.breakdown.modifier_total:.1f}  →  FINAL={r.final_score:.1f}  {r.band.value}")
print(f"  action: {r.recommended_action}\n")

print("SCENARIO 3 — Missed TWO doses of a CRITICAL med (anticoagulant)")
r = score_call(ext(BASELINE, meds=False, doses=2, critical=True), h1, cfg)
print(f"  state={r.breakdown.state_score:.1f}  traj={r.breakdown.trajectory_score:.1f}  "
      f"mods={r.breakdown.modifier_total:.1f}  →  FINAL={r.final_score:.1f}  {r.band.value}")
print(f"  action: {r.recommended_action}\n")

print("SCENARIO 4 — Trajectory worsening over 3 calls")
h = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                   prior_smoothed_state=None, prior_call_count=0)
for day, scores in [(3, {"breathlessness": 2, "pain": 2}),
                    (5, {"breathlessness": 3, "pain": 2}),
                    (7, {"breathlessness": 3, "pain": 3})]:
    full = {**BASELINE, **scores}
    r = score_call(ext(full, day=day), h, cfg)
    print(f"  day {day}: state={r.breakdown.state_score:.1f}  "
          f"smoothed={r.breakdown.smoothed_state:.1f}  traj={r.breakdown.trajectory_score:.1f}  "
          f"→  FINAL={r.final_score:.1f}  {r.band.value}")
    h = PatientHistory(patient_id="P001", pathway="post_cardiac_surgery",
                       prior_smoothed_state=r.breakdown.smoothed_state,
                       prior_call_count=h.prior_call_count + 1)

print("\nSCENARIO 5 — Patient reports chest pain (hard red flag override)")
r = score_call(
    ext(BASELINE, flags=[RedFlag(type=RedFlagType.CHEST_PAIN,
                                  evidence_quote="tight crushing chest pain")]),
    h1, cfg,
)
print(f"  FINAL={r.final_score:.1f}  {r.band.value}  (override active: {r.breakdown.red_flag_override})")
print(f"  action: {r.recommended_action}")

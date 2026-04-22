"""
Seed script: Michael Kenomore — Right Total Knee Replacement (TKA)
NICE NG157 + NG89: 42-day post-discharge monitoring pathway
Run: docker compose exec backend python3 seed_michael.py
"""
import asyncio
import uuid
from datetime import datetime, date, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models import (
    Patient, PatientMedicalProfile,
    CallRecord, SOAPNote, UrgencyFlag, FTPRecord,
    CallSchedule, LongitudinalSummary,
)
from app.models.call import ClinicalExtraction

# ── Constants ────────────────────────────────────────────────────────────────
HOSPITAL_ID   = uuid.UUID("df590695-681a-4533-9568-07fec28e533d")
DISCHARGE     = date(2026, 3, 26)   # Day 0 — today is Day 20 (April 15)
PATIENT_ID    = uuid.uuid4()

def dt(d: date, hour=9, minute=0) -> datetime:
    """Localised datetime for a given day-offset from discharge."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)

def day(n: int) -> date:
    return DISCHARGE + timedelta(days=n)

# ── Clinical score trajectory ─────────────────────────────────────────────
# Scores 0-10: lower = better recovery. TKA expected trajectory (NICE NG157).
CALLS = [
    # (day, status, pain, breathlessness, mobility, appetite, mood, adherent, duration_s)
    (1,  "completed", 8.2, 1.5, 8.5, 4.0, 5.0, True,  312),
    (2,  "missed",    None,None, None, None,None,None,  None),
    (3,  "completed", 7.1, 1.2, 7.8, 3.5, 4.5, True,  287),
    (5,  "completed", 6.3, 1.0, 7.2, 3.0, 4.0, True,  341),
    (7,  "completed", 5.4, 1.0, 6.5, 2.8, 3.8, True,  298),
    (10, "completed", 4.8, 0.8, 6.1, 2.5, 3.5, True,  265),
    (12, "missed",    None,None, None, None,None,None,  None),
    (14, "completed", 3.9, 0.7, 5.8, 2.2, 3.0, True,  310),
    (17, "completed", 3.2, 0.5, 5.4, 2.0, 2.8, True,  278),
    (20, "completed", 2.8, 0.5, 5.1, 1.8, 2.5, True,  295),
]

SOAPS = {
    1: {
        "S": "Patient reports severe pain (8/10) in right knee. Swelling noted, difficulty weight-bearing. Using crutches as instructed. Ice pack applied every 2 hours. Struggling to sleep due to discomfort.",
        "O": "Pain 8.2/10. Mobility severely limited. Rivaroxaban taken as prescribed. Wound dressing intact per patient report. Temperature 37.2°C.",
        "A": "Expected post-operative day 1 presentation. Pain and mobility consistent with NICE NG157 early recovery phase. VTE prophylaxis compliant. No red flags.",
        "P": "Continue rivaroxaban 10mg OD for 14 days. Ice, elevation, pain management per discharge plan. Call tomorrow to monitor. Physio to commence day 3.",
    },
    3: {
        "S": "Pain reduced slightly to 7/10. Swelling improving. Patient has been doing gentle ankle pumps. Reports wound site feels 'tight'. Using crutches for all mobilisation. Appetite returning.",
        "O": "Pain 7.1/10. Mobility 7.8/10. Wound site reported as intact with mild serous discharge — patient uncertain if normal. Rivaroxaban compliant.",
        "A": "Day 3 recovery in line with expected trajectory. Mild wound discharge needs monitoring — likely normal serous exudate but flagging for day 5 review. Mobility appropriate for stage.",
        "P": "Continue current plan. Monitor wound closely at next contact. Educate patient on signs of infection: increasing redness, warmth, purulent discharge, fever. Physio exercises to begin.",
    },
    5: {
        "S": "Pain 6/10. Patient reports wound dressing saturated this morning — yellow-tinged discharge. Area around wound feels warm to touch. Concerned. Physio exercises started but painful. Anticoagulation compliant.",
        "O": "Pain 6.3/10. Mobility 7.2/10. Wound seepage described as yellow-tinged, saturating dressing. Localised warmth reported. No systemic fever. Rivaroxaban day 5 of 14.",
        "A": "Wound seepage requires clinical assessment. Yellow-tinged discharge with warmth raises concern for early superficial wound infection or haematoma. Cannot rule out SSI at this stage. AMBER flag raised.",
        "P": "AMBER: Wound review required within 24 hours. Contact GP practice for same-day wound assessment. If fever >38°C, increasing redness, or worsening pain — attend A&E. Continue rivaroxaban. Physio on hold pending wound review.",
    },
    7: {
        "S": "Patient attended GP yesterday. Wound assessed — superficial haematoma, not infected. Dressing changed, wound clean. Pain 5/10, improved from day 5. Physio exercises restarted today. Sleeping better.",
        "O": "Pain 5.4/10. Mobility 6.5/10. Wound confirmed as haematoma by GP, no SSI. Rivaroxaban day 7. Physiotherapy exercises: 3 sets of 10 reps, quad sets and heel slides.",
        "A": "Wound concern resolved — haematoma, not infection. Good response to GP assessment. Recovery trajectory re-established. Mobility improving. Anticoagulation compliant. Day 7 progress satisfactory per NICE NG157.",
        "P": "Continue physiotherapy. Wound monitoring ongoing at home. Rivaroxaban for 7 more days. Next structured call day 10. 2-week GP review approaching.",
    },
    10: {
        "S": "Pain down to 4-5/10. Managing with paracetamol only — no longer needing ibuprofen. Walking short distances indoors without crutches. Physio going well. Finished rivaroxaban course yesterday (day 14 technically day 9 from discharge... confirmed compliant).",
        "O": "Pain 4.8/10. Mobility 6.1/10. VTE prophylaxis completed day 9 post-discharge. Wound healed, no concerns. ROM improving — patient reports bending knee to approximately 90 degrees.",
        "A": "Day 10: Positive trajectory. Pain management transitioning to paracetamol-only appropriate. Mobility improving but lagging slightly against NICE expected 60° ROM at day 7 / 90° at day 14 targets. VTE prophylaxis completed.",
        "P": "Continue physio twice daily. Target 90° ROM by day 14. Next call day 14 for formal 2-week review. Encourage walking with single crutch outdoors if weather permits.",
    },
    14: {
        "S": "Two-week mark. Pain 4/10. Walking with single crutch outdoors. Knee ROM approximately 95 degrees — physio pleased with progress. Sleeping well. Mood improving. Driving still not resumed.",
        "O": "Pain 3.9/10. Mobility 5.8/10. ROM ~95° — meeting NICE 90° target at 2 weeks. Wound fully healed. Off anticoagulants. Outpatient physio referral confirmed for week 4.",
        "A": "2-week review: satisfactory recovery. ROM target met. Pain within acceptable range. Wound healed. No active urgency flags. FTP status: on track. Mood and appetite normalising.",
        "P": "Continue home physio programme. Outpatient physio commencing week 4. Return to driving assessment at 6 weeks. Next monitoring call day 17. Full discharge review day 42 (NICE NG157 6-week endpoint).",
    },
    17: {
        "S": "Pain 3/10. Walking without crutches at home, single crutch outdoors for longer distances. Outpatient physio starts next week. Knee still stiff in the mornings — about 20 minutes to loosen up. Managing stairs but slowly.",
        "O": "Pain 3.2/10. Mobility 5.4/10. Morning stiffness consistent with post-TKA inflammatory response — expected at this stage. Functional mobility improving. No signs of infection or DVT.",
        "A": "Day 17: Good progress. Morning stiffness expected and resolving. Mobility slightly behind optimal NICE trajectory but improving trend. No clinical concerns at this time.",
        "P": "Commence outpatient physio as planned. Continue home exercises. Next call day 20. Monitor mobility progression — if not improving by day 21, consider physiotherapy intensification.",
    },
    20: {
        "S": "Pain 3/10, well controlled. Started outpatient physio 2 days ago. Physio notes ROM at 105° but functional mobility still limited — difficulty on stairs and rising from low chairs. Mood good. Concerned about pace of recovery.",
        "O": "Pain 2.8/10. Mobility 5.1/10. ROM 105° — above NICE 90° minimum but functional mobility lagging. Expected trajectory at day 20: mobility score ~3/10. Current: 5.1/10. Morning stiffness persisting 25 mins.",
        "A": "Day 20: Mobility lagging expected NICE NG157 trajectory. ROM is adequate but functional strength and stair-climbing not meeting day 20 benchmarks. Possible FTP risk — physio intensification required. AMBER flag raised for mobility progress.",
        "P": "AMBER: Escalate physio to daily sessions if possible. Discuss with outpatient physio team. Consider hydrotherapy if available. Reassess at day 21. If no improvement by day 28, refer to orthopaedic consultant for review. Continue monitoring per pathway.",
    },
}

# ── Future schedule (days 21–42 per NICE 6-week pathway) ─────────────────
FUTURE_CALLS = [
    (21, "Routine Check",            "routine"),
    (24, "Mobility & Physio Review", "routine"),
    (28, "4-Week Assessment",        "routine"),
    (35, "Physiotherapy Progress",   "routine"),
    (42, "6-Week Discharge Review",  "follow-up"),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # ── 1. Patient ────────────────────────────────────────────────────
        patient = Patient(
            patient_id    = PATIENT_ID,
            hospital_id   = HOSPITAL_ID,
            full_name     = "Michael Kenomore",
            nhs_number    = "485 777 3214",
            date_of_birth = date(1958, 3, 15),
            phone_number  = "+447700900456",
            condition     = "Total Knee Arthroplasty",
            procedure     = "Right Total Knee Replacement (TKA)",
            discharge_date= DISCHARGE,
            program_module= "orthopaedic-tka-42d",
            status        = "active",
        )
        db.add(patient)

        # ── 2. Medical Profile ────────────────────────────────────────────
        profile = PatientMedicalProfile(
            patient_id            = PATIENT_ID,
            primary_diagnosis     = "Osteoarthritis of right knee — end-stage",
            secondary_diagnoses   = ["Hypertension", "Type 2 Diabetes (well-controlled)", "Obesity (BMI 31)"],
            allergies             = ["Penicillin (rash)"],
            current_medications   = [
                "Metformin 500mg BD",
                "Amlodipine 5mg OD",
                "Paracetamol 1g QDS PRN",
                "Rivaroxaban 10mg OD (completed day 9 post-discharge)",
            ],
            relevant_comorbidities= ["Hypertension", "Type 2 Diabetes", "Obesity"],
            consultant_notes      = (
                "68-year-old male with end-stage right knee OA. "
                "Primary TKA performed 26 March 2026 by Mr A. Patel (Orthopaedic Consultant). "
                "Procedure uneventful. Cemented prosthesis. Tourniquet time 58 mins. "
                "Penicillin allergy documented — co-amoxiclav avoided, cefuroxime used for prophylaxis. "
                "Diabetic management: HbA1c 52 mmol/mol pre-op — acceptable for surgery. "
                "Discharge day 2 post-op as per enhanced recovery protocol."
            ),
            discharge_summary_text= (
                "Michael Kenomore, 68M, admitted 25/03/2026 for elective right TKA. "
                "Operation: Cemented right total knee replacement, posterior-stabilised implant. "
                "Post-op: Enhanced recovery protocol. Physio day 1 — weight-bearing with crutches. "
                "Rivaroxaban 10mg OD for 14 days (VTE prophylaxis per NICE NG89). "
                "Discharged 26/03/2026. Follow-up: 6-week outpatient review per NICE NG157. "
                "Enrolled in Sizor post-discharge monitoring pathway (42 days)."
            ),
        )
        db.add(profile)

        # ── 3. Call Records + Extractions + SOAP Notes ────────────────────
        call_ids = {}
        for (day_n, status, pain, breath, mob, app, mood, adherent, dur) in CALLS:
            call_date = day(day_n)
            call_id   = uuid.uuid4()
            call_ids[day_n] = call_id

            call = CallRecord(
                call_id        = call_id,
                patient_id     = PATIENT_ID,
                direction      = "outbound",
                trigger_type   = "scheduled",
                status         = status,
                started_at     = dt(call_date, hour=9, minute=15),
                ended_at       = dt(call_date, hour=9, minute=15) + timedelta(seconds=dur or 0) if dur else None,
                duration_seconds = dur,
                day_in_recovery  = day_n,
            )
            db.add(call)

            if status == "completed" and pain is not None:
                extraction = ClinicalExtraction(
                    extraction_id          = uuid.uuid4(),
                    call_id                = call_id,
                    patient_id             = PATIENT_ID,
                    pain_score             = pain,
                    breathlessness_score   = breath,
                    mobility_score         = mob,
                    appetite_score         = app,
                    mood_score             = mood,
                    medication_adherence   = adherent,
                    condition_specific_flags = {
                        "wound_concern":       day_n in (3, 5),
                        "vte_prophylaxis_done": day_n >= 10,
                        "physio_commenced":    day_n >= 3,
                        "rom_degrees":         {3:60, 5:70, 7:80, 10:90, 14:95, 17:100, 20:105}.get(day_n),
                    },
                    extracted_at = dt(call_date, hour=9, minute=30),
                )
                db.add(extraction)

                soap_data = SOAPS.get(day_n, {})
                if soap_data:
                    soap = SOAPNote(
                        soap_id           = uuid.uuid4(),
                        call_id           = call_id,
                        patient_id        = PATIENT_ID,
                        subjective        = soap_data["S"],
                        objective         = soap_data["O"],
                        assessment        = soap_data["A"],
                        plan              = soap_data["P"],
                        generated_at      = dt(call_date, hour=9, minute=45),
                        clinician_reviewed= day_n < 20,
                        model_used        = "gpt-4o",
                    )
                    db.add(soap)

        # ── 4. Urgency Flags ──────────────────────────────────────────────
        # Day 5: wound seepage — RESOLVED at day 7
        flag1 = UrgencyFlag(
            flag_id            = uuid.uuid4(),
            patient_id         = PATIENT_ID,
            call_id            = call_ids[5],
            severity           = "amber",
            flag_type          = "wound_concern",
            trigger_description= "Wound seepage reported — yellow-tinged discharge saturating dressing with localised warmth. GP wound review requested.",
            status             = "resolved",
            raised_at          = dt(day(5), hour=9, minute=50),
        )
        db.add(flag1)

        # Day 20: mobility lag — OPEN (current concern)
        flag2 = UrgencyFlag(
            flag_id            = uuid.uuid4(),
            patient_id         = PATIENT_ID,
            call_id            = call_ids[20],
            severity           = "amber",
            flag_type          = "failure_to_progress",
            trigger_description= (
                "Mobility score 5.1/10 at Day 20 — expected ≤3.0/10 per NICE NG157 TKA trajectory. "
                "Functional mobility lagging: difficulty on stairs and rising from low chairs. "
                "ROM adequate (105°) but strength and functional transfer not meeting benchmarks. "
                "Physio intensification recommended."
            ),
            status             = "open",
            raised_at          = dt(day(20), hour=9, minute=50),
        )
        db.add(flag2)

        # ── 5. FTP Record ─────────────────────────────────────────────────
        ftp = FTPRecord(
            patient_id      = PATIENT_ID,
            call_id         = call_ids[20],
            ftp_status      = "amber",
            assessed_at     = dt(day(20), hour=10, minute=0),
            day_in_recovery = 20,
            module          = "orthopaedic-tka-42d",
            condition       = "Total Knee Arthroplasty",
            actual_scores   = {"pain": 2.8, "mobility": 5.1, "breathlessness": 0.5, "appetite": 1.8, "mood": 2.5},
            expected_scores = {"pain": 3.0, "mobility": 3.0, "breathlessness": 0.5, "appetite": 2.0, "mood": 2.5},
            variance_per_domain = {"pain": 0.2, "mobility": -2.1, "breathlessness": 0.0, "appetite": 0.2, "mood": 0.0},
            reasoning_text  = (
                "Mobility score 5.1/10 at Day 20 is 2.1 points above the NICE NG157 TKA expected "
                "benchmark of 3.0/10. ROM adequate at 105° but functional strength deficit identified — "
                "difficulty on stairs and rising from low chairs. Physio intensification recommended. "
                "All other domains within expected range."
            ),
        )
        db.add(ftp)

        # ── 6. Longitudinal Summary ───────────────────────────────────────
        summary = LongitudinalSummary(
            patient_id       = PATIENT_ID,
            version_number   = 1,
            is_current       = True,
            generated_at     = dt(day(20), hour=10, minute=15),
            narrative_text   = (
                "Michael Kenomore, 68M, is Day 20 post right Total Knee Arthroplasty (TKA). "
                "His recovery has been broadly satisfactory with the expected pain trajectory — "
                "pain has reduced from 8.2/10 at discharge to 2.8/10 today, consistent with the "
                "NICE NG157 pathway. A wound haematoma was identified at Day 5 (AMBER flag), "
                "confirmed by GP assessment at Day 7 as superficial haematoma with no infection — "
                "this resolved fully by Day 10. VTE prophylaxis (rivaroxaban 10mg OD) was completed "
                "on Day 9 as per NICE NG89 (14-day course for TKA). He is now attending outpatient "
                "physiotherapy commenced Day 18. The current clinical concern is mobility — his "
                "functional mobility score of 5.1/10 is lagging the expected Day 20 benchmark of "
                "≤3.0/10 per the NICE pathway. ROM is adequate at 105° but stair-climbing and "
                "rising from low chairs remain significantly limited. An AMBER flag for failure-to-"
                "progress has been raised. Physio intensification is planned. His mood, appetite, "
                "and breathlessness scores are all within normal limits. Monitoring continues under "
                "the 42-day NICE NG157 pathway, with a 6-week discharge review scheduled for 7 May 2026."
            ),
            active_concerns_snapshot = [
                "AMBER: Mobility lagging NICE Day 20 trajectory — functional deficit on stairs and transfers",
                "Outpatient physio commenced Day 18 — daily intensification recommended",
                "6-week orthopaedic review pending (7 May 2026)",
            ],
            trend_snapshot = {
                "pain":            {"day_1": 8.2, "day_7": 5.4, "day_14": 3.9, "day_20": 2.8, "trend": "improving"},
                "mobility":        {"day_1": 8.5, "day_7": 6.5, "day_14": 5.8, "day_20": 5.1, "trend": "slow_improving"},
                "breathlessness":  {"day_1": 1.5, "day_20": 0.5, "trend": "stable"},
                "mood":            {"day_1": 5.0, "day_20": 2.5, "trend": "improving"},
                "overall_rag":     "amber",
            },
        )
        db.add(summary)

        # ── 7. Remaining Schedule (Days 21–42, NICE NG157) ────────────────
        for (d_n, module, call_type) in FUTURE_CALLS:
            sched = CallSchedule(
                patient_id             = PATIENT_ID,
                scheduled_for          = dt(day(d_n), hour=9, minute=15),
                module                 = module,
                call_type              = call_type,
                day_in_recovery_target = d_n,
                protocol_name          = "NICE NG157 TKA 42-day",
                status                 = "pending",
            )
            db.add(sched)

        await db.commit()
        print(f"\n✓ Patient created: Michael Kenomore")
        print(f"  patient_id:    {PATIENT_ID}")
        print(f"  discharge:     {DISCHARGE}  (Day 0)")
        print(f"  monitoring to: {day(42)}  (Day 42 — NICE NG157 6-week endpoint)")
        print(f"\n  Call records:  {len([c for c in CALLS if c[1]=='completed'])} completed, {len([c for c in CALLS if c[1]=='missed'])} missed")
        print(f"  SOAP notes:    {len(SOAPS)}")
        print(f"  Urgency flags: 2 (1 resolved wound concern, 1 open mobility lag)")
        print(f"  FTP status:    amber")
        print(f"  Future calls:  {len(FUTURE_CALLS)} scheduled (Days 21–42)")
        print(f"\n  NICE basis:    NG157 (perioperative care) + NG89 (VTE — 14-day rivaroxaban)")
        print(f"  Monitoring:    42 days (6 weeks) — standard NHS TKA pathway\n")

    await engine.dispose()

asyncio.run(seed())

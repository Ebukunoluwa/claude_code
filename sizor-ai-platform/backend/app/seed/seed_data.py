"""
Seed script: creates demo hospital, ward, clinician, 3 patients with full clinical data.
Run: python -m app.seed.seed_data
"""
import asyncio
import uuid
from datetime import datetime, timezone, date, timedelta
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings
from ..models import (
    Hospital, Ward, Clinician, Patient, PatientMedicalProfile,
    CallRecord, ClinicalExtraction, SOAPNote, UrgencyFlag,
    FTPRecord, LongitudinalSummary, ClinicalDecision, ClinicianAction, CallSchedule,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TODAY = datetime.now(timezone.utc)
TODAY_DATE = TODAY.date()


def days_ago(n: int) -> datetime:
    return TODAY - timedelta(days=n)


def date_ago(n: int) -> date:
    return TODAY_DATE - timedelta(days=n)


async def seed():
    async with AsyncSessionLocal() as db:
        # ── Hospital & Ward ──────────────────────────────────────────────
        hospital_id = uuid.uuid4()
        hospital = Hospital(
            hospital_id=hospital_id,
            hospital_name="Royal Free Hospital",
            nhs_trust="Royal Free London NHS Foundation Trust",
            contact_email="admin@royalfree.nhs.uk",
            active_modules=["post_discharge", "chronic_disease"],
        )
        db.add(hospital)

        ward_id = uuid.uuid4()
        ward = Ward(
            ward_id=ward_id,
            hospital_id=hospital_id,
            ward_name="Cardiology Ward",
            specialty="Cardiology",
            escalation_contacts={"on_call": "bleep 2341", "consultant": "Dr. Sarah Okafor"},
        )
        db.add(ward)
        await db.flush()

        # ── Clinician ────────────────────────────────────────────────────
        clinician_id = uuid.uuid4()
        clinician = Clinician(
            clinician_id=clinician_id,
            hospital_id=hospital_id,
            ward_id=ward_id,
            full_name="Dr. Emily Chen",
            email="emily.chen@royalfree.nhs.uk",
            hashed_password=pwd_context.hash("password123"),
            role="doctor",
        )
        db.add(clinician)
        await db.flush()

        # ════════════════════════════════════════════════════════════════
        # PATIENT 1 — Heart Failure, Day 8 post-discharge, AMBER flag
        # ════════════════════════════════════════════════════════════════
        p1_id = uuid.uuid4()
        p1 = Patient(
            patient_id=p1_id,
            hospital_id=hospital_id,
            ward_id=ward_id,
            assigned_clinician_id=clinician_id,
            full_name="Margaret Thompson",
            nhs_number="4857392016",
            date_of_birth=date(1948, 3, 12),
            phone_number="+447700123001",
            condition="Heart Failure",
            procedure="Diuretic optimisation",
            admission_date=date_ago(15),
            discharge_date=date_ago(8),
            program_module="post_discharge",
            status="active",
        )
        db.add(p1)

        p1_profile = PatientMedicalProfile(
            patient_id=p1_id,
            primary_diagnosis="Chronic Heart Failure (HFrEF, EF 30%)",
            secondary_diagnoses=["Type 2 Diabetes Mellitus", "Chronic Kidney Disease Stage 3"],
            current_medications=[
                "Furosemide 80mg OD", "Bisoprolol 5mg OD", "Ramipril 5mg OD",
                "Spironolactone 25mg OD", "Empagliflozin 10mg OD", "Metformin 500mg BD",
            ],
            allergies=["Penicillin (rash)"],
            relevant_comorbidities=["Atrial Fibrillation", "Hypertension"],
            discharge_summary_text=(
                "Mrs Thompson admitted with decompensated heart failure. "
                "BNP on admission 2840 pg/mL. Optimised diuresis with IV furosemide, "
                "transitioned to oral. Discharged euvolaemic. EF 30% on echo. "
                "Follow-up cardiology clinic booked at 6 weeks. "
                "Advised daily weights, fluid restriction 1.5L/day."
            ),
            consultant_notes="High-risk patient. BNP still elevated at discharge (880 pg/mL). Close monitoring required.",
        )
        db.add(p1_profile)
        await db.flush()

        # Call 1 for patient 1 — Day 3
        c1a_id = uuid.uuid4()
        c1a = CallRecord(
            call_id=c1a_id,
            patient_id=p1_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=3,
            status="completed",
            duration_seconds=342,
            started_at=days_ago(5),
            transcript_raw=(
                "Agent: Hello, is this Margaret? Patient: Yes, speaking. "
                "Agent: This is your post-discharge check-in call from Royal Free. How are you feeling today? "
                "Patient: I'm managing. My ankles are a bit swollen still but not as bad as before. "
                "Agent: On a scale of 0 to 10, how would you rate any breathlessness? "
                "Patient: About a 4. I get short of breath walking to the bathroom. "
                "Agent: And pain? Patient: No real pain, maybe a 2, just general tiredness. "
                "Agent: How about your mood on a scale of 0 to 10? "
                "Patient: Probably a 6, I'm worried about ending up back in hospital. "
                "Agent: Are you taking all your medications as prescribed? "
                "Patient: Yes, I've been very careful about that. "
                "Agent: Have you been doing your daily weights? "
                "Patient: Yes, I went up 1.5kg yesterday, should I be worried? "
                "Agent: It's important you let your GP or the ward know about that weight gain. "
                "Patient: Okay, I will. Thank you."
            ),
        )
        db.add(c1a)
        await db.flush()

        ext1a = ClinicalExtraction(
            call_id=c1a_id,
            patient_id=p1_id,
            pain_score=2,
            breathlessness_score=4,
            mobility_score=5,
            appetite_score=6,
            mood_score=6,
            medication_adherence=True,
            condition_specific_flags={"weight_gain_kg": 1.5, "ankle_oedema": True, "fluid_restriction_adherent": True},
        )
        db.add(ext1a)

        soap1a = SOAPNote(
            call_id=c1a_id,
            patient_id=p1_id,
            subjective="Patient reports persistent ankle swelling, breathlessness 4/10 on exertion (walking to bathroom). No significant pain (2/10). Anxious about rehospitalisation. 1.5kg weight gain overnight. Medication adherent.",
            objective="Day 3 post-discharge HF. BNP 880 at discharge. Daily weights ongoing. Medication list confirmed.",
            assessment="Mild decompensation risk: 1.5kg overnight weight gain with residual oedema and breathlessness suggests early fluid retention. Mood affected by illness anxiety.",
            plan="Alert clinical team re weight gain. Reinforce fluid restriction. Monitor daily weights. Consider GP contact if further gain >1kg.",
            clinician_reviewed=True,
            model_used="gpt-4o",
            generated_at=days_ago(5),
        )
        db.add(soap1a)

        ftp1a = FTPRecord(
            call_id=c1a_id,
            patient_id=p1_id,
            actual_scores={"pain": 2, "breathlessness": 4, "mobility": 5, "mood": 6},
            expected_scores={"pain": 2.5, "breathlessness": 4.5, "mobility": 5.0, "mood": 6.5},
            variance_per_domain={"pain": -0.5, "breathlessness": -0.5, "mobility": 0, "mood": -0.5},
            condition="Heart Failure",
            module="post_discharge",
            day_in_recovery=3,
            ftp_status="on_track",
            reasoning_text="Patient is largely on track for day 3 HF recovery. Slight underperformance on breathlessness expected given residual fluid. Weight gain requires monitoring.",
            assessed_at=days_ago(5),
        )
        db.add(ftp1a)

        # Call 2 for patient 1 — Day 6
        c1b_id = uuid.uuid4()
        c1b = CallRecord(
            call_id=c1b_id,
            patient_id=p1_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=6,
            status="completed",
            duration_seconds=418,
            started_at=days_ago(2),
            transcript_raw=(
                "Agent: Hello Margaret, this is your day 6 check-in. How are you today? "
                "Patient: Not great to be honest. My breathing is worse. "
                "Agent: Can you rate your breathlessness for me, 0 being none, 10 being the worst? "
                "Patient: It's a 7 today. I couldn't sleep last night, had to prop myself up on three pillows. "
                "Agent: That sounds uncomfortable. Any swelling in your legs or ankles? "
                "Patient: Yes, much worse. My shoes don't fit. "
                "Agent: How much has your weight changed? "
                "Patient: I've gone up another 2kg in the last two days. "
                "Agent: I'm concerned about what you're describing. This could mean fluid is building up again. "
                "I'd strongly advise you contact your GP today or call 111 if you feel worse. "
                "Patient: Should I go to A&E? "
                "Agent: Given your breathing is significantly worse and rapid weight gain, yes — if you cannot reach your GP today, please go to A&E or call 999 if it becomes severe. "
                "Patient: Alright. My daughter is here, she can take me."
            ),
        )
        db.add(c1b)
        await db.flush()

        ext1b = ClinicalExtraction(
            call_id=c1b_id,
            patient_id=p1_id,
            pain_score=2,
            breathlessness_score=7,
            mobility_score=3,
            appetite_score=4,
            mood_score=3,
            medication_adherence=True,
            condition_specific_flags={"weight_gain_kg": 2.0, "orthopnoea": True, "ankle_oedema": "severe", "pillow_count": 3},
        )
        db.add(ext1b)

        soap1b = SOAPNote(
            call_id=c1b_id,
            patient_id=p1_id,
            subjective="Significant deterioration. Breathlessness 7/10, orthopnoea requiring 3 pillows, unable to sleep supine. 2kg weight gain over 2 days. Severe ankle oedema — shoes not fitting. Medication adherent.",
            objective="Day 6 HF. Total 3.5kg weight gain since discharge. Orthopnoea present.",
            assessment="Clinical decompensation: acute fluid overload with orthopnoea and rapid weight gain. High risk of rehospitalisation. AMBER-RED alert.",
            plan="Urgent GP contact advised. A&E if unable to reach GP. Family present to assist. Flag for urgent clinician review.",
            clinician_reviewed=False,
            model_used="gpt-4o",
            generated_at=days_ago(2),
        )
        db.add(soap1b)

        flag1 = UrgencyFlag(
            patient_id=p1_id,
            call_id=c1b_id,
            severity="amber",
            flag_type="clinical_deterioration",
            trigger_description="3.5kg weight gain since discharge with worsening orthopnoea and breathlessness 7/10 on day 6 post HF discharge.",
            status="open",
            raised_at=days_ago(2),
        )
        db.add(flag1)

        ftp1b = FTPRecord(
            call_id=c1b_id,
            patient_id=p1_id,
            actual_scores={"pain": 2, "breathlessness": 7, "mobility": 3, "mood": 3},
            expected_scores={"pain": 2.0, "breathlessness": 3.5, "mobility": 6.0, "mood": 7.0},
            variance_per_domain={"pain": 0, "breathlessness": 3.5, "mobility": -3.0, "mood": -4.0},
            condition="Heart Failure",
            module="post_discharge",
            day_in_recovery=6,
            ftp_status="failing",
            reasoning_text="Significant failure to progress. Breathlessness 3.5 points above expected; mobility 3 points below expected. Rapid fluid gain strongly suggestive of decompensation.",
            assessed_at=days_ago(2),
        )
        db.add(ftp1b)

        summary1 = LongitudinalSummary(
            patient_id=p1_id,
            narrative_text=(
                "Mrs Thompson, 77, admitted for decompensated heart failure (EF 30%), discharged day 8 ago. "
                "Initial recovery was cautiously on track (day 3: breathlessness 4/10, weight +1.5kg). "
                "Day 6 marked a significant deterioration: breathlessness escalated to 7/10, orthopnoea with 3 pillows, "
                "total 3.5kg weight gain. FTP assessment shows failing trajectory across breathlessness and mobility. "
                "AMBER urgency flag raised. Patient was advised to seek urgent GP review or A&E. Family support present. "
                "Clinician review of latest SOAP note pending."
            ),
            active_concerns_snapshot=["Acute fluid overload", "Orthopnoea", "Rapid weight gain 3.5kg", "Decompensation risk"],
            trend_snapshot={"breathlessness": "worsening", "mobility": "declining", "mood": "low"},
            version_number=2,
            is_current=True,
            generated_at=days_ago(2),
        )
        db.add(summary1)

        # ════════════════════════════════════════════════════════════════
        # PATIENT 2 — COPD, Day 14 post-discharge, GREEN, progressing well
        # ════════════════════════════════════════════════════════════════
        p2_id = uuid.uuid4()
        p2 = Patient(
            patient_id=p2_id,
            hospital_id=hospital_id,
            ward_id=ward_id,
            assigned_clinician_id=clinician_id,
            full_name="Robert Davies",
            nhs_number="7291048536",
            date_of_birth=date(1952, 8, 27),
            phone_number="+447700123002",
            condition="COPD",
            procedure="COPD exacerbation management",
            admission_date=date_ago(21),
            discharge_date=date_ago(14),
            program_module="post_discharge",
            status="active",
        )
        db.add(p2)

        p2_profile = PatientMedicalProfile(
            patient_id=p2_id,
            primary_diagnosis="COPD (GOLD Stage III, FEV1 42%)",
            secondary_diagnoses=["Hypertension", "Osteoporosis"],
            current_medications=[
                "Tiotropium 18mcg OD", "Salmeterol/Fluticasone 50/250 BD",
                "Salbutamol 100mcg PRN", "Prednisolone 5mg OD (weaning)",
                "Amlodipine 5mg OD",
            ],
            allergies=[],
            relevant_comorbidities=["Ex-smoker (40 pack years)", "Cor pulmonale"],
            discharge_summary_text=(
                "Mr Davies admitted with infective COPD exacerbation. Treated with IV antibiotics "
                "(co-amoxiclav), nebulised bronchodilators, systemic steroids. Good response. "
                "Discharged on weaning prednisolone. Pulmonary rehab referral made. Smoking cessation counselling provided."
            ),
            consultant_notes="Moderate-severe COPD. Encourage adherence to inhaler technique. Pulmonary rehab attendance critical.",
        )
        db.add(p2_profile)
        await db.flush()

        # Call 1 — Day 7
        c2a_id = uuid.uuid4()
        c2a = CallRecord(
            call_id=c2a_id,
            patient_id=p2_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=7,
            status="completed",
            duration_seconds=298,
            started_at=days_ago(7),
            transcript_raw=(
                "Agent: Good morning Mr Davies, this is your week 1 check-in from Royal Free. "
                "Patient: Morning, yes go ahead. "
                "Agent: How's your breathing been this week? "
                "Patient: Much better than when I came in. Still not great but I can get around the house. "
                "Agent: On a scale of 0 to 10, how would you rate your breathlessness? "
                "Patient: About a 5. "
                "Agent: Are you using your inhalers as prescribed? "
                "Patient: Yes, the blue one when I need it, maybe twice a day. "
                "Agent: Have you started the prednisolone wean? "
                "Patient: Yes, down to 25mg now. "
                "Agent: Any increased sputum or change in colour? "
                "Patient: A bit of white sputum, nothing yellow or green. "
                "Agent: That's reassuring. How's your mood and energy? "
                "Patient: Energy is low, maybe 4 out of 10. Mood is okay, about 6. "
                "Agent: Have you heard about your pulmonary rehab referral? "
                "Patient: Got a letter, starts in two weeks. Looking forward to it."
            ),
        )
        db.add(c2a)
        await db.flush()

        ext2a = ClinicalExtraction(
            call_id=c2a_id,
            patient_id=p2_id,
            pain_score=1,
            breathlessness_score=5,
            mobility_score=5,
            appetite_score=6,
            mood_score=6,
            medication_adherence=True,
            condition_specific_flags={"sputum_colour": "white", "rescue_inhaler_use_per_day": 2, "prednisolone_dose_mg": 25},
        )
        db.add(ext2a)

        soap2a = SOAPNote(
            call_id=c2a_id,
            patient_id=p2_id,
            subjective="Day 7 COPD post-exacerbation. Breathlessness 5/10, improved from admission. Mobilising around the house. White sputum only. Salbutamol PRN ~2x/day. Prednisolone weaning as planned. Mood 6/10. Low energy.",
            objective="COPD GOLD III. FEV1 42%. Day 7 post-discharge. Steroid wean on track.",
            assessment="On-track recovery for COPD post-exacerbation. Breathlessness improving, no signs of re-exacerbation. Pulmonary rehab engagement positive.",
            plan="Continue inhaler regimen. Complete steroid wean. Attend pulmonary rehab. Monitor sputum. Routine day 14 call scheduled.",
            clinician_reviewed=True,
            model_used="gpt-4o",
            generated_at=days_ago(7),
        )
        db.add(soap2a)

        # Call 2 — Day 14
        c2b_id = uuid.uuid4()
        c2b = CallRecord(
            call_id=c2b_id,
            patient_id=p2_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=14,
            status="completed",
            duration_seconds=376,
            started_at=days_ago(0),
            transcript_raw=(
                "Agent: Hello Mr Davies, this is your 2-week check-in. "
                "Patient: Hello, yes. I'm actually feeling much better this week. "
                "Agent: Wonderful. How would you rate breathlessness today? "
                "Patient: About a 3. I walked to the corner shop yesterday without stopping! "
                "Agent: That's great progress. Have you started pulmonary rehab? "
                "Patient: Yes, had my first session Monday. Hard work but I enjoyed it. "
                "Agent: Excellent. Any sputum changes? "
                "Patient: No, clear now. "
                "Agent: Have you finished your prednisolone course? "
                "Patient: Yes, last tablet was yesterday. "
                "Agent: How are you feeling emotionally? "
                "Patient: Much better, more positive. About 8 out of 10. "
                "Agent: And pain? "
                "Patient: Barely any, maybe 1. "
                "Agent: This all sounds like very positive progress Robert. Keep it up."
            ),
        )
        db.add(c2b)
        await db.flush()

        ext2b = ClinicalExtraction(
            call_id=c2b_id,
            patient_id=p2_id,
            pain_score=1,
            breathlessness_score=3,
            mobility_score=7,
            appetite_score=7,
            mood_score=8,
            medication_adherence=True,
            condition_specific_flags={"sputum_colour": "clear", "rescue_inhaler_use_per_day": 1, "prednisolone_completed": True, "pulmonary_rehab_started": True},
        )
        db.add(ext2b)

        soap2b = SOAPNote(
            call_id=c2b_id,
            patient_id=p2_id,
            subjective="Day 14 COPD. Significant improvement: breathlessness 3/10 (was 5/10). Walking to corner shop without stopping. Pulmonary rehab started. Prednisolone course completed. Clear sputum. Mood 8/10.",
            objective="COPD GOLD III. Day 14. Steroid course complete. Rehab commenced.",
            assessment="Strong recovery trajectory. Breathlessness, mobility and mood all significantly improved. No signs of re-exacerbation. Excellent engagement with rehabilitation.",
            plan="Continue maintenance inhalers. Attend remaining pulmonary rehab sessions. Follow-up spirometry at 6 weeks. Discharge from active monitoring programme if no deterioration at day 21.",
            clinician_reviewed=False,
            model_used="gpt-4o",
            generated_at=TODAY,
        )
        db.add(soap2b)

        ftp2b = FTPRecord(
            call_id=c2b_id,
            patient_id=p2_id,
            actual_scores={"pain": 1, "breathlessness": 3, "mobility": 7, "mood": 8},
            expected_scores={"pain": 1.5, "breathlessness": 3.5, "mobility": 6.5, "mood": 7.5},
            variance_per_domain={"pain": -0.5, "breathlessness": -0.5, "mobility": 0.5, "mood": 0.5},
            condition="COPD",
            module="post_discharge",
            day_in_recovery=14,
            ftp_status="on_track",
            reasoning_text="All domains at or above expected NICE trajectory for day 14 COPD recovery. Pulmonary rehab engagement is a strong positive indicator.",
            assessed_at=TODAY,
        )
        db.add(ftp2b)

        summary2 = LongitudinalSummary(
            patient_id=p2_id,
            narrative_text=(
                "Mr Davies, 73, COPD GOLD III, discharged 14 days ago following infective exacerbation. "
                "Week 1 showed steady improvement with breathlessness 5/10 and early mobility. "
                "Week 2 shows excellent progress: breathlessness reduced to 3/10, walking independently, "
                "pulmonary rehab commenced, prednisolone course completed. Mood significantly improved (8/10). "
                "FTP assessment on-track across all domains. No urgency flags raised. "
                "Current trajectory is positive — consider step-down at day 21 if maintained."
            ),
            active_concerns_snapshot=[],
            trend_snapshot={"breathlessness": "improving", "mobility": "improving", "mood": "improving"},
            version_number=2,
            is_current=True,
            generated_at=TODAY,
        )
        db.add(summary2)

        # ════════════════════════════════════════════════════════════════
        # PATIENT 3 — Hip Replacement, Day 21, RED flag (fall risk)
        # ════════════════════════════════════════════════════════════════
        p3_id = uuid.uuid4()
        p3 = Patient(
            patient_id=p3_id,
            hospital_id=hospital_id,
            ward_id=ward_id,
            assigned_clinician_id=clinician_id,
            full_name="Doris Patel",
            nhs_number="3619274850",
            date_of_birth=date(1940, 11, 5),
            phone_number="+447700123003",
            condition="Hip Replacement",
            procedure="Right total hip replacement",
            admission_date=date_ago(28),
            discharge_date=date_ago(21),
            program_module="post_discharge",
            status="active",
        )
        db.add(p3)

        p3_profile = PatientMedicalProfile(
            patient_id=p3_id,
            primary_diagnosis="Right total hip replacement (osteoarthritis)",
            secondary_diagnoses=["Osteoporosis", "Mild cognitive impairment"],
            current_medications=[
                "Rivaroxaban 10mg OD (DVT prophylaxis, 35-day course)",
                "Paracetamol 1g QDS",
                "Codeine 30mg QDS PRN",
                "Alendronate 70mg weekly",
                "Omeprazole 20mg OD",
            ],
            allergies=["Aspirin (bronchospasm)", "NSAIDs"],
            relevant_comorbidities=["Previous fractured neck of femur (left, 2019)", "Mild cognitive impairment"],
            discharge_summary_text=(
                "Mrs Patel underwent right THR under spinal anaesthesia. "
                "Uncomplicated procedure. Mobilising with zimmer frame by day 2. "
                "Discharged to daughter's home. Physiotherapy twice weekly arranged. "
                "Hip precautions explained to patient and family. DVT prophylaxis with rivaroxaban for 35 days."
            ),
            consultant_notes="Frail elderly patient. Fall risk high. Ensure physio compliance. Watch for delirium post-discharge.",
        )
        db.add(p3_profile)
        await db.flush()

        # Call 1 — Day 7
        c3a_id = uuid.uuid4()
        c3a = CallRecord(
            call_id=c3a_id,
            patient_id=p3_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=7,
            status="completed",
            duration_seconds=445,
            started_at=days_ago(14),
            transcript_raw=(
                "Agent: Hello, may I speak with Doris? "
                "Patient's daughter: She's here, I'll pass her over. "
                "Patient: Hello? "
                "Agent: Hello Doris, this is a check-in call from the hospital. How are you getting on? "
                "Patient: Quite painful. The hip hurts a lot. "
                "Agent: On a scale of 0 to 10, how bad is the pain? "
                "Patient: About a 7 or 8. "
                "Agent: Are you taking your painkillers regularly? "
                "Patient: I forget sometimes. My daughter reminds me. "
                "Agent: It's important to take them regularly. Are you managing to do your exercises? "
                "Patient: A little. The physiotherapist came yesterday. "
                "Agent: Good. Are you walking with your frame? "
                "Patient: Yes, I need it to get to the toilet. About a 4 for walking. "
                "Agent: Any swelling in your leg or calf pain? "
                "Patient: My leg is a bit swollen but they said that was normal. "
                "Agent: How are you sleeping and feeling in yourself? "
                "Patient: I get confused sometimes at night. A bit anxious."
            ),
        )
        db.add(c3a)
        await db.flush()

        ext3a = ClinicalExtraction(
            call_id=c3a_id,
            patient_id=p3_id,
            pain_score=7,
            breathlessness_score=2,
            mobility_score=4,
            appetite_score=5,
            mood_score=4,
            medication_adherence=False,
            condition_specific_flags={"leg_swelling": True, "night_confusion": True, "using_zimmer": True, "hip_precautions_compliant": True},
        )
        db.add(ext3a)

        soap3a = SOAPNote(
            call_id=c3a_id,
            patient_id=p3_id,
            subjective="Day 7 THR. Significant pain 7-8/10. Inconsistent analgesia use (daughter prompting required). Limited mobility with zimmer frame (4/10). Night-time confusion reported. Leg swelling. Mood anxious (4/10). Physio attended.",
            objective="Frail 84F. Right THR day 7. On rivaroxaban. Prior fracture neck of femur. Mild cognitive impairment.",
            assessment="Suboptimal pain control is limiting rehabilitation. Night confusion concerning in context of MCI — possible post-operative delirium. Leg swelling noted; DVT risk requires monitoring.",
            plan="Reinforce analgesia schedule. Alert physio re pain limiting mobility. Monitor confusion — contact GP if worsening. Leg swelling: ensure rivaroxaban compliance, watch for DVT symptoms.",
            clinician_reviewed=True,
            model_used="gpt-4o",
            generated_at=days_ago(14),
        )
        db.add(soap3a)

        # Call 2 — Day 14
        c3b_id = uuid.uuid4()
        c3b = CallRecord(
            call_id=c3b_id,
            patient_id=p3_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=14,
            status="completed",
            duration_seconds=512,
            started_at=days_ago(7),
            transcript_raw=(
                "Agent: Hello Doris, this is your 2-week check-in. "
                "Patient: Hello yes. "
                "Agent: How has the pain been this week? "
                "Patient: Better than last week. Maybe a 5 now. "
                "Agent: Are you remembering your painkillers? "
                "Patient: Better yes, my daughter puts them out for me. "
                "Agent: Good. How about walking? "
                "Patient: I can go to the kitchen now with the frame. Maybe 5 out of 10. "
                "Agent: Have you had any falls? "
                "Patient: I did trip on the rug on Wednesday but caught myself. "
                "Agent: I'm glad you're okay. We'd recommend removing any loose rugs to reduce fall risk. "
                "Patient: My daughter has already taken it away. "
                "Agent: Good. Any calf pain or new swelling? "
                "Patient: No, the swelling in my leg has gone down. "
                "Agent: The confusion at night — has that improved? "
                "Patient: Yes, less confused this week."
            ),
        )
        db.add(c3b)
        await db.flush()

        ext3b = ClinicalExtraction(
            call_id=c3b_id,
            patient_id=p3_id,
            pain_score=5,
            breathlessness_score=1,
            mobility_score=5,
            appetite_score=6,
            mood_score=5,
            medication_adherence=True,
            condition_specific_flags={"near_fall": True, "rug_removed": True, "leg_swelling_resolved": True, "night_confusion": False},
        )
        db.add(ext3b)

        soap3b = SOAPNote(
            call_id=c3b_id,
            patient_id=p3_id,
            subjective="Day 14 THR. Improved pain 5/10. Medication adherence improved with daughter's supervision. Mobility improved to kitchen with zimmer. Near-fall on rug (rug now removed). Leg swelling resolved. Night confusion resolving.",
            objective="Day 14 post-THR. Fall risk: near-fall this week.",
            assessment="Gradual improvement overall. Near-fall is a significant concern given frailty and previous fractured NOF. Mobility still limited but progressing. Pain improving.",
            plan="Ongoing physiotherapy. Fall risk assessment by physio. Ensure home hazard removal complete. Continue rivaroxaban until day 35. Monitor for DVT.",
            clinician_reviewed=True,
            model_used="gpt-4o",
            generated_at=days_ago(7),
        )
        db.add(soap3b)

        # Call 3 — Day 21
        c3c_id = uuid.uuid4()
        c3c = CallRecord(
            call_id=c3c_id,
            patient_id=p3_id,
            direction="outbound",
            trigger_type="scheduled",
            day_in_recovery=21,
            status="completed",
            duration_seconds=389,
            started_at=days_ago(0),
            transcript_raw=(
                "Agent: Good morning Doris, this is your 3-week check-in. "
                "Patient: Hello. I had a fall yesterday. "
                "Agent: Oh no, I'm sorry to hear that. Are you hurt? "
                "Patient: I landed on my side. My hip is very sore. I didn't fall on the operated hip but it still hurts. "
                "Agent: Did you go to the hospital or see a doctor after the fall? "
                "Patient: No, my daughter said to wait and see. "
                "Agent: Given your recent hip surgery, it's very important you get assessed after any fall. "
                "I'd strongly recommend you call 111 or go to A&E today to make sure nothing is damaged. "
                "Patient: Even if I can still walk? "
                "Agent: Yes, even so. Especially with the type of surgery you've had. "
                "Can you rate your pain right now? "
                "Patient: About an 8 where I landed. "
                "Agent: And is there any new calf pain or swelling? "
                "Patient: A little in the right calf, I thought it was just bruising. "
                "Agent: That combination — a fall and calf pain — does require urgent assessment today. "
                "Is your daughter there? Patient: Yes. "
                "Agent: Please let her know you need to be seen today. This is important."
            ),
        )
        db.add(c3c)
        await db.flush()

        ext3c = ClinicalExtraction(
            call_id=c3c_id,
            patient_id=p3_id,
            pain_score=8,
            breathlessness_score=2,
            mobility_score=3,
            appetite_score=4,
            mood_score=3,
            medication_adherence=True,
            condition_specific_flags={"fall_yesterday": True, "calf_pain": True, "calf_swelling": True, "dvt_risk": "high", "post_fall_assessed": False},
        )
        db.add(ext3c)

        soap3c = SOAPNote(
            call_id=c3c_id,
            patient_id=p3_id,
            subjective="Day 21 THR. FALL yesterday — landed on side, not operated hip. Pain 8/10 at landing site. New right calf pain and swelling. Not yet assessed post-fall. Mobility severely reduced (3/10). Mood low (3/10).",
            objective="Day 21 post right THR. Rivaroxaban day 21/35. Fall with new calf pain and swelling. High DVT suspicion.",
            assessment="RED FLAG: Fall post-THR with new calf pain/swelling raises significant DVT suspicion. Urgent same-day assessment required. Prosthesis integrity also requires evaluation. High-risk frail patient.",
            plan="URGENT: Same-day A&E attendance advised. DVT assessment (Wells score, D-dimer/Doppler USS). Hip X-ray if weight-bearing pain. Alert on-call orthopaedics.",
            clinician_reviewed=False,
            model_used="gpt-4o",
            generated_at=TODAY,
        )
        db.add(soap3c)

        flag3 = UrgencyFlag(
            patient_id=p3_id,
            call_id=c3c_id,
            severity="red",
            flag_type="dvt_risk",
            trigger_description="Day 21 post-THR fall with new right calf pain and swelling. DVT high suspicion. Patient not yet assessed. Urgent same-day A&E attendance required.",
            status="open",
            raised_at=TODAY,
        )
        db.add(flag3)

        ftp3c = FTPRecord(
            call_id=c3c_id,
            patient_id=p3_id,
            actual_scores={"pain": 8, "breathlessness": 2, "mobility": 3, "mood": 3},
            expected_scores={"pain": 3.0, "breathlessness": 1.5, "mobility": 7.0, "mood": 7.0},
            variance_per_domain={"pain": 5.0, "breathlessness": 0.5, "mobility": -4.0, "mood": -4.0},
            condition="Hip Replacement",
            module="post_discharge",
            day_in_recovery=21,
            ftp_status="failing",
            reasoning_text="Acute deterioration at day 21 secondary to fall. Pain 5 points above expected. Mobility 4 below expected. Fall + DVT risk represents acute clinical emergency superseding standard FTP assessment.",
            assessed_at=TODAY,
        )
        db.add(ftp3c)

        summary3 = LongitudinalSummary(
            patient_id=p3_id,
            narrative_text=(
                "Mrs Patel, 84, underwent right total hip replacement 21 days ago. "
                "Week 1: significant pain (7-8/10), medication non-adherence, night confusion (possible delirium), limited mobility. "
                "Week 2: gradual improvement, pain reduced to 5/10, near-fall on rug (removed), night confusion resolving. "
                "Week 3 (today): ACUTE DETERIORATION — fall with right calf pain and swelling, pain 8/10, mobility severely limited. "
                "HIGH suspicion of DVT. RED urgency flag raised. Urgent same-day A&E assessment advised but not yet completed. "
                "Family (daughter) present and aware. Clinician URGENT review required."
            ),
            active_concerns_snapshot=["FALL — post-THR", "Right calf pain + swelling — DVT suspicion", "Pain 8/10", "Not yet medically assessed"],
            trend_snapshot={"pain": "acute_deterioration", "mobility": "acute_deterioration", "mood": "low"},
            version_number=3,
            is_current=True,
            generated_at=TODAY,
        )
        db.add(summary3)

        # Clinical decision for patient 3
        decision3 = ClinicalDecision(
            patient_id=p3_id,
            call_id=c3c_id,
            clinician_id=clinician_id,
            clinical_question="Fall post-THR with calf pain and swelling on day 21. DVT? Prosthesis integrity?",
            patient_context_snapshot={"condition": "Hip Replacement", "day": 21},
            differential_diagnoses=[
                "Deep vein thrombosis (primary concern)",
                "Soft tissue injury from fall",
                "Periprosthetic fracture",
                "Haematoma",
            ],
            recommended_actions=[
                "Same-day emergency department attendance",
                "Wells DVT score assessment",
                "D-dimer if Wells score intermediate",
                "Doppler USS lower limb if clinical suspicion high",
                "Hip X-ray to exclude periprosthetic fracture",
                "Orthopaedic review if X-ray abnormal",
                "Continue rivaroxaban — do not stop pending assessment",
            ],
            risk_assessment=(
                "HIGH RISK. DVT probability elevated: day 21 post major lower limb surgery, calf pain, "
                "swelling, fall. Pre-test probability HIGH by Wells criteria. Risk of fatal PE if DVT confirmed "
                "and untreated. Periprosthetic fracture risk present. This presentation requires same-day "
                "emergency assessment. Delay is clinically dangerous."
            ),
            uncertainty_flags=["Calf swelling may be post-fall haematoma vs DVT — imaging required to differentiate"],
            nice_references=[
                "NICE CG144: Venous thromboembolic diseases",
                "NICE NG157: Hip fracture management",
                "NICE QS29: Hip replacement quality standard",
            ],
            full_reasoning_text=(
                "Patient is day 21 post right THR — a high DVT risk period. She has fallen and reports new "
                "right calf pain with swelling. By Wells DVT criteria: active cancer (no, 0), paralysis (no, 0), "
                "bedridden >3 days (partial, +1), local tenderness (+1), entire leg swollen (partial), "
                "calf swelling >3cm (unknown), pitting oedema (unknown), collateral veins (unknown), "
                "prior DVT (no), alternative diagnosis less likely (+1). Estimated score 2-3 = HIGH probability. "
                "Rivaroxaban was prescribed for prophylaxis but therapeutic DVT treatment requires dose escalation "
                "(15mg BD for 21 days then 20mg OD). Periprosthetic fracture must also be excluded given fall. "
                "This is a time-critical emergency requiring same-day assessment."
            ),
            actioned=False,
        )
        db.add(decision3)

        # ── Upcoming schedules ────────────────────────────────────────────
        for pid, day_offset, module in [
            (p1_id, 1, "post_discharge"),
            (p2_id, 7, "post_discharge"),
            (p3_id, 0, "post_discharge"),
        ]:
            sched = CallSchedule(
                patient_id=pid,
                scheduled_for=TODAY + timedelta(days=day_offset),
                module=module,
                call_type="routine",
                protocol_name="standard_checkin",
            )
            db.add(sched)

        await db.commit()
        print("✓ Seed data written successfully.")
        print(f"  Hospital: Royal Free Hospital ({hospital_id})")
        print(f"  Clinician: Dr. Emily Chen — email: emily.chen@royalfree.nhs.uk — password: password123")
        print(f"  Patient 1: Margaret Thompson (Heart Failure) — AMBER flag")
        print(f"  Patient 2: Robert Davies (COPD) — progressing well")
        print(f"  Patient 3: Doris Patel (Hip Replacement) — RED flag, urgent")


if __name__ == "__main__":
    asyncio.run(seed())

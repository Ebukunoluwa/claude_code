"""
Quick script to add a patient to Sizor.
Run: python add_patient.py
Edit the PATIENT dict below before running.
"""
import asyncio
from datetime import date
from sqlalchemy import select, text
from app.database import engine, AsyncSessionLocal
from app.models import Hospital, Patient, PatientMedicalProfile

PATIENT = {
    "nhs_number": "165701",
    "full_name": "James",           # change to full name
    "phone_number": "+447888629971",  # change to patient's number
    "date_of_birth": date(1995, 9, 18),  # change DOB
    "condition": "Post-Surgical Recovery",
    "procedure": "General procedure",
    "discharge_date": date.today(),
    "program_module": "post_discharge",
    "status": "active",
}

async def main():
    async with AsyncSessionLocal() as db:
        # Get the first hospital
        result = await db.execute(select(Hospital).limit(1))
        hospital = result.scalar_one_or_none()
        if not hospital:
            print("ERROR: No hospital found. Run seed_data.py first.")
            return

        # Check patient doesn't already exist
        existing = await db.execute(
            select(Patient).where(Patient.nhs_number == PATIENT["nhs_number"])
        )
        if existing.scalar_one_or_none():
            print(f"Patient with NHS {PATIENT['nhs_number']} already exists.")
            return

        patient = Patient(
            hospital_id=hospital.hospital_id,
            **PATIENT,
        )
        db.add(patient)
        await db.flush()

        profile = PatientMedicalProfile(
            patient_id=patient.patient_id,
            primary_diagnosis=PATIENT["condition"],
        )
        db.add(profile)
        await db.commit()

        print(f"✓ Patient created: {PATIENT['full_name']} (NHS: {PATIENT['nhs_number']})")
        print(f"  patient_id: {patient.patient_id}")

asyncio.run(main())

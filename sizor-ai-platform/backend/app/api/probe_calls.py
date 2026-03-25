"""
Probe Call API

Flow:
  POST /probe-calls
    → saves ProbeCall record
    → generates call_prompt via Groq Llama 4 (fallback: GPT-4o, then raw note)
    → enqueues fire_probe_call Celery task at scheduled_time

  GET /patients/{patient_id}/probe-calls
    → returns all probe calls for patient, newest first

  GET /probe-calls/{probe_call_id}
    → returns single probe call; resolves soap_note if available

  GET /probe-calls/{probe_call_id}/twiml
    → returns TwiML served to Twilio when the outbound call connects

  POST /probe-calls/status-callback
    → Twilio webhook; updates probe_call.status on call state changes
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import litellm

from ..database import get_db
from ..models import Patient, ProbeCall, SOAPNote, CallRecord, Clinician, Hospital
from .auth import get_current_clinician
from ..config import settings

router = APIRouter(tags=["probe-calls"])

TEST_PHONE_NUMBER = "+447888629971"


# ─── Prompt generation ───────────────────────────────────────────────────────

async def _extract_questions(note: str, patient_name: str, condition: str) -> list[str]:
    """
    Use LLM to turn the clinician's free-text note into 2-4 specific,
    conversational questions to ask the patient — one at a time.
    Returns a list of question strings, or a fallback list on failure.
    """
    system = (
        "You are a clinical AI assistant. A clinician has written a note about a patient concern. "
        "Convert this into 2 to 4 specific, plain-English questions to ask the patient over the phone. "
        "Rules:\n"
        "- Each question should be short, warm, and conversational — not clinical or robotic.\n"
        "- One topic per question. Never bundle two questions into one.\n"
        "- Avoid medical jargon. Speak like a kind, caring nurse.\n"
        "- Output ONLY a JSON array of question strings, e.g. [\"How has your pain been lately?\", \"...\"]\n"
        "- No commentary, no markdown, just the JSON array."
    )
    user = (
        f"Patient: {patient_name}\n"
        f"Condition: {condition}\n"
        f"Clinician's note: {note}\n\n"
        "Generate the questions array."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    for model, key_attr, env_var in [
        ("groq/meta-llama/llama-4-scout-17b-16e-instruct", "groq_api_key", "GROQ_API_KEY"),
        ("gpt-4o", "openai_api_key", "OPENAI_API_KEY"),
    ]:
        api_key = getattr(settings, key_attr, "")
        if not api_key:
            continue
        os.environ[env_var] = api_key
        try:
            resp = await litellm.acompletion(
                model=model, messages=messages, temperature=0.3, max_tokens=300,
            )
            import json as _json
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            questions = _json.loads(raw)
            if isinstance(questions, list) and questions:
                return [str(q) for q in questions]
        except Exception:
            continue

    # Fallback: derive a simple question from the raw note
    return [f"How have you been feeling with regards to {note.lower().rstrip('.')}?"]


def _build_probe_script(
    patient_name: str,
    condition: str,
    clinician_name: str,
    hospital_name: str,
    questions: list[str],
) -> str:
    first_name = patient_name.split()[0] if patient_name else "there"
    clinician_short = clinician_name if clinician_name else "your care team"
    hospital_short  = hospital_name  if hospital_name  else "the hospital"
    q_lines = "\n".join(f"- {q}" for q in questions)

    return f"""You are Sarah, a friendly NHS follow-up nurse. You are calling {patient_name} \
on behalf of {clinician_short} at {hospital_short}.

Your personality: warm, unhurried, genuinely caring. You sound like a real person having \
a real conversation — not reading from a list. Use natural British phrases like \
"Oh absolutely", "Right, of course", "That's good to hear" to keep things flowing.

Here is how the call should go:

When the call connects, introduce yourself simply and warmly. Something like:
"Hi, is that {first_name}? Brilliant — hi {first_name}, my name's Sarah. \
I'm just calling on behalf of {clinician_short} at {hospital_short} to see how you've \
been getting on. Hope I haven't caught you at a bad time?"

If they say it is a bad time, apologise and end the call politely.

Once they're happy to talk, mention the call may be recorded and check that's okay.

Then work through these questions, one at a time:
{q_lines}

Ask each question naturally in your own words — don't read it out robotically. \
After the patient answers, acknowledge what they said (show empathy if they're \
struggling, warmth if they're doing well), then move to the next question. \
If an answer is vague or unclear, gently clarify before moving on — \
for example: "Just so I've got that right — you said your pain is around a 4, is that correct?"

Once all questions are done, ask if there's anything else on their mind that they \
haven't mentioned. Then wrap up warmly — thank them, let them know you'll pass \
everything back to {clinician_short}, and tell them to ring NHS 111 if anything \
urgent comes up.

If at any point the patient mentions chest pain, difficulty breathing, a pain score of \
8 or above, heavy bleeding, or thoughts of self-harm — stop immediately and say: \
"That sounds like it needs urgent attention right away. Please call 999 or get to A&E \
immediately. I'm flagging this for your team now. Please don't wait. Take care. Goodbye." \
Then end the call.

Keep every response short — you're on a phone call. Never give medical advice. \
Never diagnose. If something concerns you, tell them you'll pass it on to {clinician_short}.
"""


# ─── Time slot resolver ───────────────────────────────────────────────────────

def _resolve_slot(slot: str) -> datetime:
    now = datetime.now(timezone.utc)
    if slot == "immediate":
        return now + timedelta(seconds=10)
    tomorrow = (now + timedelta(days=1)).date()
    if slot == "morning":
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 0, tzinfo=timezone.utc)
    if slot == "afternoon":
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 13, 0, tzinfo=timezone.utc)
    # Allow explicit ISO datetime for future extensibility
    try:
        return datetime.fromisoformat(slot).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, f"Unknown slot '{slot}'. Use 'immediate', 'morning', or 'afternoon'.")


# ─── Serialiser ───────────────────────────────────────────────────────────────

def _serialise(pc: ProbeCall, soap: SOAPNote | None = None) -> dict:
    return {
        "probe_call_id":     str(pc.probe_call_id),
        "patient_id":        str(pc.patient_id),
        "clinician_id":      str(pc.clinician_id),
        "note":              pc.note,
        "call_prompt":       pc.call_prompt,
        "scheduled_time":    pc.scheduled_time.isoformat(),
        "status":            pc.status,
        "call_sid":          pc.call_sid,
        "prompt_source":     pc.prompt_source,
        "needs_manual_review": pc.needs_manual_review,
        "created_at":        pc.created_at.isoformat(),
        "soap_note_id":      str(pc.soap_note_id) if pc.soap_note_id else None,
        "soap_note":         {
            "soap_id":    str(soap.soap_id),
            "subjective": soap.subjective,
            "objective":  soap.objective,
            "assessment": soap.assessment,
            "plan":       soap.plan,
        } if soap else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/probe-calls", status_code=201)
async def create_probe_call(
    data: dict,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    """
    Body: { "patient_id": "uuid", "note": "...", "slot": "immediate|morning|afternoon" }
    """
    patient_id = data.get("patient_id")
    note = (data.get("note") or "").strip()
    slot = data.get("slot", "immediate")

    if not note:
        raise HTTPException(400, "note is required")

    patient = (await db.execute(
        select(Patient).where(Patient.patient_id == uuid.UUID(patient_id))
    )).scalar_one_or_none()
    if not patient:
        raise HTTPException(404, "Patient not found")

    # Fetch clinician name and hospital for the greeting
    clin_obj = (await db.execute(
        select(Clinician).where(Clinician.clinician_id == clinician.clinician_id)
    )).scalar_one_or_none()
    hosp_obj = None
    if clin_obj:
        hosp_obj = (await db.execute(
            select(Hospital).where(Hospital.hospital_id == clin_obj.hospital_id)
        )).scalar_one_or_none()

    clinician_name = f"Dr {clin_obj.full_name}" if clin_obj else "your care team"
    hospital_name  = hosp_obj.hospital_name if hosp_obj else "the hospital"

    scheduled_time = _resolve_slot(slot)

    # Step 1: extract specific questions from clinician's note
    questions = await _extract_questions(note, patient.full_name, patient.condition)

    # Step 2: build full structured script
    call_prompt = _build_probe_script(
        patient_name=patient.full_name,
        condition=patient.condition,
        clinician_name=clinician_name,
        hospital_name=hospital_name,
        questions=questions,
    )
    prompt_source = "llm" if questions else "fallback"
    needs_review = prompt_source == "fallback"

    pc = ProbeCall(
        patient_id=patient.patient_id,
        clinician_id=clinician.clinician_id,
        note=note,
        call_prompt=call_prompt,
        scheduled_time=scheduled_time,
        status="pending",
        prompt_source=prompt_source,
        needs_manual_review=needs_review,
    )
    db.add(pc)
    await db.commit()
    await db.refresh(pc)

    # Enqueue Celery task with ETA
    from ..tasks.celery_app import celery_app
    celery_app.send_task(
        "fire_probe_call",
        args=[str(pc.probe_call_id)],
        eta=scheduled_time,
    )

    return _serialise(pc)


@router.get("/patients/{patient_id}/probe-calls")
async def list_probe_calls(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    rows = (await db.execute(
        select(ProbeCall)
        .where(ProbeCall.patient_id == uuid.UUID(patient_id))
        .order_by(ProbeCall.created_at.desc())
    )).scalars().all()
    return [_serialise(pc) for pc in rows]


@router.get("/probe-calls/{probe_call_id}")
async def get_probe_call(
    probe_call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    pc = (await db.execute(
        select(ProbeCall).where(ProbeCall.probe_call_id == uuid.UUID(probe_call_id))
    )).scalar_one_or_none()
    if not pc:
        raise HTTPException(404, "Probe call not found")

    soap = None
    if pc.soap_note_id:
        soap = (await db.execute(
            select(SOAPNote).where(SOAPNote.soap_id == pc.soap_note_id)
        )).scalar_one_or_none()
    elif pc.call_sid:
        # Attempt to resolve via CallRecord.call_sid → SOAPNote
        call = (await db.execute(
            select(CallRecord).where(CallRecord.call_sid == pc.call_sid)
        )).scalar_one_or_none()
        if call:
            soap = (await db.execute(
                select(SOAPNote).where(SOAPNote.call_id == call.call_id)
            )).scalar_one_or_none()
            if soap:
                pc.soap_note_id = soap.soap_id
                await db.commit()

    return _serialise(pc, soap)


@router.get("/probe-calls/{probe_call_id}/twiml")
async def probe_twiml(probe_call_id: str, db: AsyncSession = Depends(get_db)):
    """
    TwiML served to Twilio when the outbound probe call connects.
    Connects via SIP to the LiveKit voice agent if configured,
    otherwise reads a brief intro and hangs up gracefully.
    """
    pc = (await db.execute(
        select(ProbeCall).where(ProbeCall.probe_call_id == uuid.UUID(probe_call_id))
    )).scalar_one_or_none()
    if not pc:
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Call record not found.</Say></Response>',
            media_type="application/xml",
        )

    sip_uri = settings.livekit_sip_trunk_uri
    if sip_uri:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Sip>{sip_uri}</Sip>
  </Connect>
</Response>"""
    else:
        # Development fallback — greet and record so we have something to ingest
        intro = (
            "Hello, this is Sizor AI calling on behalf of your care team for a quick check-in. "
            "Please hold on for a moment."
        )
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">{intro}</Say>
  <Record maxLength="120" transcribe="false" />
  <Say voice="alice">Thank you. Your care team will review this shortly. Goodbye.</Say>
</Response>"""

    return Response(content=xml, media_type="application/xml")


@router.post("/probe-calls/status-callback")
async def probe_status_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Twilio posts call status updates here.
    Updates probe_call.status accordingly.
    """
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")  # initiated/ringing/in-progress/completed/failed/busy/no-answer

    if not call_sid:
        return Response(status_code=200)

    pc = (await db.execute(
        select(ProbeCall).where(ProbeCall.call_sid == call_sid)
    )).scalar_one_or_none()

    if pc:
        if call_status in ("completed",):
            pc.status = "completed"
        elif call_status in ("failed", "busy", "no-answer", "canceled"):
            pc.status = "failed"
        await db.commit()

    return Response(status_code=200)

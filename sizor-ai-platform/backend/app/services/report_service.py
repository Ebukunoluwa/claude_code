"""
Patient Summary Report Service
Generates a comprehensive clinical PDF and optionally emails it.
"""
from __future__ import annotations

import io
import smtplib
import asyncio
from datetime import date, datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

from ..config import settings

# ── Colour palette ──────────────────────────────────────────────────────────
NHS_BLUE   = colors.HexColor("#005EB8")
NHS_LIGHT  = colors.HexColor("#E8F1FB")
NHS_GREEN  = colors.HexColor("#007F3B")
NHS_AMBER  = colors.HexColor("#FFB81C")
NHS_RED    = colors.HexColor("#DA291C")
GREY_50    = colors.HexColor("#F8FAFC")
GREY_200   = colors.HexColor("#E2E8F0")
GREY_600   = colors.HexColor("#475569")
GREY_800   = colors.HexColor("#1E293B")
WHITE      = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _styles():
    base = getSampleStyleSheet()
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "title": s("RPTitle", fontName="Helvetica-Bold", fontSize=20, textColor=WHITE, leading=24, alignment=TA_LEFT),
        "subtitle": s("RPSubtitle", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#BFD9F5"), leading=14, alignment=TA_LEFT),
        "section": s("RPSection", fontName="Helvetica-Bold", fontSize=9, textColor=NHS_BLUE, leading=12, spaceBefore=6, spaceAfter=3, textTransform="uppercase", letterSpacing=0.8),
        "label": s("RPLabel", fontName="Helvetica-Bold", fontSize=8, textColor=GREY_600, leading=10),
        "body": s("RPBody", fontName="Helvetica", fontSize=9, textColor=GREY_800, leading=13),
        "body_sm": s("RPBodySm", fontName="Helvetica", fontSize=8, textColor=GREY_600, leading=11),
        "bold": s("RPBold", fontName="Helvetica-Bold", fontSize=9, textColor=GREY_800, leading=13),
        "soap_label": s("RPSoap", fontName="Helvetica-Bold", fontSize=8, textColor=NHS_BLUE, leading=10),
        "soap_body": s("RPSoapBody", fontName="Helvetica", fontSize=8, textColor=GREY_800, leading=12),
        "flag_red": s("RPFlagRed", fontName="Helvetica-Bold", fontSize=8, textColor=NHS_RED, leading=10),
        "flag_amber": s("RPFlagAmber", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#92400E"), leading=10),
        "footer": s("RPFooter", fontName="Helvetica", fontSize=7, textColor=GREY_600, leading=10, alignment=TA_CENTER),
    }


def _hr():
    return HRFlowable(width="100%", thickness=0.5, color=GREY_200, spaceAfter=6, spaceBefore=4)


def _section(title, st):
    return [
        Spacer(1, 8),
        Paragraph(title, st["section"]),
        _hr(),
    ]


def _info_table(rows: list[tuple[str, str]], st, col_widths=None):
    """Two-column label/value table."""
    usable = PAGE_W - 2 * MARGIN
    col_widths = col_widths or [usable * 0.28, usable * 0.72]
    data = [[Paragraph(k, st["label"]), Paragraph(v or "—", st["body"])] for k, v in rows]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, GREY_50]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, -1), (-1, -1), 0.3, GREY_200),
    ]))
    return tbl


def _score_badge(score, label):
    """Return coloured score text."""
    if score is None:
        return "—"
    score = float(score)
    if label in ("pain_management", "pain", "chest_pain"):
        color = "#DC2626" if score >= 3 else "#D97706" if score >= 2 else "#16A34A"
    else:
        color = "#16A34A" if score >= 3 else "#D97706" if score >= 2 else "#DC2626"
    return f'<font color="{color}"><b>{score:.0f}/4</b></font>'


def _format_dt(val):
    if not val:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%d %b %Y %H:%M")
    if isinstance(val, date):
        return val.strftime("%d %b %Y")
    try:
        return datetime.fromisoformat(str(val)).strftime("%d %b %Y %H:%M")
    except Exception:
        return str(val)


def _format_date(val):
    if not val:
        return "—"
    try:
        if isinstance(val, (date, datetime)):
            return val.strftime("%d %b %Y")
        return date.fromisoformat(str(val)).strftime("%d %b %Y")
    except Exception:
        return str(val)


def _sev_color(sev: str):
    return {"red": NHS_RED, "amber": NHS_AMBER, "green": NHS_GREEN}.get(sev, GREY_200)


# ── PDF builder ─────────────────────────────────────────────────────────────

def build_patient_summary_pdf(data: dict) -> bytes:
    """
    Accepts a pre-fetched data dict (assembled by the API endpoint) and returns
    the raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Clinical Summary – {data['patient']['full_name']}",
        author="Sizor AI Platform",
    )

    st = _styles()
    usable = PAGE_W - 2 * MARGIN
    story = []

    patient = data["patient"]
    profile = data.get("profile") or {}
    pathway = data.get("pathway") or {}
    calls   = data.get("calls") or []
    flags   = data.get("urgency_flags") or []
    actions = data.get("clinician_actions") or []
    long_s  = data.get("longitudinal_summary") or {}
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y at %H:%M UTC")

    # ── Cover header ────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"Clinical Monitoring Summary", st["title"]),
        Paragraph(f"Generated {generated_at}<br/>Sizor AI Platform", st["subtitle"]),
    ]]
    header_tbl = Table(header_data, colWidths=[usable * 0.6, usable * 0.4])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NHS_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))

    # Urgency banner if active flags
    open_flags = [f for f in flags if f.get("status") in ("open", "reviewing")]
    if open_flags:
        worst = "red" if any(f["severity"] == "red" for f in open_flags) else "amber"
        banner_text = f"⚠  {len(open_flags)} active urgency flag{'s' if len(open_flags) > 1 else ''} — {'URGENT review required' if worst == 'red' else 'review recommended'}"
        banner = Table([[Paragraph(banner_text, ParagraphStyle("banner", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, leading=12))]],
                       colWidths=[usable])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NHS_RED if worst == "red" else NHS_AMBER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(banner)
        story.append(Spacer(1, 4))

    # ── Patient information ──────────────────────────────────────────────────
    story += _section("Patient Information", st)
    discharge_date = patient.get("discharge_date")
    monitoring_days = None
    if discharge_date:
        try:
            monitoring_days = (date.today() - date.fromisoformat(str(discharge_date))).days
        except Exception:
            pass

    story.append(_info_table([
        ("Full Name",        patient.get("full_name", "")),
        ("NHS Number",       patient.get("nhs_number", "")),
        ("Date of Birth",    _format_date(patient.get("date_of_birth"))),
        ("Postcode",         patient.get("postcode") or "—"),
        ("Phone Number",     patient.get("phone_number") or "—"),
        ("Condition",        patient.get("condition") or "—"),
        ("Procedure",        patient.get("procedure") or "—"),
        ("Discharge Date",   _format_date(discharge_date)),
        ("Monitoring Period",
         f"{monitoring_days} days (since {_format_date(discharge_date)})" if monitoring_days is not None else "—"),
        ("Current Status",   (patient.get("status") or "active").upper()),
    ], st))

    # ── Medical profile ──────────────────────────────────────────────────────
    if profile:
        story += _section("Medical Profile", st)
        rows = [("Primary Diagnosis", profile.get("primary_diagnosis") or "—")]
        sec_dx = profile.get("secondary_diagnoses") or []
        if isinstance(sec_dx, list):
            sec_dx = ", ".join(sec_dx)
        if sec_dx:
            rows.append(("Secondary Diagnoses", sec_dx))

        allergies = profile.get("allergies") or []
        if isinstance(allergies, list):
            allergies = ", ".join(allergies)
        if allergies:
            rows.append(("⚠ Allergies", allergies))

        meds = profile.get("current_medications") or []
        if isinstance(meds, list):
            meds = "\n".join(f"• {m}" for m in meds)
        if meds:
            rows.append(("Current Medications", meds))

        story.append(_info_table(rows, st))

        if profile.get("consultant_notes"):
            story.append(Spacer(1, 4))
            story.append(Paragraph("Consultant Notes", st["label"]))
            story.append(Paragraph(profile["consultant_notes"], st["body"]))

        if profile.get("discharge_summary_text"):
            story.append(Spacer(1, 4))
            story.append(Paragraph("Discharge Summary", st["label"]))
            story.append(Paragraph(profile["discharge_summary_text"], st["body"]))

    # ── Pathway & monitoring plan ────────────────────────────────────────────
    if pathway:
        story += _section("Monitoring Pathway", st)
        pw_rows = [
            ("Pathway", f"{pathway.get('pathway_label', '')} ({pathway.get('opcs_code', '')})"),
        ]
        domains = pathway.get("domains") or []
        if domains:
            pw_rows.append(("Domains Monitored", ", ".join(d.replace("_", " ").title() for d in domains)))
        red_flags = pathway.get("clinical_red_flags") or []
        if red_flags:
            pw_rows.append(("Clinical Red Flags", " | ".join(red_flags)))
        risk_flags = pathway.get("risk_flags") or []
        if risk_flags:
            pw_rows.append(("Patient Risk Factors", " | ".join(risk_flags)))
        story.append(_info_table(pw_rows, st))

    # ── Longitudinal AI summary ──────────────────────────────────────────────
    if long_s.get("narrative_text"):
        story += _section("AI Longitudinal Summary", st)
        narrative = long_s["narrative_text"]
        # Strip sentinel sections
        import re
        narrative = re.sub(r"\n?\s*(?:ACTIVE_CONCERNS|TREND_SNAPSHOT)\s*:[\s\S]*", "", narrative, flags=re.IGNORECASE).strip()
        story.append(Paragraph(narrative, st["body"]))

        concerns = long_s.get("active_concerns_snapshot") or []
        if concerns:
            story.append(Spacer(1, 4))
            story.append(Paragraph("Active Concerns", st["label"]))
            for c in concerns:
                label = c.get("concern") if isinstance(c, dict) else c
                if label:
                    story.append(Paragraph(f"• {label}", st["body"]))

    # ── Urgency flags ────────────────────────────────────────────────────────
    if flags:
        story += _section(f"Urgency Flags ({len(flags)} total)", st)
        flag_rows = [
            [
                Paragraph("Severity", st["label"]),
                Paragraph("Type", st["label"]),
                Paragraph("Status", st["label"]),
                Paragraph("Raised", st["label"]),
                Paragraph("Description", st["label"]),
            ]
        ]
        for f in flags:
            sev = f.get("severity", "")
            sev_color = {"red": NHS_RED, "amber": NHS_AMBER, "green": NHS_GREEN}.get(sev, GREY_600)
            flag_rows.append([
                Paragraph(f'<font color="#{sev_color.hexval()[2:] if hasattr(sev_color, "hexval") else "475569"}"><b>{sev.upper()}</b></font>', st["body"]),
                Paragraph(f.get("flag_type", "").replace("_", " ").title(), st["body_sm"]),
                Paragraph(f.get("status", "").upper(), st["body_sm"]),
                Paragraph(_format_dt(f.get("raised_at")), st["body_sm"]),
                Paragraph(f.get("trigger_description") or "—", st["body_sm"]),
            ])
        flag_tbl = Table(flag_rows, colWidths=[usable * 0.1, usable * 0.14, usable * 0.1, usable * 0.2, usable * 0.46])
        flag_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NHS_LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_50]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.3, GREY_200),
        ]))
        story.append(flag_tbl)

    # ── Call-by-call breakdown ───────────────────────────────────────────────
    if calls:
        story += _section(f"Call Records ({len(calls)} completed)", st)

        for i, call in enumerate(calls):
            call_date = _format_dt(call.get("started_at"))
            day = call.get("day_in_recovery")
            duration = call.get("duration_seconds")
            dur_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration else "—"
            day_str = f"Day {day} post-discharge" if day is not None else ""

            header_text = f"Call {i + 1}  ·  {call_date}  ·  {day_str}  ·  Duration: {dur_str}"

            call_header = Table(
                [[Paragraph(header_text, ParagraphStyle("callhdr", fontName="Helvetica-Bold", fontSize=8.5, textColor=WHITE, leading=11))]],
                colWidths=[usable],
            )
            call_header.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E3A5F")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))

            call_elements = [Spacer(1, 6), call_header]

            # SOAP note
            soap = call.get("soap") or {}
            if soap:
                soap_rows = []
                for key, label in [("subjective", "Subjective (Patient Report)"),
                                    ("objective", "Objective"),
                                    ("assessment", "Assessment"),
                                    ("plan", "Plan")]:
                    val = soap.get(key)
                    if val:
                        soap_rows.append([
                            Paragraph(label, st["soap_label"]),
                            Paragraph(val, st["soap_body"]),
                        ])
                if soap_rows:
                    soap_tbl = Table(soap_rows, colWidths=[usable * 0.22, usable * 0.78])
                    soap_tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (0, -1), NHS_LIGHT),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.3, GREY_200),
                    ]))
                    call_elements.append(soap_tbl)

            # Clinical scores
            extraction = call.get("extraction") or {}
            scores = {}
            # Generic scores
            for field, label in [("pain_score", "Pain"), ("mood_score", "Mood"),
                                   ("mobility_score", "Mobility"), ("breathlessness_score", "Breathlessness")]:
                if extraction.get(field) is not None:
                    scores[label] = f"{extraction[field]}/10"

            # Domain scores (0–4)
            domain_scores = (extraction.get("condition_specific_flags") or {}).get("domain_scores") or {}
            domain_score_cells = []
            if domain_scores:
                for domain, score in domain_scores.items():
                    if score is not None:
                        domain_score_cells.append(
                            f"{domain.replace('_', ' ').title()}: {score}/4"
                        )

            if scores or domain_score_cells or extraction.get("medication_adherence") is not None:
                score_lines = []
                for label, val in scores.items():
                    score_lines.append(f"<b>{label}:</b> {val}")
                if extraction.get("medication_adherence") is not None:
                    adh = "Yes" if extraction["medication_adherence"] else "No"
                    score_lines.append(f"<b>Medication Adherent:</b> {adh}")
                if domain_score_cells:
                    score_lines.append("<b>Domain Scores:</b> " + "  |  ".join(domain_score_cells))

                score_tbl = Table([[Paragraph("Clinical Scores", st["soap_label"]),
                                    Paragraph("  •  ".join(score_lines), st["soap_body"])]],
                                  colWidths=[usable * 0.22, usable * 0.78])
                score_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0FDF4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                call_elements.append(score_tbl)

            # Red flags & concerns from this call
            csf = (extraction.get("condition_specific_flags") or {})
            call_red_flags = csf.get("red_flags") or []
            call_concerns = csf.get("concerns") or []
            if call_red_flags or call_concerns:
                flag_lines = []
                for rf in call_red_flags:
                    flag_lines.append(Paragraph(f"⚠ Red Flag: {rf}", st["flag_red"]))
                for concern in call_concerns:
                    flag_lines.append(Paragraph(f"• Concern: {concern}", st["flag_amber"]))
                flag_box = Table([[col] for col in flag_lines], colWidths=[usable])
                flag_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF1F2")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                call_elements.append(flag_box)

            story.append(KeepTogether(call_elements))

    # ── Clinician actions log ────────────────────────────────────────────────
    if actions:
        story += _section(f"Clinician Actions Log ({len(actions)} entries)", st)
        action_rows = [[
            Paragraph("Date", st["label"]),
            Paragraph("Type", st["label"]),
            Paragraph("Notes", st["label"]),
        ]]
        for a in actions:
            action_rows.append([
                Paragraph(_format_dt(a.get("action_at")), st["body_sm"]),
                Paragraph((a.get("action_type") or "").replace("_", " ").title(), st["body_sm"]),
                Paragraph(a.get("notes_text") or a.get("probe_instructions") or "—", st["body_sm"]),
            ])
        action_tbl = Table(action_rows, colWidths=[usable * 0.2, usable * 0.18, usable * 0.62])
        action_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NHS_LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_50]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.3, GREY_200),
        ]))
        story.append(action_tbl)

    # ── Footer note ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(_hr())
    story.append(Paragraph(
        f"This report was automatically generated by the Sizor AI clinical monitoring platform on {generated_at}. "
        "All AI-generated content should be reviewed by a qualified clinician before acting on clinical findings. "
        "This document is confidential and intended solely for the recipient.",
        st["footer"],
    ))

    doc.build(story)
    return buf.getvalue()


# ── Email sender ─────────────────────────────────────────────────────────────

def _send_email_sync(to_email: str, patient_name: str, pdf_bytes: bytes, sender_name: str):
    if not settings.smtp_host:
        raise ValueError("SMTP is not configured (SMTP_HOST is empty).")

    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} via Sizor AI <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"Clinical Monitoring Summary — {patient_name}"

    body = (
        f"Dear Colleague,\n\n"
        f"Please find attached the clinical monitoring summary for {patient_name}, "
        f"generated by the Sizor AI post-discharge monitoring platform.\n\n"
        f"This report covers all AI-assisted monitoring calls, SOAP notes, clinical extractions, "
        f"and any raised urgency flags during the monitoring period.\n\n"
        f"Please review this document and take any necessary clinical action.\n\n"
        f"Regards,\n{sender_name}\n(via Sizor AI Platform)"
    )
    msg.attach(MIMEText(body, "plain"))

    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(pdf_bytes)
    encoders.encode_base64(attachment)
    safe_name = patient_name.replace(" ", "_")
    attachment.add_header("Content-Disposition", f'attachment; filename="Sizor_Summary_{safe_name}.pdf"')
    msg.attach(attachment)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, to_email, msg.as_string())


async def send_summary_email(to_email: str, patient_name: str, pdf_bytes: bytes, sender_name: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(_send_email_sync, to_email, patient_name, pdf_bytes, sender_name),
    )

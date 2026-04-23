import { useState, useEffect, useRef } from "react";
import client from "../api/client";
import { getWards } from "../api/patients";
import { useTheme } from "../theme/ThemeContext";

const MODULES = [
  { value: "post_discharge", label: "Post Discharge" },
  { value: "post_surgery",   label: "Post Surgery" },
  { value: "routine_checks", label: "Routine Checks" },
];

const PATHWAY_CATEGORIES = ["All", "Surgical", "Obstetric", "Medical", "Mental Health"];

const PATHWAYS = [
  // ── SURGICAL ──────────────────────────────────────────────────────────────
  {
    value: "Total hip replacement", opcs: "W37", label: "Total Hip Replacement", icon: "🦴", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Hip dislocation", "DVT — leg swelling / calf pain", "PE — acute breathlessness", "Wound dehiscence / discharge", "Deep infection (fever >38.5°C)"],
    monitor: ["VTE prophylaxis (LMWH/DOAC)", "Analgesia step-down by Day 7", "Physio within 72 h", "Wound review at 10–14 days", "Orthopaedic OPD at 6 weeks", "X-ray at 6 weeks"],
  },
  {
    value: "Hip fracture / hemiarthroplasty", opcs: "W38", label: "Hip Fracture", icon: "🦴", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Acute delirium", "DVT symptoms", "PE symptoms", "Wound infection", "Falls with injury"],
    monitor: ["Delirium / cognitive screen daily", "VTE prophylaxis", "Pain management", "Falls risk assessment", "Mobility and rehabilitation", "Wound healing"],
  },
  {
    value: "Total knee replacement", opcs: "W40", label: "Total Knee Replacement", icon: "🦵", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["DVT — calf swelling / warmth", "PE — acute breathlessness", "Wound dehiscence / discharge", "Deep joint infection (fever >38.5°C)", "Severe knee effusion"],
    monitor: ["VTE prophylaxis 14 days (NICE NG89)", "Analgesia step-down by Day 7", "Physio within 72 h", "Wound review at 10–14 days", "Knee flexion target 90° by 2 wks", "Orthopaedic OPD at 6 weeks"],
  },
  {
    value: "Unicompartmental knee replacement", opcs: "W43", label: "Unicompartmental Knee", icon: "🦵", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42],
    red_flags: ["DVT symptoms", "Wound infection", "PE symptoms", "Persistent swelling"],
    monitor: ["VTE prophylaxis", "Pain management", "Mobility progress", "Wound healing", "Physio compliance"],
  },
  {
    value: "Coronary artery bypass graft", opcs: "K40_CABG", label: "CABG", icon: "❤️‍🩹", category: "Surgical", ward: "Cardiology Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    red_flags: ["Chest pain at rest", "Sternal wound breakdown", "PE symptoms", "Cardiac arrest signs", "Sustained palpitations"],
    monitor: ["Sternal wound healing", "Leg wound healing", "Antiplatelet adherence", "Cardiac rehab attendance", "Mood and depression screen", "Mobility and fatigue"],
  },
  {
    value: "Colectomy / bowel surgery", opcs: "H04", label: "Bowel Surgery", icon: "🔬", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Anastomotic leak signs", "Bowel obstruction", "Wound infection", "DVT symptoms", "Stoma complications"],
    monitor: ["Wound healing", "Bowel function recovery", "Stoma care", "Pain management", "Diet and nutrition", "VTE prophylaxis"],
  },
  {
    value: "Appendectomy", opcs: "H01", label: "Appendectomy", icon: "🏥", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28],
    red_flags: ["Wound infection", "Abscess formation", "Bowel obstruction", "Fever >38.5°C"],
    monitor: ["Wound healing", "Pain management", "Bowel function", "Infection signs", "Return to activity"],
  },
  {
    value: "Cholecystectomy", opcs: "J18_CHOLE", label: "Cholecystectomy", icon: "🏥", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28],
    red_flags: ["Jaundice", "Severe abdominal pain", "Bile leak signs", "Wound infection"],
    monitor: ["Wound healing", "Pain management", "Diet and digestion", "Jaundice monitoring"],
  },
  // ── OBSTETRIC ──────────────────────────────────────────────────────────────
  {
    value: "Elective caesarean section", opcs: "R17", label: "Elective C-Section", icon: "👶", category: "Obstetric", ward: "Maternity & Gynaecology Ward",
    call_days: [1, 3, 5, 7, 10, 14, 21, 28],
    red_flags: ["Wound dehiscence", "Postpartum haemorrhage", "PE symptoms", "Pre-eclampsia signs", "Severe postnatal depression", "Infant feeding failure"],
    monitor: ["Wound healing (Pfannenstiel)", "Pain management", "Lochia pattern", "LMWH adherence", "Postnatal depression screen", "Mobility progress", "Breastfeeding support"],
  },
  {
    value: "Emergency caesarean section", opcs: "R18", label: "Emergency C-Section", icon: "👶", category: "Obstetric", ward: "Maternity & Gynaecology Ward",
    call_days: [1, 3, 5, 7, 10, 14, 21, 28],
    red_flags: ["Wound dehiscence", "Postpartum haemorrhage", "PE symptoms", "Pre-eclampsia signs", "Severe postnatal depression", "PTSD symptoms"],
    monitor: ["Wound healing (Pfannenstiel)", "Pain management", "Lochia pattern", "LMWH adherence", "Postnatal depression screen", "Mobility progress", "Breastfeeding support", "PTSD screening", "Emotional processing of birth"],
  },
  {
    value: "Hysterectomy", opcs: "Q07", label: "Hysterectomy", icon: "🏥", category: "Obstetric", ward: "Maternity & Gynaecology Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Haemorrhage", "Wound infection", "DVT symptoms", "Urinary retention", "PE symptoms"],
    monitor: ["Wound healing", "Vaginal bleeding", "Urinary function", "VTE prophylaxis", "Pain management", "Menopausal symptoms"],
  },
  {
    value: "Radical prostatectomy", opcs: "M61", label: "Radical Prostatectomy", icon: "🏥", category: "Surgical", ward: "Surgical & Orthopaedic Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Haemorrhage", "Catheter blockage", "DVT symptoms", "PE symptoms", "Wound infection"],
    monitor: ["Wound healing", "Urinary continence", "Catheter care", "Pain management", "VTE prophylaxis"],
  },
  // ── MEDICAL ──────────────────────────────────────────────────────────────
  {
    value: "Heart failure", opcs: "K60", label: "Heart Failure", icon: "❤️", category: "Medical", ward: "Cardiology Ward",
    call_days: [1, 3, 7, 14, 21, 30, 42, 60, 90],
    red_flags: ["Breathlessness at rest", "Weight gain >2 kg in 2 days", "O₂ sat below 92%", "Chest pain", "Acute confusion", "Uncontrolled oedema", "BP >180 mmHg", "Anuria / oliguria"],
    monitor: ["Daily weight monitoring", "Breathlessness (NYHA)", "Ankle swelling", "Diuretic adherence", "Fluid restriction", "Renal function", "Blood pressure", "Cardiac rehab referral"],
  },
  {
    value: "Myocardial infarction / ACS", opcs: "K40", label: "MI / ACS", icon: "❤️‍🔥", category: "Medical", ward: "Cardiology Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Chest pain at rest", "Syncope", "Sustained palpitations", "Breathlessness at rest", "PE symptoms"],
    monitor: ["Chest pain monitoring", "Antiplatelet adherence", "Cardiac rehab attendance", "Mood and depression screen", "Activity progression", "Risk factor modification"],
  },
  {
    value: "Atrial fibrillation", opcs: "K57", label: "Atrial Fibrillation", icon: "💓", category: "Medical", ward: "Cardiology Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Severe palpitations", "Stroke signs", "Haemorrhage", "Syncope", "Acute breathlessness"],
    monitor: ["Rate control monitoring", "Anticoagulation adherence", "Symptom monitoring", "Bleeding signs", "Mood and anxiety"],
  },
  {
    value: "Stroke / ischaemic", opcs: "S01", label: "Stroke", icon: "🧠", category: "Medical", ward: "Medical & Emergency Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    red_flags: ["New neurological symptoms", "Anticoagulant non-adherence", "BP severely uncontrolled", "Dysphagia / aspiration risk", "Falls with injury", "Stroke recurrence signs"],
    monitor: ["Neurological deficit monitoring", "Antiplatelet / anticoagulant", "Blood pressure control", "Swallowing and nutrition", "Mood / post-stroke depression", "Rehabilitation attendance", "Falls risk"],
  },
  {
    value: "TIA", opcs: "G45", label: "TIA", icon: "🧠", category: "Medical", ward: "Medical & Emergency Ward",
    call_days: [1, 3, 7, 14, 21, 28],
    red_flags: ["New neurological symptoms", "Missed antiplatelet dose", "BP crisis", "Stroke signs"],
    monitor: ["Symptom recurrence", "Antiplatelet adherence", "Blood pressure control", "Lifestyle modification"],
  },
  {
    value: "COPD exacerbation", opcs: "J44", label: "COPD", icon: "🫁", category: "Medical", ward: "Respiratory Ward",
    call_days: [1, 3, 7, 14, 28, 42, 56],
    red_flags: ["O₂ sat below 88%", "Acute severe breathlessness", "Central cyanosis", "Acute confusion", "Unable to complete sentences"],
    monitor: ["Inhaler technique review", "Steroid and antibiotic course completion", "Oxygen saturation", "Smoking cessation support", "GP review within 2 weeks", "Resp nurse call within 72 h", "Pulmonary rehab within 4 weeks", "Spirometry at 6 weeks"],
  },
  {
    value: "Pneumonia", opcs: "J18_PNEUMONIA", label: "Pneumonia", icon: "🫁", category: "Medical", ward: "Respiratory Ward",
    call_days: [1, 3, 7, 14, 21, 28],
    red_flags: ["O₂ sat below 92%", "Fever returning after Day 3", "Pleuritic chest pain", "Haemoptysis", "Confusion"],
    monitor: ["Breathlessness and cough", "Antibiotic completion", "Temperature and fever", "Fatigue and recovery"],
  },
  {
    value: "Sepsis", opcs: "A41", label: "Sepsis", icon: "🌡️", category: "Medical", ward: "Medical & Emergency Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Fever recurrence", "Source not controlled", "Antibiotic non-completion", "Acute confusion", "O₂ sat below 92%"],
    monitor: ["Temperature and fever", "Antibiotic course completion", "Source monitoring", "Fatigue and functional recovery", "Cognitive function", "Psychological impact"],
  },
  {
    value: "Pulmonary embolism", opcs: "I26", label: "Pulmonary Embolism", icon: "🩸", category: "Medical", ward: "Medical & Emergency Ward",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60],
    red_flags: ["Missed anticoagulant dose", "Haemorrhage", "Acute breathlessness", "Recurrent PE signs", "Syncope"],
    monitor: ["Anticoagulation adherence", "Breathlessness recovery", "Bleeding signs", "DVT signs"],
  },
  {
    value: "Diabetic ketoacidosis", opcs: "E11_DKA", label: "DKA", icon: "💉", category: "Medical", ward: "Medical & Emergency Ward",
    call_days: [1, 3, 7, 14, 21, 28],
    red_flags: ["Blood glucose >20 mmol/L", "Moderate–high ketones", "Vomiting preventing medication", "Confusion", "Hyperglycaemia unresponsive to treatment"],
    monitor: ["Blood glucose monitoring", "Insulin / medication adherence", "Trigger identification", "Sick day rules education", "Ketone monitoring"],
  },
  // ── MENTAL HEALTH ──────────────────────────────────────────────────────────
  {
    value: "Acute psychiatric admission", opcs: "Z03_MH", label: "Acute Psychiatry", icon: "🧠", category: "Mental Health", ward: "Mental Health Unit",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    red_flags: ["Active suicidal ideation", "Medication stopped abruptly", "Psychotic relapse", "Risk to others", "Safeguarding concern", "Missing from contact"],
    monitor: ["Medication concordance", "Mood and mental state", "Safety and safeguarding", "Community team engagement", "Crisis plan awareness", "Social support and daily living", "Substance use screen"],
  },
  {
    value: "Self-harm / overdose", opcs: "X60", label: "Self-Harm / Overdose", icon: "🤝", category: "Mental Health", ward: "Mental Health Unit",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    red_flags: ["Suicidal ideation with plan", "Means not restricted", "Missed follow-up appointment", "Medication stockpiling", "Acute deterioration"],
    monitor: ["Safety and suicidality", "Crisis plan and means restriction", "Mental health follow-up", "Medication adherence", "Mood and psychological state", "Social and protective factors"],
  },
  {
    value: "First episode psychosis", opcs: "F20", label: "First Episode Psychosis", icon: "🧠", category: "Mental Health", ward: "Mental Health Unit",
    call_days: [1, 3, 7, 14, 21, 28, 42, 60, 90],
    red_flags: ["Antipsychotic stopped", "Florid psychosis", "Risk to self or others", "Disengagement from EIS", "Safeguarding concern"],
    monitor: ["Antipsychotic adherence", "Psychotic symptoms", "Early intervention team engagement", "Safety and risk", "Family and carer support", "Daily functioning and insight"],
  },
];

const EMPTY = {
  full_name: "", nhs_number: "", phone_number: "",
  date_of_birth: "", postcode: "", pathway: "",
  ward_id: "",
  procedure: "", discharge_date: "", program_module: "post_discharge",
  primary_diagnosis: "", current_medications: "", allergies: "",
  schedule_date: "", schedule_time: "",
};

export default function AddPatientModal({ clinician, onClose, onAdded }) {
  const { t } = useTheme();
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pathwayTab, setPathwayTab] = useState("All");
  const [monitorItems, setMonitorItems] = useState({});
  const [newMonitor, setNewMonitor] = useState("");
  const [wards, setWards] = useState([]);
  const formBodyRef = useRef(null);

  useEffect(() => {
    getWards().then(setWards).catch(() => {});
  }, []);

  const selectedWard    = wards.find((w) => w.ward_id === form.ward_id) ?? null;
  const selectedPathway = PATHWAYS.find((p) => p.value === form.pathway) ?? null;
  const currentMonitor  = form.pathway ? (monitorItems[form.pathway] ?? []) : [];
  const visiblePathways = selectedWard
    ? PATHWAYS.filter((p) => p.ward === selectedWard.ward_name)
    : PATHWAYS;

  function selectPathway(value) {
    setForm((f) => ({ ...f, pathway: f.pathway === value ? "" : value }));
    if (!monitorItems[value]) {
      const p = PATHWAYS.find((p) => p.value === value);
      if (p) setMonitorItems((m) => ({ ...m, [value]: [...p.monitor] }));
    }
  }

  function removeMonitor(item) {
    setMonitorItems((m) => ({ ...m, [form.pathway]: m[form.pathway].filter((i) => i !== item) }));
  }

  function addMonitor() {
    const val = newMonitor.trim();
    if (!val || !form.pathway) return;
    setMonitorItems((m) => ({ ...m, [form.pathway]: [...(m[form.pathway] || []), val] }));
    setNewMonitor("");
  }

  function set(field, value) {
    setForm((f) => {
      const next = { ...f, [field]: value };
      // Reset pathway if ward changes and the selected pathway doesn't belong to the new ward
      if (field === "ward_id") {
        const newWard = wards.find((w) => w.ward_id === value);
        const currentPathway = PATHWAYS.find((p) => p.value === f.pathway);
        if (newWard && currentPathway && currentPathway.ward !== newWard.ward_name) {
          next.pathway = "";
        }
        setPathwayTab("All");
      }
      return next;
    });
  }

  function showError(msg) {
    setError(msg);
    // Scroll form body to top so the error banner is visible
    if (formBodyRef.current) {
      formBodyRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    // Client-side validation — the footer button is outside the <form> so
    // HTML `required` attributes are never triggered; we enforce them here.
    if (!form.full_name.trim()) return showError("Full name is required.");
    if (!form.nhs_number.trim()) return showError("NHS number is required.");
    if (!form.phone_number.trim()) return showError("Phone number is required.");
    // Warn if number looks local (missing country code) — UK local is auto-corrected
    // by the voice agent, but ambiguous international numbers will fail silently.
    const rawPhone = form.phone_number.trim();
    const digitsOnly = rawPhone.replace(/[\s\-().]/g, "");
    if (!digitsOnly.startsWith("+") && !digitsOnly.startsWith("00")) {
      if (!/^0[127]\d{9}$/.test(digitsOnly)) {
        return showError(
          "Phone number must be in international format, e.g. +2348012345678 for Nigeria or +447700900123 for UK. " +
          "Local formats without a country code may not connect."
        );
      }
    }
    if (!form.ward_id) return showError("Please select a ward.");
    if (selectedPathway && !form.discharge_date) return showError("Discharge date is required when a pathway is selected.");
    if (form.schedule_date && !form.schedule_time) return showError("Please set a time for the scheduled call.");

    setError(""); setSaving(true);
    try {
      let patientId;

      if (selectedPathway && form.discharge_date) {
        // ── Full pathway registration (creates patient + pathway record + playbook) ──
        const payload = {
          nhs_number:    form.nhs_number.trim(),
          name:          form.full_name.trim(),
          phone_number:  form.phone_number.trim(),
          opcs_code:     selectedPathway.opcs,
          discharge_date: form.discharge_date,
          ...(form.date_of_birth && { date_of_birth: form.date_of_birth }),
          ...(form.postcode && { postcode: form.postcode.replace(/\s/g, "").toUpperCase() }),
          ...(form.ward_id && { ward_id: form.ward_id }),
          // Pass editable monitoring items as custom domain names
          domains: currentMonitor,
          // Pass visible red flags
          clinical_red_flags: selectedPathway.red_flags,
        };
        const { data: created } = await client.post("/patients/pathway-register", payload);
        patientId = created.patient_id;
      } else {
        // ── Basic patient creation (no pathway selected or no discharge date) ──
        const payload = {
          hospital_id:    clinician.hospital_id,
          full_name:      form.full_name.trim(),
          nhs_number:     form.nhs_number.trim(),
          phone_number:   form.phone_number.trim(),
          condition:      form.pathway || form.procedure || "General",
          program_module: form.program_module,
          ...(form.date_of_birth  && { date_of_birth:  form.date_of_birth }),
          ...(form.postcode        && { postcode: form.postcode.replace(/\s/g, "").toUpperCase() }),
          ...(form.procedure       && { procedure: form.procedure.trim() }),
          ...(form.discharge_date  && { discharge_date: form.discharge_date }),
          ...(form.ward_id         && { ward_id: form.ward_id }),
        };

        const hasMedical = form.primary_diagnosis || form.current_medications || form.allergies;
        if (hasMedical) {
          payload.medical_profile = {
            ...(form.primary_diagnosis  && { primary_diagnosis: form.primary_diagnosis.trim() }),
            ...(form.current_medications && {
              current_medications: form.current_medications.split(",").map((m) => m.trim()).filter(Boolean),
            }),
            ...(form.allergies && {
              allergies: form.allergies.split(",").map((a) => a.trim()).filter(Boolean),
            }),
          };
        }

        const { data: created } = await client.post("/patients", payload);
        patientId = created.patient_id;
      }

      // ── Optional one-off schedule (on top of any pathway call schedule) ──
      if (form.schedule_date && form.schedule_time && patientId) {
        const scheduledFor = new Date(`${form.schedule_date}T${form.schedule_time}:00`).toISOString();
        await client.post(`/patients/${patientId}/schedule`, {
          scheduled_for: scheduledFor,
          call_type: "outbound",
          module: form.program_module,
          protocol_name: form.program_module,
        });
      }

      onAdded?.(); onClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      let msg = Array.isArray(detail)
        ? detail.map((e) => e.msg || JSON.stringify(e)).join("; ")
        : typeof detail === "string" ? detail
        : err.message || "Failed to add patient.";
      // Friendlier message for duplicate NHS numbers
      if (msg.includes("unique") || msg.includes("duplicate") || msg.includes("UniqueViolation")) {
        msg = `A patient with NHS number "${form.nhs_number.trim()}" already exists.`;
      }
      showError(msg);
    } finally {
      setSaving(false);
    }
  }

  // ── Shared style helpers ────────────────────────────────────────────────────
  const inputStyle = {
    width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "10px",
    border: `1px solid ${t.border}`, background: t.surface, color: t.textPrimary,
    outline: "none", transition: "border-color 0.15s, box-shadow 0.15s",
    colorScheme: t.isDark ? "dark" : "light",
  };
  const inputFocus = { borderColor: t.brand, boxShadow: `0 0 0 3px ${t.brandGlow}` };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50, display: "flex",
      alignItems: "center", justifyContent: "center", padding: "16px",
      background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)",
    }}>
      <div style={{
        background: t.surface, borderRadius: "16px", border: `1px solid ${t.border}`,
        boxShadow: `0 24px 48px ${t.shadow}`, width: "100%", maxWidth: "672px",
        maxHeight: "90vh", display: "flex", flexDirection: "column",
      }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 24px", borderBottom: `1px solid ${t.border}` }}>
          <div>
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: t.textPrimary, margin: 0 }}>
              Add New Patient
            </h2>
            <p style={{ fontSize: "11px", color: t.textMuted, marginTop: "2px" }}>
              Register a patient and optionally schedule a call
            </p>
          </div>
          <button onClick={onClose} style={{
            width: 32, height: 32, borderRadius: "50%", border: "none",
            background: "transparent", cursor: "pointer", color: t.textMuted,
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "background 0.15s",
          }}
            onMouseEnter={e => e.currentTarget.style.background = t.surfaceHigh}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form ref={formBodyRef} onSubmit={handleSubmit} style={{ overflowY: "auto", flex: 1, padding: "20px 24px", display: "flex", flexDirection: "column", gap: "20px" }}>

          {error && (
            <div style={{ background: t.redBg, border: `1px solid ${t.redBorder}`, color: t.red,
              fontSize: "13px", padding: "10px 16px", borderRadius: "10px" }}>
              {error}
            </div>
          )}

          {/* Patient Details */}
          <section>
            <SectionLabel t={t}>Patient Details</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <Field label="Full Name *" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text" placeholder="e.g. James Okafor"
                  value={form.full_name} onChange={(e) => set("full_name", e.target.value)} required />
              </Field>
              <Field label="NHS Number *" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text" placeholder="e.g. 485 777 3456"
                  value={form.nhs_number} onChange={(e) => set("nhs_number", e.target.value)} required />
              </Field>
              <Field label="Phone Number *" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="tel" placeholder="e.g. +447700900123"
                  value={form.phone_number} onChange={(e) => set("phone_number", e.target.value)} required />
              </Field>
              <Field label="Date of Birth" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="date"
                  value={form.date_of_birth} onChange={(e) => set("date_of_birth", e.target.value)} />
              </Field>
              <Field label="Postcode" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text" placeholder="e.g. SW1A 2AA"
                  maxLength={8} value={form.postcode}
                  onChange={(e) => set("postcode", e.target.value.toUpperCase())} />
              </Field>
              <Field label="Ward *" t={t}>
                <select value={form.ward_id} onChange={(e) => set("ward_id", e.target.value)}
                  required style={inputStyle}>
                  <option value="">Select a ward…</option>
                  {wards.map((w) => (
                    <option key={w.ward_id} value={w.ward_id}
                      style={{ background: t.surface, color: t.textPrimary }}>
                      {w.ward_name} — {w.specialty}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </section>

          {/* Clinical Pathway */}
          <section>
            <SectionLabel t={t}>Clinical Pathway</SectionLabel>
            {selectedWard && (
              <p style={{ fontSize: "11px", color: t.brand, marginBottom: "10px", fontFamily: "'DM Mono',monospace" }}>
                Showing {visiblePathways.length} pathway{visiblePathways.length !== 1 ? "s" : ""} for {selectedWard.ward_name}
              </p>
            )}

            {/* Category tabs — only show if no ward selected or ward spans multiple categories */}
            {(!selectedWard || visiblePathways.length > 6) && (
              <div style={{ display: "flex", gap: "6px", marginBottom: "10px", flexWrap: "wrap" }}>
                {PATHWAY_CATEGORIES.map((cat) => {
                  const count = cat === "All" ? visiblePathways.length : visiblePathways.filter(p => p.category === cat).length;
                  if (count === 0) return null;
                  const active = pathwayTab === cat;
                  return (
                    <button key={cat} type="button" onClick={() => setPathwayTab(cat)} style={{
                      padding: "4px 12px", borderRadius: "999px", fontSize: "11px", fontWeight: 600,
                      cursor: "pointer", transition: "all 0.15s",
                      border: `1px solid ${active ? t.brand : t.border}`,
                      background: active ? t.brandGlow : "transparent",
                      color: active ? t.brand : t.textMuted,
                    }}>
                      {cat}
                      <span style={{ marginLeft: "5px", fontSize: "10px", opacity: 0.7 }}>{count}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Pathway cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", marginBottom: "12px" }}>
              {visiblePathways.filter(p => pathwayTab === "All" || p.category === pathwayTab).map((p) => {
                const active = form.pathway === p.value;
                return (
                  <button key={p.value} type="button" onClick={() => selectPathway(p.value)} style={{
                    display: "flex", flexDirection: "column", alignItems: "center", gap: "6px",
                    padding: "12px 8px", borderRadius: "10px", cursor: "pointer",
                    border: `1px solid ${active ? t.brand : t.border}`,
                    background: active ? t.brandGlow : t.surfaceHigh,
                    color: active ? t.brand : t.textMuted,
                    fontSize: "11px", fontWeight: 600, transition: "all 0.15s",
                  }}
                    onMouseEnter={e => { if (!active) { e.currentTarget.style.borderColor = t.borderHigh; e.currentTarget.style.color = t.textSecond; }}}
                    onMouseLeave={e => { if (!active) { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textMuted; }}}
                  >
                    <span style={{ fontSize: "20px" }}>{p.icon}</span>
                    <span style={{ textAlign: "center", lineHeight: 1.3 }}>{p.label}</span>
                  </button>
                );
              })}
            </div>

            {/* NICE guidelines panel */}
            {selectedPathway && (
              <div style={{ border: `1px solid ${t.border}`, borderRadius: "10px",
                background: t.surfaceHigh, overflow: "hidden", marginBottom: "12px" }}>

                {/* Call schedule */}
                <div style={{ padding: "10px 16px", borderBottom: `1px solid ${t.border}`,
                  display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "10px", fontWeight: 700, color: t.textMuted,
                    textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
                    Call schedule (post-discharge day)
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                    {selectedPathway.call_days.map((d) => (
                      <span key={d} style={{
                        padding: "2px 8px", borderRadius: "999px", fontSize: "11px", fontWeight: 600,
                        background: t.brandGlow, border: `1px solid ${t.brand}50`, color: t.brand,
                      }}>Day {d}</span>
                    ))}
                  </div>
                </div>

                {/* Red flags */}
                <div style={{ padding: "12px 16px", borderBottom: `1px solid ${t.border}` }}>
                  <p style={{ fontSize: "10px", fontWeight: 700, color: t.red,
                    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
                    Red Flags — NICE
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {selectedPathway.red_flags.map((f, i) => (
                      <span key={i} style={{
                        padding: "3px 10px", borderRadius: "999px", fontSize: "11px",
                        background: t.redBg, border: `1px solid ${t.redBorder}`, color: t.red,
                      }}>{f}</span>
                    ))}
                  </div>
                </div>

                {/* Monitoring — editable */}
                <div style={{ padding: "12px 16px" }}>
                  <p style={{ fontSize: "10px", fontWeight: 700, color: t.brand,
                    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
                    Monitoring &amp; Follow-up
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                    {currentMonitor.map((item, i) => (
                      <span key={i} style={{
                        display: "flex", alignItems: "center", gap: "4px",
                        padding: "3px 10px", borderRadius: "999px", fontSize: "11px",
                        background: t.brandGlow, border: `1px solid ${t.brand}40`, color: t.brand,
                      }}>
                        {item}
                        <button type="button" onClick={() => removeMonitor(item)} style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: t.textMuted, fontSize: "13px", lineHeight: 1,
                          padding: "0 0 0 2px", transition: "color 0.15s",
                        }}
                          onMouseEnter={e => e.currentTarget.style.color = t.red}
                          onMouseLeave={e => e.currentTarget.style.color = t.textMuted}
                        >×</button>
                      </span>
                    ))}
                  </div>
                  {/* Add item */}
                  <div style={{ display: "flex", gap: "8px" }}>
                    <Input style={{ ...inputStyle, fontSize: "12px", padding: "6px 10px", flex: 1 }}
                      focusStyle={inputFocus} type="text" placeholder="Add monitoring item…"
                      value={newMonitor} onChange={(e) => setNewMonitor(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addMonitor())} />
                    <button type="button" onClick={addMonitor} style={{
                      padding: "6px 14px", fontSize: "12px", fontWeight: 600,
                      background: t.brand, color: "#fff", border: "none",
                      borderRadius: "8px", cursor: "pointer", whiteSpace: "nowrap",
                      transition: "opacity 0.15s",
                    }}
                      onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
                      onMouseLeave={e => e.currentTarget.style.opacity = "1"}
                    >+ Add</button>
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <Field label="Procedure" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text"
                  placeholder="e.g. Total hip arthroplasty" value={form.procedure}
                  onChange={(e) => set("procedure", e.target.value)} />
              </Field>
              <Field label={selectedPathway ? "Discharge Date *" : "Discharge Date"} t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="date"
                  value={form.discharge_date} onChange={(e) => set("discharge_date", e.target.value)} />
                {selectedPathway && !form.discharge_date && (
                  <p style={{ fontSize: "10px", color: t.amber, marginTop: "4px" }}>
                    Required to register pathway &amp; generate call schedule
                  </p>
                )}
              </Field>
              <Field label="Programme *" t={t}>
                <select value={form.program_module} onChange={(e) => set("program_module", e.target.value)}
                  required style={inputStyle}>
                  {MODULES.map((m) => (
                    <option key={m.value} value={m.value}
                      style={{ background: t.surface, color: t.textPrimary }}>{m.label}</option>
                  ))}
                </select>
              </Field>
            </div>
          </section>

          {/* Medical Profile */}
          <section>
            <SectionLabel t={t} optional>Medical Profile</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <Field label="Primary Diagnosis" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text"
                  placeholder="e.g. Osteoarthritis of the left hip" value={form.primary_diagnosis}
                  onChange={(e) => set("primary_diagnosis", e.target.value)} />
              </Field>
              <Field label="Current Medications — Comma separated" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text"
                  placeholder="e.g. Paracetamol, Ibuprofen, Lansoprazole" value={form.current_medications}
                  onChange={(e) => set("current_medications", e.target.value)} />
              </Field>
              <Field label="Allergies — Comma separated" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="text"
                  placeholder="e.g. Penicillin, Aspirin" value={form.allergies}
                  onChange={(e) => set("allergies", e.target.value)} />
              </Field>
            </div>
          </section>

          {/* Schedule */}
          <section>
            <SectionLabel t={t} optional>Schedule First Call</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <Field label="Date" t={t}>
                <Input style={inputStyle} focusStyle={inputFocus} type="date"
                  value={form.schedule_date} onChange={(e) => set("schedule_date", e.target.value)} />
              </Field>
              <Field label="Time" t={t}>
                <Input style={{ ...inputStyle, opacity: form.schedule_date ? 1 : 0.5 }}
                  focusStyle={inputFocus} type="time" value={form.schedule_time}
                  onChange={(e) => set("schedule_time", e.target.value)}
                  disabled={!form.schedule_date} />
              </Field>
            </div>
            {form.schedule_date && !form.schedule_time && (
              <p style={{ fontSize: "11px", color: t.amber, marginTop: "6px" }}>Please also set a time.</p>
            )}
          </section>

        </form>

        {/* Footer */}
        <div style={{ padding: "14px 24px", borderTop: `1px solid ${t.border}`,
          display: "flex", flexDirection: "column", gap: "10px" }}>
          {error && (
            <div style={{
              background: t.redBg, border: `1px solid ${t.redBorder}`, color: t.red,
              fontSize: "12px", padding: "8px 14px", borderRadius: "8px",
            }}>
              {error}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "12px" }}>
          <button type="button" onClick={onClose} style={{
            padding: "8px 16px", fontSize: "13px", fontWeight: 500,
            background: "none", border: "none", cursor: "pointer",
            color: t.textMuted, transition: "color 0.15s",
          }}
            onMouseEnter={e => e.currentTarget.style.color = t.textPrimary}
            onMouseLeave={e => e.currentTarget.style.color = t.textMuted}
          >Cancel</button>
          <button onClick={handleSubmit} disabled={saving} style={{
            padding: "8px 20px", fontSize: "13px", fontWeight: 700,
            background: t.brand, color: "#fff", border: "none", borderRadius: "10px",
            cursor: saving ? "not-allowed" : "pointer", opacity: saving ? 0.6 : 1,
            display: "flex", alignItems: "center", gap: "8px", transition: "opacity 0.15s",
          }}>
            {saving && (
              <svg style={{ animation: "spin 1s linear infinite", width: 14, height: 14 }}
                fill="none" viewBox="0 0 24 24">
                <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {saving ? "Saving…" : "Add Patient"}
          </button>
          </div>
        </div>

      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionLabel({ children, optional, t }) {
  return (
    <p style={{ fontSize: "10px", fontWeight: 700, color: t.textMuted,
      textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>
      {children}
      {optional && <span style={{ fontWeight: 400, textTransform: "none", color: t.textMuted, marginLeft: "4px" }}>(optional)</span>}
    </p>
  );
}

function Field({ label, children, t }) {
  return (
    <label style={{ display: "block" }}>
      <span style={{ display: "block", fontSize: "11px", fontWeight: 600,
        color: t.textSecond, marginBottom: "4px" }}>
        {label}
      </span>
      {children}
    </label>
  );
}

/** Controlled input that applies focus styles via JS (since we can't use :focus in inline styles) */
function Input({ style, focusStyle, ...props }) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      {...props}
      style={{ ...style, ...(focused ? focusStyle : {}) }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  );
}

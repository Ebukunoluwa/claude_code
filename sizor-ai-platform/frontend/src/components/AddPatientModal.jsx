import { useState } from "react";
import client from "../api/client";

const MODULES = [
  { value: "post_discharge", label: "Post Discharge" },
  { value: "post_surgery", label: "Post Surgery" },
  { value: "routine_checks", label: "Routine Checks" },
];

const EMPTY = {
  full_name: "",
  nhs_number: "",
  phone_number: "",
  date_of_birth: "",
  condition: "",
  procedure: "",
  discharge_date: "",
  program_module: "post_discharge",
  primary_diagnosis: "",
  current_medications: "",
  allergies: "",
  schedule_date: "",
  schedule_time: "",
};

export default function AddPatientModal({ clinician, onClose, onAdded }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const payload = {
        hospital_id: clinician.hospital_id,
        full_name: form.full_name.trim(),
        nhs_number: form.nhs_number.trim(),
        phone_number: form.phone_number.trim(),
        condition: form.condition.trim(),
        program_module: form.program_module,
        ...(form.date_of_birth && { date_of_birth: form.date_of_birth }),
        ...(form.procedure && { procedure: form.procedure.trim() }),
        ...(form.discharge_date && { discharge_date: form.discharge_date }),
      };

      const hasMedical = form.primary_diagnosis || form.current_medications || form.allergies;
      if (hasMedical) {
        payload.medical_profile = {
          ...(form.primary_diagnosis && { primary_diagnosis: form.primary_diagnosis.trim() }),
          ...(form.current_medications && {
            current_medications: form.current_medications
              .split(",")
              .map((m) => m.trim())
              .filter(Boolean),
          }),
          ...(form.allergies && {
            allergies: form.allergies
              .split(",")
              .map((a) => a.trim())
              .filter(Boolean),
          }),
        };
      }

      const { data: created } = await client.post("/patients", payload);

      if (form.schedule_date && form.schedule_time) {
        const scheduledFor = `${form.schedule_date}T${form.schedule_time}:00`;
        await client.post(`/patients/${created.patient_id}/schedule`, {
          scheduled_for: scheduledFor,
          call_type: "outbound",
          module: form.program_module,
          protocol_name: form.program_module,
        });
      }

      onAdded?.();
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((e) => e.msg || JSON.stringify(e)).join("; ")
        : typeof detail === "string"
        ? detail
        : err.message || "Failed to add patient.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Add New Patient</h2>
            <p className="text-xs text-gray-400 mt-0.5">Register a patient and optionally schedule a call</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1 px-6 py-5 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2.5 rounded-xl">
              {error}
            </div>
          )}

          {/* Patient details */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Patient Details</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Full Name *" required>
                <input
                  type="text"
                  placeholder="e.g. James Okafor"
                  value={form.full_name}
                  onChange={(e) => set("full_name", e.target.value)}
                  required
                  className="input"
                />
              </Field>
              <Field label="NHS Number *" required>
                <input
                  type="text"
                  placeholder="e.g. 485 777 3456"
                  value={form.nhs_number}
                  onChange={(e) => set("nhs_number", e.target.value)}
                  required
                  className="input"
                />
              </Field>
              <Field label="Phone Number *" required>
                <input
                  type="tel"
                  placeholder="e.g. +447700900123"
                  value={form.phone_number}
                  onChange={(e) => set("phone_number", e.target.value)}
                  required
                  className="input"
                />
              </Field>
              <Field label="Date of Birth">
                <input
                  type="date"
                  value={form.date_of_birth}
                  onChange={(e) => set("date_of_birth", e.target.value)}
                  className="input"
                />
              </Field>
            </div>
          </section>

          {/* Clinical */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Clinical</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Condition *" required>
                <input
                  type="text"
                  placeholder="e.g. Hip replacement"
                  value={form.condition}
                  onChange={(e) => set("condition", e.target.value)}
                  required
                  className="input"
                />
              </Field>
              <Field label="Procedure">
                <input
                  type="text"
                  placeholder="e.g. Total hip arthroplasty"
                  value={form.procedure}
                  onChange={(e) => set("procedure", e.target.value)}
                  className="input"
                />
              </Field>
              <Field label="Discharge Date">
                <input
                  type="date"
                  value={form.discharge_date}
                  onChange={(e) => set("discharge_date", e.target.value)}
                  className="input"
                />
              </Field>
              <Field label="Programme *" required>
                <select
                  value={form.program_module}
                  onChange={(e) => set("program_module", e.target.value)}
                  required
                  className="input"
                >
                  {MODULES.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </Field>
            </div>
          </section>

          {/* Medical profile */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Medical Profile <span className="font-normal normal-case text-gray-400">(optional)</span></h3>
            <div className="space-y-3">
              <Field label="Primary Diagnosis">
                <input
                  type="text"
                  placeholder="e.g. Osteoarthritis of the left hip"
                  value={form.primary_diagnosis}
                  onChange={(e) => set("primary_diagnosis", e.target.value)}
                  className="input"
                />
              </Field>
              <Field label="Current Medications" hint="Comma separated">
                <input
                  type="text"
                  placeholder="e.g. Paracetamol, Ibuprofen, Lansoprazole"
                  value={form.current_medications}
                  onChange={(e) => set("current_medications", e.target.value)}
                  className="input"
                />
              </Field>
              <Field label="Allergies" hint="Comma separated">
                <input
                  type="text"
                  placeholder="e.g. Penicillin, Aspirin"
                  value={form.allergies}
                  onChange={(e) => set("allergies", e.target.value)}
                  className="input"
                />
              </Field>
            </div>
          </section>

          {/* Schedule */}
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Schedule First Call <span className="font-normal normal-case text-gray-400">(optional)</span></h3>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Date">
                <input
                  type="date"
                  value={form.schedule_date}
                  onChange={(e) => set("schedule_date", e.target.value)}
                  className="input"
                />
              </Field>
              <Field label="Time">
                <input
                  type="time"
                  value={form.schedule_time}
                  onChange={(e) => set("schedule_time", e.target.value)}
                  className="input"
                  disabled={!form.schedule_date}
                />
              </Field>
            </div>
            {form.schedule_date && !form.schedule_time && (
              <p className="text-xs text-amber-600 mt-1.5">Please also set a time.</p>
            )}
          </section>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-5 py-2 text-sm font-semibold bg-nhs-blue text-white rounded-xl hover:bg-blue-700 disabled:opacity-60 transition flex items-center gap-2"
          >
            {saving && (
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            )}
            {saving ? "Saving…" : "Add Patient"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, hint, required, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-gray-600 mb-1">
        {label}
        {hint && <span className="text-gray-400 font-normal ml-1">— {hint}</span>}
      </span>
      {children}
    </label>
  );
}

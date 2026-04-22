import { useState, useEffect } from "react";
import {
  getPatientSchedule,
  getPatientPathwayInfo,
  bulkCreateSchedule,
  updateSchedule,
  deleteSchedule,
} from "../api/patients";

// ── helpers ──────────────────────────────────────────────────────────────────

function addDays(dateStr, days) {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function toISO(dateStr, timeStr) {
  // Converts local date+time to UTC ISO string (respects browser timezone)
  return new Date(`${dateStr}T${timeStr}:00`).toISOString();
}

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric",
  });
}
function fmtTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

const STATUS_STYLES = {
  pending:    "bg-blue-50 text-blue-700 border-blue-200",
  dispatched: "bg-blue-50 text-blue-700 border-blue-200",
  completed:  "bg-green-50 text-green-700 border-green-200",
  missed:     "bg-red-50 text-red-700 border-red-200",
  cancelled:  "bg-gray-100 text-gray-500 border-gray-200",
};

// ── component ─────────────────────────────────────────────────────────────────

export default function SchedulerPanel({ patient }) {
  const patientId = patient.patient_id;

  // ── state ─────────────────────────────────────────────────────────────────
  const [schedules, setSchedules]     = useState([]);
  const [pathway, setPathway]         = useState(null);   // from /pathway-info
  const [loadingPathway, setLoadingPathway] = useState(true);
  const [loadingSched, setLoadingSched]    = useState(true);
  const [saving, setSaving]           = useState(false);
  const [msg, setMsg]                 = useState(null);

  // editable draft before saving
  const [draftItems, setDraftItems]   = useState([]);

  // inline reschedule
  const [editingId, setEditingId]     = useState(null);
  const [editDt, setEditDt]           = useState("");
  const [editTm, setEditTm]           = useState("");

  // add single call
  const [showAddForm, setShowAddForm] = useState(false);
  const [newDate, setNewDate]         = useState("");
  const [newTime, setNewTime]         = useState("10:00");
  const [addingSingle, setAddingSingle] = useState(false);

  // ── load pathway info + existing schedules ────────────────────────────────
  async function loadSchedules() {
    setLoadingSched(true);
    try { setSchedules(await getPatientSchedule(patientId)); } catch {}
    setLoadingSched(false);
  }

  useEffect(() => {
    async function init() {
      setLoadingPathway(true);
      try {
        const pw = await getPatientPathwayInfo(patientId);
        setPathway(pw);

        // Auto-generate draft if pathway exists and no schedules yet
        if (pw.has_pathway && pw.call_days?.length) {
          const existing = await getPatientSchedule(patientId);
          setSchedules(existing);
          setLoadingSched(false);

          if (existing.length === 0 && pw.discharge_date) {
            const time = pw.default_call_time || "10:00";
            setDraftItems(
              pw.call_days.map((day, i) => ({
                call_number: i + 1,
                label: `Call ${i + 1} — Day ${day}`,
                date: addDays(pw.discharge_date, day),
                time,
              }))
            );
          }
        } else {
          await loadSchedules();
        }
      } catch {
        await loadSchedules();
      }
      setLoadingPathway(false);
    }
    init();
  }, [patientId]);

  // ── draft helpers ─────────────────────────────────────────────────────────
  function updateDraftItem(idx, field, value) {
    setDraftItems((prev) => prev.map((item, i) => i === idx ? { ...item, [field]: value } : item));
  }
  function removeDraftItem(idx) {
    setDraftItems((prev) => prev.filter((_, i) => i !== idx));
  }

  // ── save ──────────────────────────────────────────────────────────────────
  async function handleSave() {
    if (!draftItems.length) return;
    setSaving(true);
    setMsg(null);
    try {
      await bulkCreateSchedule(patientId, {
        protocol_name: pathway?.pathway_label || "standard",
        module: pathway?.module || "post_discharge",
        items: draftItems.map((item) => ({
          scheduled_for: toISO(item.date, item.time),
          call_number: item.call_number,
        })),
      });
      setMsg({ type: "ok", text: `${draftItems.length} calls scheduled.` });
      setDraftItems([]);
      await loadSchedules();
    } catch {
      setMsg({ type: "err", text: "Failed to save schedule." });
    }
    setSaving(false);
  }

  // ── cancel / reschedule / delete ──────────────────────────────────────────
  async function handleCancel(scheduleId) {
    try {
      await updateSchedule(patientId, scheduleId, { status: "cancelled" });
      await loadSchedules();
    } catch {
      setMsg({ type: "err", text: "Failed to cancel." });
    }
  }

  function startEdit(s) {
    const d = new Date(s.scheduled_for);
    setEditingId(s.schedule_id);
    setEditDt(d.toISOString().slice(0, 10));
    setEditTm(d.toTimeString().slice(0, 5));
  }

  async function saveEdit(scheduleId) {
    try {
      await updateSchedule(patientId, scheduleId, {
        scheduled_for: toISO(editDt, editTm),
      });
      setEditingId(null);
      await loadSchedules();
    } catch {
      setMsg({ type: "err", text: "Failed to reschedule." });
    }
  }

  async function handleAddSingle() {
    if (!newDate || !newTime) return;
    setAddingSingle(true);
    setMsg(null);
    try {
      await bulkCreateSchedule(patientId, {
        protocol_name: pathway?.pathway_label || "standard",
        module: pathway?.module || "post_discharge",
        items: [{ scheduled_for: toISO(newDate, newTime), call_number: schedules.length + 1 }],
      });
      setShowAddForm(false);
      setNewDate("");
      setNewTime("10:00");
      setMsg({ type: "ok", text: "Call added to schedule." });
      await loadSchedules();
    } catch {
      setMsg({ type: "err", text: "Failed to add call." });
    }
    setAddingSingle(false);
  }

  async function handleDelete(scheduleId) {
    try {
      await deleteSchedule(patientId, scheduleId);
      await loadSchedules();
    } catch {
      setMsg({ type: "err", text: "Failed to delete." });
    }
  }

  // ── split ─────────────────────────────────────────────────────────────────
  const upcoming = schedules.filter((s) => ["pending", "dispatched"].includes(s.status));
  const past     = schedules.filter((s) => ["completed", "missed", "cancelled"].includes(s.status));

  // ── loading state ─────────────────────────────────────────────────────────
  if (loadingPathway) {
    return <p className="text-sm text-gray-400 py-8 text-center">Loading pathway…</p>;
  }

  // ── no pathway registered ─────────────────────────────────────────────────
  if (!pathway?.has_pathway) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 px-5 py-8 text-center">
        <p className="text-sm text-gray-500">No clinical pathway registered for this patient.</p>
        <p className="text-xs text-gray-400 mt-1">
          Register the patient via <strong>Pathway Register</strong> to enable scheduling.
        </p>
      </div>
    );
  }

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">

      {/* Feedback */}
      {msg && (
        <div className={`flex items-center justify-between text-sm rounded-xl px-4 py-2.5 border ${
          msg.type === "ok"
            ? "bg-green-50 border-green-200 text-green-800"
            : "bg-red-50 border-red-200 text-red-700"
        }`}>
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} className="ml-4 opacity-60 hover:opacity-100">✕</button>
        </div>
      )}

      {/* ── Pathway banner ─────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 px-5 py-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-nhs-blue/10 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-nhs-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-800">{pathway.pathway_label}</div>
          <div className="text-xs text-gray-400">
            {pathway.call_days.length} calls · discharge {fmtDate(pathway.discharge_date)}
            {" · "}days {pathway.call_days.join(", ")}
          </div>
        </div>
      </div>

      {/* ── Draft list (shown before saving) ───────────────────────────── */}
      {draftItems.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Generated Schedule</h2>
            <span className="text-xs text-gray-400">Adjust times before saving</span>
          </div>
          <div className="px-5 py-4 space-y-2">
            {draftItems.map((item, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                <span className="w-6 h-6 rounded-full bg-nhs-blue/10 text-nhs-blue text-[10px] font-bold flex items-center justify-center shrink-0">
                  {item.call_number}
                </span>
                <span className="text-xs text-gray-600 flex-1 min-w-0 truncate">{item.label}</span>
                <input
                  type="date"
                  value={item.date}
                  onChange={(e) => updateDraftItem(idx, "date", e.target.value)}
                  className="text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30"
                />
                <input
                  type="time"
                  value={item.time}
                  onChange={(e) => updateDraftItem(idx, "time", e.target.value)}
                  className="text-xs border border-gray-200 rounded px-2 py-1 w-20 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30"
                />
                <button
                  onClick={() => removeDraftItem(idx)}
                  className="text-gray-300 hover:text-red-400 text-sm leading-none"
                  title="Remove"
                >✕</button>
              </div>
            ))}

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-gray-400">{draftItems.length} calls · auto-generated from {pathway.pathway_label}</span>
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-sm font-semibold px-5 py-2 rounded-lg bg-nhs-blue text-white hover:bg-nhs-blue-light disabled:opacity-50 transition"
              >
                {saving ? "Saving…" : "Confirm Schedule"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Upcoming calls ──────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">
            Upcoming Calls
            {upcoming.length > 0 && (
              <span className="ml-2 px-1.5 py-0.5 rounded-full bg-nhs-blue/10 text-nhs-blue text-[10px] font-bold">
                {upcoming.length}
              </span>
            )}
          </h2>
          <button
            onClick={() => { setShowAddForm((v) => !v); setNewDate(""); setNewTime("10:00"); }}
            className="text-xs font-semibold text-nhs-blue border border-nhs-blue/30 px-3 py-1 rounded-lg hover:bg-nhs-blue hover:text-white transition"
          >
            + Add Call
          </button>
        </div>

        {/* Add call form */}
        {showAddForm && (
          <div className="px-5 py-3 border-b border-gray-100 bg-blue-50 flex items-center gap-3 flex-wrap">
            <span className="text-xs font-semibold text-gray-600">New call:</span>
            <input
              type="date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30 bg-white"
            />
            <input
              type="time"
              value={newTime}
              onChange={(e) => setNewTime(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1.5 w-24 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30 bg-white"
            />
            <button
              onClick={handleAddSingle}
              disabled={addingSingle || !newDate}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-nhs-blue text-white hover:bg-nhs-blue-light disabled:opacity-50 transition"
            >
              {addingSingle ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => setShowAddForm(false)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >Cancel</button>
          </div>
        )}

        <div className="px-5 py-4">
          {loadingSched ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : upcoming.length === 0 ? (
            <p className="text-sm text-gray-400">
              {draftItems.length > 0
                ? "Review and confirm the generated schedule above."
                : "No upcoming calls — use + Add Call or confirm the generated schedule."}
            </p>
          ) : (
            <div className="relative">
              <div className="absolute left-[18px] top-0 bottom-0 w-px bg-gray-100" />
              <div className="space-y-1">
                {upcoming.map((s, i) => (
                  <div key={s.schedule_id}>
                    {editingId === s.schedule_id ? (
                      <div className="ml-10 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 flex items-center gap-2 flex-wrap">
                        <input
                          type="date"
                          value={editDt}
                          onChange={(e) => setEditDt(e.target.value)}
                          className="text-xs border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30 bg-white"
                        />
                        <input
                          type="time"
                          value={editTm}
                          onChange={(e) => setEditTm(e.target.value)}
                          className="text-xs border border-gray-200 rounded px-2 py-1.5 w-24 focus:outline-none focus:ring-1 focus:ring-nhs-blue/30 bg-white"
                        />
                        <button
                          onClick={() => saveEdit(s.schedule_id)}
                          className="text-xs font-semibold text-white bg-nhs-blue px-3 py-1.5 rounded-lg hover:bg-nhs-blue-light"
                        >Save</button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="text-xs text-gray-400 hover:text-gray-600"
                        >Cancel</button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 py-2">
                        <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0 z-10 ${
                          i === 0
                            ? "bg-nhs-blue border-nhs-blue text-white"
                            : "bg-white border-gray-200 text-gray-500"
                        }`}>
                          {s.call_number ?? i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-semibold text-gray-800">{fmtDate(s.scheduled_for)}</span>
                            <span className="text-xs text-gray-400">{fmtTime(s.scheduled_for)}</span>
                            {s.call_number != null && (
                              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200">
                                Day {s.call_number}
                              </span>
                            )}
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[s.status] ?? STATUS_STYLES.pending}`}>
                              {s.status}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => startEdit(s)}
                            className="text-[11px] px-2 py-1 rounded border border-gray-200 text-gray-500 hover:border-nhs-blue hover:text-nhs-blue transition"
                          >Edit</button>
                          <button
                            onClick={() => handleCancel(s.schedule_id)}
                            className="text-[11px] px-2 py-1 rounded border border-gray-200 text-gray-500 hover:border-red-300 hover:text-red-500 transition"
                          >Cancel</button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Past calls ──────────────────────────────────────────────────── */}
      {past.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-gray-100">
            <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Past Calls</h2>
          </div>
          <div className="px-5 py-4 space-y-1">
            {past.map((s, i) => (
              <div key={s.schedule_id} className="flex items-center gap-3 py-2">
                <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0 ${
                  s.status === "completed" ? "bg-green-50 border-green-300 text-green-700"
                  : s.status === "missed"  ? "bg-red-50 border-red-300 text-red-500"
                  : "bg-gray-50 border-gray-200 text-gray-400"
                }`}>
                  {s.call_number ?? i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-gray-700">{fmtDate(s.scheduled_for)}</span>
                    <span className="text-xs text-gray-400">{fmtTime(s.scheduled_for)}</span>
                    {s.call_number != null && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200">
                        Day {s.call_number}
                      </span>
                    )}
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[s.status] ?? STATUS_STYLES.cancelled}`}>
                      {s.status}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(s.schedule_id)}
                  className="text-[11px] text-gray-300 hover:text-red-400 transition"
                  title="Remove"
                >✕</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

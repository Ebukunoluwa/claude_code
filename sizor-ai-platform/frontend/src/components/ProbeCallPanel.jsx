import { useState, useEffect, useRef, useCallback } from "react";
import { createProbeCall, getPatientProbeCalls } from "../api/probe_calls";

const SLOTS = [
  { id: "immediate", label: "Now", sub: "Fire immediately" },
  { id: "morning",   label: "Tomorrow Morning", sub: "9:00 – 11:00 am" },
  { id: "afternoon", label: "Tomorrow Afternoon", sub: "1:00 – 4:00 pm" },
];

const STATUS_STYLES = {
  pending:   { dot: "bg-amber-400",  text: "text-amber-700",  bg: "bg-amber-50",  border: "border-amber-200",  label: "Pending" },
  initiated: { dot: "bg-blue-400",   text: "text-blue-700",   bg: "bg-blue-50",   border: "border-blue-200",   label: "In Progress" },
  completed: { dot: "bg-green-400",  text: "text-green-700",  bg: "bg-green-50",  border: "border-green-200",  label: "Completed" },
  failed:    { dot: "bg-red-400",    text: "text-red-700",    bg: "bg-red-50",    border: "border-red-200",    label: "Failed" },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border ${s.bg} ${s.border} ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${status === "initiated" ? "animate-pulse" : ""}`} />
      {s.label}
    </span>
  );
}

function ProbeCallRow({ pc, onRefresh }) {
  const date = new Date(pc.scheduled_time);
  const label = date.toLocaleString("en-GB", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5">
          <div className="text-xs font-semibold text-gray-700 line-clamp-2">{pc.note}</div>
          <div className="text-[10px] text-gray-400">{label}</div>
        </div>
        <StatusBadge status={pc.status} />
      </div>

      {pc.needs_manual_review && (
        <div className="flex items-center gap-1.5 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1">
          <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          Prompt generated from raw note — manual review recommended
        </div>
      )}

      {pc.soap_note && (
        <details className="rounded-lg border border-green-100 overflow-hidden">
          <summary className="px-3 py-1.5 text-[10px] font-semibold text-green-700 bg-green-50 cursor-pointer hover:bg-green-100 transition flex items-center gap-1.5">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            View SOAP Note
          </summary>
          <div className="p-3 space-y-1.5 bg-white text-xs text-gray-700">
            {[
              { key: "subjective",  label: "S", color: "bg-blue-100 text-blue-700" },
              { key: "objective",   label: "O", color: "bg-slate-100 text-slate-700" },
              { key: "assessment",  label: "A", color: "bg-amber-100 text-amber-700" },
              { key: "plan",        label: "P", color: "bg-green-100 text-green-700" },
            ].map(({ key, label, color }) => (
              <div key={key} className="flex gap-2">
                <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5 ${color}`}>{label}</span>
                <span className="leading-relaxed">{pc.soap_note[key]}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {pc.status === "completed" && !pc.soap_note && (
        <button
          onClick={onRefresh}
          className="text-[10px] text-purple-600 hover:text-purple-800 font-semibold flex items-center gap-1 transition"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh for SOAP note
        </button>
      )}
    </div>
  );
}

export default function ProbeCallPanel({ patientId }) {
  const [note, setNote]             = useState("");
  const [slot, setSlot]             = useState("immediate");
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [saved, setSaved]           = useState(false);
  const [probeCalls, setProbeCalls] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const debounceRef = useRef(null);

  const loadProbeCalls = useCallback(async () => {
    try {
      const data = await getPatientProbeCalls(patientId);
      setProbeCalls(data);
    } catch {
      // silently fail
    } finally {
      setListLoading(false);
    }
  }, [patientId]);

  useEffect(() => { loadProbeCalls(); }, [loadProbeCalls]);

  // Auto-save draft to localStorage with 500ms debounce
  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!note) { setSaved(false); return; }
    debounceRef.current = setTimeout(() => {
      localStorage.setItem(`probe_draft_${patientId}`, note);
      setSaved(true);
    }, 500);
    return () => clearTimeout(debounceRef.current);
  }, [note, patientId]);

  // Restore draft on mount
  useEffect(() => {
    const draft = localStorage.getItem(`probe_draft_${patientId}`);
    if (draft) setNote(draft);
  }, [patientId]);

  async function handleSchedule() {
    if (!note.trim()) return;
    setLoading(true);
    setError("");
    try {
      await createProbeCall({ patient_id: patientId, note: note.trim(), slot });
      localStorage.removeItem(`probe_draft_${patientId}`);
      setNote("");
      setSaved(false);
      await loadProbeCalls();
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to schedule probe call.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Note composer */}
      <div className="space-y-2">
        <div className="relative">
          <textarea
            rows={3}
            value={note}
            onChange={(e) => { setNote(e.target.value); setSaved(false); }}
            placeholder="Describe the concern or question you want the AI agent to probe…"
            className="w-full resize-none text-sm border border-gray-200 rounded-xl px-3 py-2.5 bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-400 transition"
          />
          {saved && (
            <span className="absolute bottom-2 right-2 text-[10px] text-gray-400 flex items-center gap-1">
              <svg className="w-3 h-3 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Draft saved
            </span>
          )}
        </div>

        {/* Time slot picker */}
        <div className="grid grid-cols-3 gap-1.5">
          {SLOTS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSlot(s.id)}
              className={`text-left rounded-xl border px-2.5 py-2 transition ${
                slot === s.id
                  ? "border-purple-400 bg-purple-50 ring-1 ring-purple-400/30"
                  : "border-gray-200 bg-gray-50 hover:border-gray-300 hover:bg-gray-100"
              }`}
            >
              <div className={`text-[11px] font-bold leading-none ${slot === s.id ? "text-purple-700" : "text-gray-700"}`}>
                {s.label}
              </div>
              <div className={`text-[10px] mt-0.5 leading-none ${slot === s.id ? "text-purple-500" : "text-gray-400"}`}>
                {s.sub}
              </div>
            </button>
          ))}
        </div>

        {error && (
          <div className="text-[11px] text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          onClick={handleSchedule}
          disabled={!note.trim() || loading}
          className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white text-xs font-semibold py-2 rounded-xl transition"
        >
          {loading ? (
            <>
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Generating prompt & scheduling…
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              Schedule Probe Call
            </>
          )}
        </button>
      </div>

      {/* History */}
      {listLoading ? (
        <div className="text-[11px] text-gray-400 text-center py-2">Loading…</div>
      ) : probeCalls.length > 0 ? (
        <div className="space-y-2">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Previous Probe Calls</div>
          {probeCalls.map((pc) => (
            <ProbeCallRow key={pc.probe_call_id} pc={pc} onRefresh={loadProbeCalls} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

import { useEffect, useState } from "react";
import client from "../api/client";

const SOAP_SECTION_LABELS = {
  subjective: { label: "S — Subjective", description: "What the patient reported", color: "border-blue-300 bg-blue-50" },
  objective: { label: "O — Objective", description: "Scored observations", color: "border-purple-300 bg-purple-50" },
  assessment: { label: "A — Assessment", description: "Clinical interpretation", color: "border-amber-300 bg-amber-50" },
  plan: { label: "P — Plan", description: "Actions and follow-up", color: "border-green-300 bg-green-50" },
};

const ESCALATION_TIER_STYLES = {
  "999": "bg-red-600 text-white border-red-700",
  same_day: "bg-orange-500 text-white border-orange-600",
  urgent_gp: "bg-amber-500 text-white border-amber-600",
  next_call: "bg-blue-500 text-white border-blue-600",
};

const ESCALATION_TIER_LABELS = {
  "999": "EMERGENCY — Call 999",
  same_day: "Same-day review required",
  urgent_gp: "Urgent GP review",
  next_call: "Review at next call",
};

function SoapSection({ sectionKey, content }) {
  const meta = SOAP_SECTION_LABELS[sectionKey];
  if (!content && !meta) return null;
  return (
    <div className={`rounded-lg border-l-4 p-3 ${meta?.color || "border-gray-300 bg-gray-50"}`}>
      <div className="text-xs font-bold uppercase tracking-wide text-[var(--color-text-secondary,#6b7280)] mb-1">
        {meta?.label || sectionKey}
        {meta?.description && (
          <span className="ml-1 font-normal normal-case tracking-normal text-gray-400">
            — {meta.description}
          </span>
        )}
      </div>
      <p className="text-sm text-[var(--color-text,#111827)] whitespace-pre-wrap leading-relaxed">
        {content || <span className="italic text-gray-400">Not recorded</span>}
      </p>
    </div>
  );
}

function DomainNote({ note }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="rounded-xl border border-[var(--color-border,#e5e7eb)] bg-[var(--color-surface,#fff)] overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--color-surface-secondary,#f9fafb)] transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-sm capitalize text-[var(--color-text,#111827)]">
            {note.domain.replace(/_/g, " ")}
          </span>
          {note.nice_reference && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-700 font-medium">
              {note.nice_reference}
            </span>
          )}
          {note.escalation_action && (
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded border font-bold ${
                ESCALATION_TIER_STYLES[note.escalation_tier] || "bg-red-100 text-red-800 border-red-300"
              }`}
            >
              {ESCALATION_TIER_LABELS[note.escalation_tier] || "Escalation required"}
            </span>
          )}
        </div>
        <span className="text-gray-400 text-xs ml-2">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-2 border-t border-[var(--color-border,#e5e7eb)]">
          <div className="pt-3 space-y-2">
            {["subjective", "objective", "assessment", "plan"].map((section) => (
              <SoapSection key={section} sectionKey={section} content={note[section]} />
            ))}
          </div>

          {note.escalation_action && (
            <div
              className={`mt-2 p-3 rounded-lg border font-medium text-sm ${
                ESCALATION_TIER_STYLES[note.escalation_tier] || "bg-red-100 text-red-800 border-red-300"
              }`}
            >
              <span className="font-bold block text-xs uppercase tracking-wide mb-0.5">
                {ESCALATION_TIER_LABELS[note.escalation_tier] || "Escalation Action"}
              </span>
              {note.escalation_action}
            </div>
          )}

          {note.created_at && (
            <p className="text-[10px] text-gray-400 text-right mt-1">
              Recorded {new Date(note.created_at).toLocaleString("en-GB")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * SoapNoteViewer
 *
 * Props:
 *   callId  {string}  Call UUID — fetches SOAP notes via GET /api/calls/:callId/soap
 */
export default function SoapNoteViewer({ callId }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!callId) return;
    setLoading(true);
    setError(null);
    client
      .get(`/calls/${callId}/soap`)
      .then((r) => {
        const data = Array.isArray(r.data) ? r.data : [r.data];
        setNotes(data);
      })
      .catch((e) => setError(e.response?.data?.detail || "Failed to load SOAP notes"))
      .finally(() => setLoading(false));
  }, [callId]);

  function exportAsText() {
    if (!notes.length) return;
    const lines = [];
    for (const note of notes) {
      lines.push(`Domain: ${note.domain.replace(/_/g, " ")}`);
      if (note.nice_reference) lines.push(`NICE: ${note.nice_reference}`);
      if (note.subjective) lines.push(`S: ${note.subjective}`);
      if (note.objective) lines.push(`O: ${note.objective}`);
      if (note.assessment) lines.push(`A: ${note.assessment}`);
      if (note.plan) lines.push(`P: ${note.plan}`);
      if (note.escalation_action) lines.push(`ESCALATION: ${note.escalation_action}`);
      lines.push("");
    }
    const text = lines.join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `soap_notes_call_${callId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!callId) {
    return (
      <div className="p-4 text-sm text-[var(--color-text-secondary,#6b7280)]">
        Select a call to view SOAP notes.
      </div>
    );
  }

  const escalatingNotes = notes.filter((n) => n.escalation_action);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text,#111827)]">
            SOAP Notes
          </h3>
          {notes.length > 0 && (
            <p className="text-xs text-[var(--color-text-secondary,#6b7280)] mt-0.5">
              {notes.length} domain{notes.length !== 1 ? "s" : ""} recorded
              {escalatingNotes.length > 0 && (
                <span className="ml-2 text-red-600 font-semibold">
                  · {escalatingNotes.length} escalation{escalatingNotes.length !== 1 ? "s" : ""}
                </span>
              )}
            </p>
          )}
        </div>
        {notes.length > 0 && (
          <button
            type="button"
            onClick={exportAsText}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--color-border,#e5e7eb)] text-[var(--color-text-secondary,#6b7280)] hover:bg-[var(--color-surface-secondary,#f9fafb)] transition-colors"
          >
            Export as text
          </button>
        )}
      </div>

      {/* Escalation summary banner */}
      {escalatingNotes.length > 0 && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200">
          <p className="text-xs font-bold text-red-800 uppercase tracking-wide mb-1">
            Escalation actions required
          </p>
          <ul className="text-xs text-red-700 space-y-0.5 list-disc list-inside">
            {escalatingNotes.map((n) => (
              <li key={n.domain || n.id}>
                <span className="capitalize">{n.domain.replace(/_/g, " ")}</span>
                {" — "}
                <span className="font-medium">
                  {ESCALATION_TIER_LABELS[n.escalation_tier] || n.escalation_tier}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 py-6">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-500">Loading SOAP notes…</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && notes.length === 0 && (
        <div className="py-8 text-center">
          <p className="text-sm text-gray-500">No SOAP notes recorded for this call.</p>
        </div>
      )}

      {!loading && !error && notes.map((note, i) => (
        <DomainNote key={note.id || i} note={note} />
      ))}
    </div>
  );
}

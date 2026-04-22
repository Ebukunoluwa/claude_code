/**
 * ProbeCallPanel — full Probe Scheduler page (replaces old embedded panel).
 * Rendered by /scheduler route. Wired to src/api/probe_calls.js.
 */
import { useEffect, useState } from "react";
import { createProbeCall } from "../api/probe_calls";
import { getDashboard } from "../api/decisions";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Layout from "./Layout";

function toRag(severity) {
  if (severity === "red")   return "RED";
  if (severity === "amber") return "AMBER";
  return "GREEN";
}

const TIMES = [
  "08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30",
  "14:00","14:30","15:00","15:30","16:00","16:30",
];

const REASONS = [
  "Routine Check-in",
  "FTP Follow-up",
  "Pain Review",
  "Medication Query",
  "Respiratory Check",
  "Wound Concern",
  "Escalation Follow-up",
  "Discharge Planning",
];

export default function ProbeCallPanel() {
  const { t } = useTheme();

  /* Patient list */
  const [patients, setPatients]     = useState([]);
  const [search, setSearch]         = useState("");
  const [selP, setSelP]             = useState(null);

  /* Schedule form */
  const [selDate, setSelDate]       = useState("tomorrow");
  const [customDate, setCustomDate] = useState("");
  const [selTime, setSelTime]       = useState("08:00");
  const [selReason, setSelReason]   = useState("Routine Check-in");
  const [notes, setNotes]           = useState("");

  /* Queue preview */
  const [queue, setQueue]           = useState([]);

  /* UI state */
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess]       = useState(false);
  const [error, setError]           = useState("");

  /* Load patients from dashboard worklist (has patient_name + urgency_severity) */
  useEffect(() => {
    getDashboard()
      .then((data) => {
        const list = data.worklist || [];
        setPatients(list);
        if (list.length > 0 && !selP) setSelP(list[0]);
      })
      .catch(() => {});
  }, []);

  /* Load today's call queue */
  useEffect(() => {
    getDashboard()
      .then((data) => {
        const items = (data.worklist || [])
          .filter((p) => p.next_scheduled_call)
          .sort((a, b) => new Date(a.next_scheduled_call) - new Date(b.next_scheduled_call))
          .slice(0, 5)
          .map((p) => ({
            id: p.patient_id,
            patient: p.patient_name,
            time: new Date(p.next_scheduled_call).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
            date: new Date(p.next_scheduled_call).toDateString() === new Date().toDateString() ? "Today" : "Tomorrow",
            type: p.condition || "Routine",
            rag: toRag(p.urgency_severity),
          }));
        setQueue(items);
      })
      .catch(() => {});
  }, []);

  const filteredPatients = patients.filter((p) => {
    const q = search.toLowerCase();
    return (
      (p.patient_name  || "").toLowerCase().includes(q) ||
      (p.patient_id    || "").toLowerCase().includes(q) ||
      (p.nhs_number    || "").toLowerCase().includes(q) ||
      (p.condition     || "").toLowerCase().includes(q)
    );
  });

  const cfg = selP ? ragCfg(t, toRag(selP.urgency_severity)) : ragCfg(t, "GREEN");

  async function handleSchedule() {
    if (!selP) return;
    setSubmitting(true);
    setError("");
    try {
      // Build scheduled_time from selected date + time
      let base;
      if (selDate === "custom" && customDate) {
        base = new Date(customDate);
      } else {
        base = new Date();
        if (selDate === "tomorrow") base.setDate(base.getDate() + 1);
      }
      const [h, m] = selTime.split(":").map(Number);
      base.setHours(h, m, 0, 0);

      await createProbeCall({
        patient_id:     selP.patient_id,
        note:           notes.trim() || selReason,
        slot:           selDate === "today" ? "immediate" : "morning",
        scheduled_time: base.toISOString(),
      });
      setSuccess(true);
      setNotes("");
      setTimeout(() => setSuccess(false), 3500);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to schedule probe call.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.brand, letterSpacing: "2px", marginBottom: 8 }}>
            CLINICIAN-INITIATED · OUTBOUND CALL
          </div>
          <h1 style={{ fontFamily: "'Outfit',sans-serif", fontSize: 32, fontWeight: 900, color: t.textPrimary, letterSpacing: "-0.8px" }}>
            Schedule a Probe Call
          </h1>
        </div>

        {/* Success banner */}
        {success && (
          <div style={{ padding: "14px 20px", borderRadius: 12, background: t.greenBg, border: "1px solid " + t.greenBorder, marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ color: t.green, fontSize: 18 }}>✓</span>
            <span style={{ fontFamily: "'Outfit',sans-serif", fontSize: 14, color: t.green, fontWeight: 600 }}>
              Probe call scheduled — Sizor will call {selP?.patient_name} at {selTime}
            </span>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 330px", gap: 20 }}>
          {/* ── Left column: 3-step form ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Step 1 — Select patient */}
            <div style={{ background: t.surface, border: "1px solid " + t.border, borderRadius: 16, padding: 22, boxShadow: "0 2px 12px " + t.shadow }}>
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1.5px", marginBottom: 14 }}>STEP 1 · SELECT PATIENT</div>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search patient…"
                style={{ width: "100%", padding: "10px 14px", borderRadius: 9, background: t.bg, border: "1px solid " + t.border, fontFamily: "'Outfit',sans-serif", fontSize: 14, color: t.textPrimary, marginBottom: 10, outline: "none", boxSizing: "border-box" }}
              />
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {filteredPatients.slice(0, 8).map((p) => {
                  const rag  = toRag(p.urgency_severity);
                  const pcfg = ragCfg(t, rag);
                  const isSel = selP?.patient_id === p.patient_id;
                  return (
                    <div
                      key={p.patient_id}
                      onClick={() => setSelP(p)}
                      style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 14px", borderRadius: 9, cursor: "pointer", background: isSel ? pcfg.bg : t.surfaceHigh, border: "1px solid " + (isSel ? pcfg.border : t.border), transition: "all 0.15s" }}
                    >
                      <div>
                        <div style={{ fontFamily: "'Outfit',sans-serif", fontWeight: 700, fontSize: 14, color: t.textPrimary }}>
                          {p.patient_name || "Unknown Patient"}
                        </div>
                        <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted }}>
                          {p.nhs_number ? "NHS " + p.nhs_number + " · " : ""}{p.condition || "General"}
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: pcfg.text, fontWeight: 600 }}>{rag}</span>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: pcfg.dot, display: "inline-block" }} />
                      </div>
                    </div>
                  );
                })}
                {filteredPatients.length === 0 && (
                  <div style={{ fontFamily: "'Outfit',sans-serif", fontSize: 13, color: t.textMuted, padding: "8px 0", textAlign: "center" }}>No patients found.</div>
                )}
              </div>
            </div>

            {/* Step 2 — Date & time */}
            <div style={{ background: t.surface, border: "1px solid " + t.border, borderRadius: 16, padding: 22, boxShadow: "0 2px 12px " + t.shadow }}>
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1.5px", marginBottom: 14 }}>STEP 2 · DATE & TIME</div>
              {/* Today / Tomorrow / Custom toggle */}
              <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
                {[["today","Today"],["tomorrow","Tomorrow"],["custom","Custom"]].map(([v, l]) => (
                  <button
                    key={v}
                    onClick={() => setSelDate(v)}
                    style={{ flex: 1, padding: 9, borderRadius: 9, cursor: "pointer", fontFamily: "'Outfit',sans-serif", fontWeight: 600, fontSize: 13, background: selDate === v ? t.brandGlow : t.surfaceHigh, border: "1px solid " + (selDate === v ? t.brand + "40" : t.border), color: selDate === v ? t.brand : t.textMuted, transition: "all 0.15s" }}
                  >{l}</button>
                ))}
              </div>

              {/* Custom date picker */}
              {selDate === "custom" && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1px", marginBottom: 8 }}>SELECT DATE</div>
                  <input
                    type="date"
                    value={customDate}
                    min={new Date().toISOString().split("T")[0]}
                    onChange={(e) => setCustomDate(e.target.value)}
                    style={{ width: "100%", padding: "10px 14px", borderRadius: 9, background: t.bg, border: "1px solid " + (customDate ? t.brand + "60" : t.border), fontFamily: "'DM Mono',monospace", fontSize: 13, color: t.textPrimary, outline: "none", boxSizing: "border-box", colorScheme: "dark" }}
                  />
                </div>
              )}

              {/* Time slots */}
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1px", marginBottom: 8 }}>SELECT TIME</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 6 }}>
                {TIMES.map((tm) => (
                  <button
                    key={tm}
                    onClick={() => setSelTime(tm)}
                    style={{ padding: "8px 3px", borderRadius: 7, cursor: "pointer", fontFamily: "'DM Mono',monospace", fontSize: 11, background: selTime === tm ? t.brandGlow : t.surfaceHigh, border: "1px solid " + (selTime === tm ? t.brand + "40" : t.border), color: selTime === tm ? t.brand : t.textMuted, transition: "all 0.15s" }}
                  >{tm}</button>
                ))}
              </div>
            </div>

            {/* Step 3 — Reason & notes */}
            <div style={{ background: t.surface, border: "1px solid " + t.border, borderRadius: 16, padding: 22, boxShadow: "0 2px 12px " + t.shadow }}>
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1.5px", marginBottom: 14 }}>STEP 3 · REASON & NOTES</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7, marginBottom: 14 }}>
                {REASONS.map((r) => (
                  <button
                    key={r}
                    onClick={() => setSelReason(r)}
                    style={{ padding: "9px 12px", borderRadius: 7, cursor: "pointer", textAlign: "left", fontFamily: "'Outfit',sans-serif", fontWeight: 500, fontSize: 13, background: selReason === r ? t.brandGlow : t.surfaceHigh, border: "1px solid " + (selReason === r ? t.brand + "40" : t.border), color: selReason === r ? t.brand : t.textSecond, transition: "all 0.15s" }}
                  >{r}</button>
                ))}
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional context for AI agent (optional)…"
                rows={3}
                style={{ width: "100%", padding: "11px 14px", borderRadius: 9, background: t.bg, border: "1px solid " + t.border, fontFamily: "'Outfit',sans-serif", fontSize: 13, color: t.textPrimary, resize: "none", lineHeight: 1.6, outline: "none", boxSizing: "border-box" }}
              />
            </div>

            {/* Error */}
            {error && (
              <div style={{ padding: "12px 16px", borderRadius: 10, background: t.redBg, border: "1px solid " + t.redBorder, fontFamily: "'Outfit',sans-serif", fontSize: 13, color: t.red }}>{error}</div>
            )}

            {/* Submit */}
            <button
              onClick={handleSchedule}
              disabled={!selP || submitting}
              onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-2px)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; }}
              style={{ padding: 15, borderRadius: 12, background: "linear-gradient(135deg,#0AAFA8,#076E69)", border: "none", color: "#fff", fontFamily: "'Outfit',sans-serif", fontWeight: 800, fontSize: 15, cursor: selP ? "pointer" : "not-allowed", boxShadow: "0 8px 32px #0AAFA840", transition: "all 0.2s", opacity: selP ? 1 : 0.5 }}
            >
              {submitting ? "Scheduling…" : `◎  Schedule Probe Call${selP ? " for " + selP.patient_name : ""}`}
            </button>
          </div>

          {/* ── Right column: call preview + queue ── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Call preview card */}
            <div style={{ background: cfg.bg, border: "1px solid " + cfg.border, borderRadius: 16, padding: 22, boxShadow: cfg.glow, position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: "linear-gradient(90deg,transparent," + cfg.dot + ",transparent)" }} />
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1.5px", marginBottom: 14 }}>CALL PREVIEW</div>
              {selP ? (
                <>
                  <div style={{ fontFamily: "'Outfit',sans-serif", fontWeight: 800, fontSize: 18, color: t.textPrimary, marginBottom: 3 }}>
                    {selP.patient_name || "Unknown Patient"}
                  </div>
                  <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, marginBottom: 14 }}>
                    {selP.patient_id} · {selP.condition || "General"}
                  </div>
                  {[
                    ["Date",   selDate === "today" ? "Today" : selDate === "tomorrow" ? "Tomorrow" : customDate || "Pick a date"],
                    ["Time",   selTime],
                    ["Reason", selReason],
                    ["RAG",    toRag(selP.urgency_severity)],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid " + t.border + "80" }}>
                      <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted }}>{k.toUpperCase()}</span>
                      <span style={{ fontFamily: "'Outfit',sans-serif", fontSize: 13, color: k === "RAG" ? cfg.text : t.textSecond, fontWeight: 600 }}>{v}</span>
                    </div>
                  ))}
                </>
              ) : (
                <div style={{ fontFamily: "'Outfit',sans-serif", fontSize: 13, color: t.textMuted, padding: "8px 0" }}>Select a patient above.</div>
              )}
            </div>

            {/* Upcoming queue */}
            <div style={{ background: t.surface, border: "1px solid " + t.border, borderRadius: 16, padding: 18, boxShadow: "0 2px 12px " + t.shadow }}>
              <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 10, color: t.textMuted, letterSpacing: "1.5px", marginBottom: 12 }}>CALL QUEUE · NEXT 24H</div>
              {queue.length === 0 ? (
                <div style={{ fontFamily: "'Outfit',sans-serif", fontSize: 13, color: t.textMuted }}>No calls scheduled.</div>
              ) : queue.map((q) => {
                const qcfg = ragCfg(t, q.rag);
                return (
                  <div key={q.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: 10, borderRadius: 9, background: t.surfaceHigh, border: "1px solid " + t.border, marginBottom: 8 }}>
                    <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 12, color: t.brand, width: 40, flexShrink: 0 }}>{q.time}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontFamily: "'Outfit',sans-serif", fontWeight: 600, fontSize: 13, color: t.textPrimary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{q.patient}</div>
                      <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 9, color: t.textMuted }}>{q.date} · {q.type}</div>
                    </div>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: qcfg.dot, display: "inline-block" }} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  getPatient, getPatientCalls, getPatientTrends,
  getPatientDecisions, actionNote, actionProbe,
  actionEscalate, resolveFlag,
} from "../api/patients";
import { getCall, reviewCall } from "../api/calls";
import { createDecision, getDecision, respondToDecision } from "../api/decisions";
import { getMe } from "../api/auth";
import UrgencyBadge from "../components/UrgencyBadge";
import FTPBadge from "../components/FTPBadge";
import Layout from "../components/Layout";
import PatientChat from "../components/PatientChat";
import { formatDateTime, formatDate, formatDuration } from "../utils/timezone";
import { NHS_BLUE, NHS_GREEN, NHS_AMBER, NHS_RED } from "../utils/colors";

const DOMAIN_COLORS = {
  pain: NHS_RED,
  breathlessness: NHS_AMBER,
  mobility: NHS_BLUE,
  appetite: "#8B5CF6",
  mood: NHS_GREEN,
};

const DOMAIN_ICONS = {
  pain: "🔴",
  breathlessness: "💨",
  mobility: "🚶",
  appetite: "🍽",
  mood: "😊",
};

function ScoreRing({ value, label, color }) {
  const max = 10;
  const r = 22;
  const circ = 2 * Math.PI * r;
  const offset = circ - (circ * (value ?? 0)) / max;
  const isHigh = label === "Pain" || label === "Breathless";
  const warn = isHigh ? value >= 6 : value !== null && value <= 3;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-14 h-14">
        <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
          <circle cx="28" cy="28" r={r} stroke="#f1f5f9" strokeWidth="5" fill="none" />
          <circle
            cx="28" cy="28" r={r}
            stroke={warn ? (isHigh ? "#ef4444" : "#f59e0b") : color}
            strokeWidth="5"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gray-800">
          {value ?? "—"}
        </span>
      </div>
      <span className="text-[10px] text-gray-500 font-medium">{label}</span>
    </div>
  );
}

function Section({ title, children, action }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest">{title}</h2>
        {action}
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

export default function PatientPage() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);
  const [clinician, setClinician] = useState(null);
  const [calls, setCalls] = useState([]);
  const [trends, setTrends] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [selectedCall, setSelectedCall] = useState(null);
  const [callDetail, setCallDetail] = useState(null);
  const [callDecision, setCallDecision] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTranscript, setShowTranscript] = useState(false);

  const [noteText, setNoteText] = useState("");
  const [probeInstructions, setProbeInstructions] = useState("");
  const [escalateNote, setEscalateNote] = useState("");
  const [decisionQuestion, setDecisionQuestion] = useState("");
  const [decisionResponse, setDecisionResponse] = useState("");
  const [activeAction, setActiveAction] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  const loadPatient = useCallback(async () => {
    const [p, c, t, d, me] = await Promise.all([
      getPatient(patientId),
      getPatientCalls(patientId),
      getPatientTrends(patientId),
      getPatientDecisions(patientId),
      getMe(),
    ]);
    setPatient(p); setCalls(c); setTrends(t); setDecisions(d); setClinician(me);
    if (c.length > 0) setSelectedCall(c[0].call_id);
    setLoading(false);
  }, [patientId]);

  useEffect(() => { loadPatient(); }, [loadPatient]);

  useEffect(() => {
    if (!selectedCall) return;
    setCallDetail(null); setCallDecision(null); setShowTranscript(false);
    Promise.all([getCall(selectedCall), getDecision(selectedCall)]).then(
      ([cd, dec]) => { setCallDetail(cd); setCallDecision(dec); }
    );
  }, [selectedCall]);

  async function handleReviewCall() {
    setActionLoading(true);
    await reviewCall(selectedCall);
    setActionMsg("Call marked as reviewed.");
    await loadPatient();
    const cd = await getCall(selectedCall);
    setCallDetail(cd);
    setActionLoading(false);
  }

  async function handleNote() {
    setActionLoading(true);
    await actionNote(patientId, { notes_text: noteText, call_id: selectedCall });
    setNoteText(""); setActiveAction(null); setActionMsg("Note saved.");
    await loadPatient(); setActionLoading(false);
  }

  async function handleProbe() {
    setActionLoading(true);
    const tomorrow = new Date(Date.now() + 86400000).toISOString();
    await actionProbe(patientId, {
      probe_instructions: probeInstructions,
      scheduled_for: tomorrow,
      module: patient?.program_module || "post_discharge",
    });
    setProbeInstructions(""); setActiveAction(null);
    setActionMsg("Probe call scheduled for tomorrow.");
    await loadPatient(); setActionLoading(false);
  }

  async function handleEscalate() {
    setActionLoading(true);
    await actionEscalate(patientId, { notes: escalateNote });
    setEscalateNote(""); setActiveAction(null); setActionMsg("Patient escalated.");
    await loadPatient(); setActionLoading(false);
  }

  async function handleResolveFlag(flagId) {
    setActionLoading(true);
    await resolveFlag(patientId, flagId, { resolution_notes: "Resolved by clinician" });
    setActionMsg("Flag resolved.");
    await loadPatient(); setActionLoading(false);
  }

  async function handleRequestDecision() {
    setActionLoading(true);
    const dec = await createDecision(selectedCall, { clinical_question: decisionQuestion });
    setCallDecision(dec); setDecisionQuestion(""); setActiveAction(null);
    setActionMsg("AI decision generated.");
    await loadPatient(); setActionLoading(false);
  }

  async function handleRespondDecision() {
    if (!callDecision) return;
    setActionLoading(true);
    await respondToDecision(callDecision.decision_id, { clinician_response: decisionResponse });
    const updated = await getDecision(selectedCall);
    setCallDecision(updated); setDecisionResponse(""); setActiveAction(null);
    setActionMsg("Response saved."); setActionLoading(false);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <aside className="sidebar" />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin w-5 h-5 text-nhs-blue" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            Loading patient…
          </div>
        </div>
      </div>
    );
  }

  // Trend chart
  const trendDays = new Set();
  if (trends) Object.values(trends).forEach((d) => d.actual.forEach((p) => trendDays.add(p.day)));
  const trendChartData = Array.from(trendDays).sort((a, b) => a - b).map((day) => {
    const row = { day };
    if (trends) {
      Object.entries(trends).forEach(([domain, d]) => {
        const actual = d.actual.find((p) => p.day === day);
        const expected = d.expected.find((p) => p.day === day);
        if (actual) row[domain] = actual.score;
        if (expected) row[`${domain}_exp`] = expected.score;
      });
    }
    return row;
  });

  const initials = patient.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  const urgencyGradient = patient.urgency_severity === "red"
    ? "from-red-600 to-rose-700"
    : patient.urgency_severity === "amber"
    ? "from-amber-500 to-orange-600"
    : "from-nhs-blue to-nhs-blue-light";

  return (
    <Layout clinician={clinician}>
      {/* Patient hero banner */}
      <div className={`bg-gradient-to-r ${urgencyGradient} px-6 py-5`}>
        <button
          onClick={() => navigate("/dashboard")}
          className="flex items-center gap-1.5 text-white/70 hover:text-white text-xs font-medium mb-4 transition"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to Dashboard
        </button>
        <div className="flex items-center gap-5">
          <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center text-white text-xl font-bold shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-white">{patient.full_name}</h1>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
                patient.status === "active" ? "bg-white/20 border-white/30 text-white" :
                patient.status === "escalated" ? "bg-red-200/30 border-red-200/50 text-red-100" :
                "bg-white/10 border-white/20 text-white/70"
              }`}>
                {patient.status}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 mt-1.5 text-white/80 text-sm">
              <span>NHS: <strong className="text-white">{patient.nhs_number}</strong></span>
              <span>DOB: <strong className="text-white">{formatDate(patient.date_of_birth)}</strong></span>
              <span>{patient.condition}</span>
              {patient.day_in_recovery != null && (
                <span className="font-semibold text-white bg-white/20 px-2 py-0.5 rounded-full text-xs">
                  Day {patient.day_in_recovery} post-discharge
                </span>
              )}
            </div>
          </div>
          <div className="shrink-0">
            <UrgencyBadge severity={patient.urgency_severity} />
          </div>
        </div>
      </div>

      <div className="flex-1 p-5 space-y-4">
        {/* Action message */}
        {actionMsg && (
          <div className="flex items-center justify-between bg-green-50 border border-green-200 text-green-800 text-sm rounded-xl px-4 py-2.5">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              {actionMsg}
            </div>
            <button onClick={() => setActionMsg("")} className="text-green-500 hover:text-green-700 ml-4">✕</button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left col */}
          <div className="space-y-4 lg:col-span-2">

            {/* Longitudinal Summary */}
            {patient.longitudinal_summary && (
              <Section title="AI Longitudinal Summary">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-nhs-blue/10 flex items-center justify-center shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-nhs-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-700 leading-relaxed">{patient.longitudinal_summary.narrative_text}</p>
                    <div className="text-[10px] text-gray-400 mt-2">
                      v{patient.longitudinal_summary.version_number} · {formatDateTime(patient.longitudinal_summary.generated_at)}
                    </div>
                    {patient.longitudinal_summary.active_concerns_snapshot?.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {patient.longitudinal_summary.active_concerns_snapshot.map((c, i) => (
                          <span key={i} className="bg-red-50 text-red-700 text-xs px-2.5 py-1 rounded-full border border-red-100 font-medium">
                            ⚠ {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Section>
            )}

            {/* Trend chart */}
            {trendChartData.length > 0 && (
              <Section title="Recovery Trends">
                {patient.longitudinal_summary?.trend_snapshot && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {Object.entries(patient.longitudinal_summary.trend_snapshot).map(([k, v]) => {
                      const arrow = v === "improving" ? "↑" : v === "worsening" || v === "acute_deterioration" ? "↓" : "→";
                      const cls = v === "improving" ? "text-green-700 bg-green-50 border-green-100" :
                        (v === "worsening" || v === "acute_deterioration") ? "text-red-700 bg-red-50 border-red-100" :
                        "text-gray-600 bg-gray-50 border-gray-100";
                      return (
                        <span key={k} className={`text-xs font-semibold px-2.5 py-1 rounded-full border capitalize ${cls}`}>
                          {arrow} {k}
                        </span>
                      );
                    })}
                  </div>
                )}
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={trendChartData} margin={{ top: 5, right: 5, left: -15, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="day" label={{ value: "Day", position: "insideBottom", offset: -2 }} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                    <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)", fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {Object.entries(DOMAIN_COLORS).map(([domain, color]) =>
                      trendChartData.some((d) => d[domain] != null) && (
                        <Line key={domain} type="monotone" dataKey={domain} stroke={color}
                          strokeWidth={2.5} dot={{ r: 4, strokeWidth: 0, fill: color }}
                          activeDot={{ r: 6 }} connectNulls
                          name={`${DOMAIN_ICONS[domain]} ${domain.charAt(0).toUpperCase() + domain.slice(1)}`}
                        />
                      )
                    )}
                    {Object.entries(DOMAIN_COLORS).map(([domain, color]) =>
                      trendChartData.some((d) => d[`${domain}_exp`] != null) && (
                        <Line key={`${domain}_exp`} type="monotone" dataKey={`${domain}_exp`}
                          stroke={color} strokeWidth={1} strokeDasharray="4 2"
                          dot={false} connectNulls name={`${domain} (expected)`}
                        />
                      )
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </Section>
            )}

            {/* Call History */}
            <Section title="Call History">
              {calls.length === 0 ? (
                <p className="text-sm text-gray-400">No calls recorded yet.</p>
              ) : (
                <div className="space-y-1.5">
                  {calls.map((c) => {
                    const active = selectedCall === c.call_id;
                    return (
                      <button
                        key={c.call_id}
                        onClick={() => setSelectedCall(c.call_id)}
                        className={`w-full text-left px-4 py-2.5 rounded-xl text-sm flex items-center justify-between transition-all ${
                          active ? "bg-nhs-blue text-white shadow-md" : "hover:bg-gray-50 text-gray-700 border border-gray-100"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                            active ? "bg-white/20 text-white" : "bg-nhs-blue/10 text-nhs-blue"
                          }`}>
                            {c.day_in_recovery ?? "?"}
                          </div>
                          <div>
                            <div className="font-semibold text-xs">Day {c.day_in_recovery} — {c.trigger_type}</div>
                            <div className={`text-[10px] ${active ? "text-blue-200" : "text-gray-400"}`}>
                              {c.direction} · {formatDuration(c.duration_seconds)}
                            </div>
                          </div>
                        </div>
                        <span className={`text-xs ${active ? "text-blue-200" : "text-gray-400"}`}>
                          {formatDateTime(c.started_at)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </Section>

            {/* Call Detail */}
            {callDetail && (
              <Section
                title={`Call Detail — Day ${callDetail.day_in_recovery}`}
                action={
                  callDetail.soap_note?.clinician_reviewed ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full border border-green-100">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Reviewed
                    </span>
                  ) : (
                    <button
                      onClick={handleReviewCall}
                      disabled={actionLoading}
                      className="text-xs font-semibold bg-nhs-blue text-white px-3 py-1.5 rounded-lg hover:bg-nhs-blue/90 disabled:opacity-50 transition"
                    >
                      Mark Reviewed
                    </button>
                  )
                }
              >
                <div className="space-y-5">
                  {/* Scores */}
                  {callDetail.extraction && (
                    <div>
                      <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Extracted Scores</div>
                      <div className="flex justify-around">
                        {[
                          ["Pain", callDetail.extraction.pain_score, NHS_RED],
                          ["Breathless", callDetail.extraction.breathlessness_score, NHS_AMBER],
                          ["Mobility", callDetail.extraction.mobility_score, NHS_BLUE],
                          ["Appetite", callDetail.extraction.appetite_score, "#8B5CF6"],
                          ["Mood", callDetail.extraction.mood_score, NHS_GREEN],
                        ].map(([label, val, color]) => (
                          <ScoreRing key={label} value={val} label={label} color={color} />
                        ))}
                      </div>
                      <div className="mt-3 text-center">
                        <span className={`text-xs font-semibold px-3 py-1 rounded-full ${
                          callDetail.extraction.medication_adherence
                            ? "bg-green-50 text-green-700 border border-green-100"
                            : "bg-red-50 text-red-700 border border-red-100"
                        }`}>
                          {callDetail.extraction.medication_adherence ? "✓ Medication adherent" : "✗ Medication non-adherent"}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* SOAP Note */}
                  {callDetail.soap_note && (
                    <div>
                      <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">SOAP Note</div>
                      <div className="space-y-3">
                        {[
                          ["S", "Subjective", callDetail.soap_note.subjective, "bg-blue-50 border-blue-100 text-blue-800"],
                          ["O", "Objective", callDetail.soap_note.objective, "bg-slate-50 border-slate-100 text-slate-700"],
                          ["A", "Assessment", callDetail.soap_note.assessment, "bg-amber-50 border-amber-100 text-amber-800"],
                          ["P", "Plan", callDetail.soap_note.plan, "bg-green-50 border-green-100 text-green-800"],
                        ].map(([code, label, text, cls]) => (
                          <div key={code} className={`rounded-xl border p-3 ${cls}`}>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="w-5 h-5 rounded-md bg-white/60 flex items-center justify-center text-[10px] font-black">{code}</span>
                              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">{label}</span>
                            </div>
                            <p className="text-xs leading-relaxed">{text}</p>
                          </div>
                        ))}
                        <p className="text-[10px] text-gray-400">
                          Generated {formatDateTime(callDetail.soap_note.generated_at)} · {callDetail.soap_note.model_used}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Urgency flags */}
                  {callDetail.urgency_flags?.length > 0 && (
                    <div>
                      <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Urgency Flags</div>
                      <div className="space-y-2">
                        {callDetail.urgency_flags.map((f) => (
                          <div key={f.flag_id} className={`rounded-xl border p-3 flex items-start justify-between gap-3 ${
                            f.severity === "red" ? "bg-red-50 border-red-200" :
                            f.severity === "amber" ? "bg-amber-50 border-amber-200" :
                            "bg-green-50 border-green-200"
                          }`}>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <UrgencyBadge severity={f.severity} />
                                <span className="text-xs font-semibold text-gray-700">{f.flag_type.replace(/_/g, " ")}</span>
                              </div>
                              <p className="text-xs text-gray-600">{f.trigger_description}</p>
                            </div>
                            {f.status !== "resolved" && (
                              <button
                                onClick={() => handleResolveFlag(f.flag_id)}
                                disabled={actionLoading}
                                className="text-xs font-medium text-green-700 border border-green-300 px-2.5 py-1 rounded-lg hover:bg-green-50 shrink-0 transition"
                              >
                                Resolve
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Transcript */}
                  {callDetail.transcript_raw && (
                    <div>
                      <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="flex items-center gap-2 text-xs font-semibold text-gray-500 hover:text-gray-700 transition"
                      >
                        <svg className={`w-3.5 h-3.5 transition-transform ${showTranscript ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                        {showTranscript ? "Hide" : "View"} Transcript
                      </button>
                      {showTranscript && (
                        <div className="mt-2 rounded-xl bg-gray-50 border border-gray-100 p-3 text-xs text-gray-600 whitespace-pre-wrap max-h-64 overflow-y-auto leading-relaxed">
                          {callDetail.transcript_raw}
                        </div>
                      )}
                    </div>
                  )}

                  {/* AI Decision Support */}
                  <div className="border-t border-gray-100 pt-4">
                    <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
                      AI Clinical Decision Support
                    </div>

                    {callDecision ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>Requested {formatDateTime(callDecision.requested_at)}</span>
                          {callDecision.actioned && (
                            <span className="text-green-600 font-semibold bg-green-50 px-2 py-0.5 rounded-full border border-green-100">✓ Actioned</span>
                          )}
                        </div>

                        {[
                          ["Differential Diagnoses", callDecision.differential_diagnoses, "bg-blue-50 border-blue-100 text-blue-800"],
                          ["Recommended Actions", callDecision.recommended_actions, "bg-green-50 border-green-100 text-green-800"],
                          ["NICE References", callDecision.nice_references, "bg-purple-50 border-purple-100 text-purple-800"],
                        ].map(([label, items, cls]) => items?.length > 0 && (
                          <div key={label} className={`rounded-xl border p-3 ${cls}`}>
                            <div className="text-[10px] font-bold uppercase tracking-widest mb-2 opacity-70">{label}</div>
                            <ul className="space-y-1">
                              {items.map((item, i) => (
                                <li key={i} className="text-xs flex items-start gap-1.5">
                                  <span className="mt-0.5 shrink-0">•</span>
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ))}

                        {callDecision.risk_assessment && (
                          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                            <div className="text-[10px] font-bold text-amber-700 uppercase tracking-widest mb-1">Risk Assessment</div>
                            <p className="text-xs text-amber-800">{callDecision.risk_assessment}</p>
                          </div>
                        )}

                        {callDecision.uncertainty_flags?.length > 0 && (
                          <div className="bg-orange-50 border border-orange-200 rounded-xl p-3">
                            <div className="text-[10px] font-bold text-orange-700 uppercase tracking-widest mb-1">Uncertainty Flags</div>
                            {callDecision.uncertainty_flags.map((f, i) => (
                              <p key={i} className="text-xs text-orange-800 flex items-start gap-1.5"><span>⚠</span>{f}</p>
                            ))}
                          </div>
                        )}

                        {!callDecision.actioned && (
                          activeAction === "respond" ? (
                            <div className="space-y-2">
                              <textarea
                                className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-nhs-blue/30 focus:border-nhs-blue transition"
                                rows={3}
                                placeholder="Document your clinical response…"
                                value={decisionResponse}
                                onChange={(e) => setDecisionResponse(e.target.value)}
                              />
                              <div className="flex gap-2">
                                <button onClick={handleRespondDecision} disabled={actionLoading || !decisionResponse}
                                  className="text-xs font-semibold bg-nhs-blue text-white px-3 py-1.5 rounded-lg hover:bg-nhs-blue/90 disabled:opacity-50 transition">
                                  {actionLoading ? "Saving…" : "Save Response"}
                                </button>
                                <button onClick={() => setActiveAction(null)} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                              </div>
                            </div>
                          ) : (
                            <button onClick={() => setActiveAction("respond")}
                              className="text-xs font-semibold text-nhs-blue border border-nhs-blue/30 bg-nhs-blue/5 px-3 py-1.5 rounded-lg hover:bg-nhs-blue/10 transition">
                              Document Response
                            </button>
                          )
                        )}

                        {callDecision.actioned && callDecision.clinician_response && (
                          <div className="bg-green-50 border border-green-200 rounded-xl px-3 py-2">
                            <span className="text-xs font-bold text-green-700">Clinician Response: </span>
                            <span className="text-xs text-green-800">{callDecision.clinician_response}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      activeAction === "decision" ? (
                        <div className="space-y-2">
                          <textarea
                            className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-nhs-blue/30 focus:border-nhs-blue transition"
                            rows={2}
                            placeholder="Clinical question (optional)…"
                            value={decisionQuestion}
                            onChange={(e) => setDecisionQuestion(e.target.value)}
                          />
                          <div className="flex gap-2">
                            <button onClick={handleRequestDecision} disabled={actionLoading}
                              className="text-xs font-semibold bg-nhs-blue text-white px-3 py-1.5 rounded-lg hover:bg-nhs-blue/90 disabled:opacity-50 transition">
                              {actionLoading ? "Generating…" : "Generate Decision"}
                            </button>
                            <button onClick={() => setActiveAction(null)} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => setActiveAction("decision")}
                          className="flex items-center gap-2 text-xs font-semibold bg-nhs-blue text-white px-4 py-2 rounded-lg hover:bg-nhs-blue/90 transition"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                          </svg>
                          Request AI Decision Support
                        </button>
                      )
                    )}
                  </div>
                </div>
              </Section>
            )}
          </div>

          {/* Right col */}
          <div className="space-y-4">
            {/* Medical Profile */}
            {patient.medical_profile && (
              <Section title="Medical Profile">
                <div className="space-y-3">
                  <div>
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Primary Diagnosis</div>
                    <p className="text-sm font-semibold text-gray-800">{patient.medical_profile.primary_diagnosis}</p>
                  </div>
                  {patient.medical_profile.secondary_diagnoses?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Secondary Diagnoses</div>
                      <div className="flex flex-wrap gap-1">
                        {patient.medical_profile.secondary_diagnoses.map((d, i) => (
                          <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full">{d}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {patient.medical_profile.allergies?.length > 0 && (
                    <div className="bg-red-50 border border-red-100 rounded-xl p-3">
                      <div className="text-[10px] font-bold text-red-500 uppercase tracking-widest mb-1">⚠ Allergies</div>
                      <p className="text-xs text-red-800 font-semibold">{patient.medical_profile.allergies.join(", ")}</p>
                    </div>
                  )}
                  {patient.medical_profile.current_medications?.length > 0 && (
                    <div>
                      <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Medications</div>
                      <div className="space-y-1">
                        {patient.medical_profile.current_medications.map((m, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs text-gray-700">
                            <span className="w-1.5 h-1.5 rounded-full bg-nhs-blue/50 shrink-0" />
                            {m}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {patient.medical_profile.consultant_notes && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                      <div className="text-[10px] font-bold text-amber-600 uppercase tracking-widest mb-1">Consultant Notes</div>
                      <p className="text-xs text-amber-800">{patient.medical_profile.consultant_notes}</p>
                    </div>
                  )}
                  {patient.medical_profile.discharge_summary_text && (
                    <details className="rounded-xl border border-gray-100 overflow-hidden">
                      <summary className="px-3 py-2 text-xs font-semibold text-gray-600 cursor-pointer bg-gray-50 hover:bg-gray-100 transition">
                        Discharge Summary
                      </summary>
                      <p className="px-3 py-2 text-xs text-gray-600 leading-relaxed bg-white">
                        {patient.medical_profile.discharge_summary_text}
                      </p>
                    </details>
                  )}
                </div>
              </Section>
            )}

            {/* Clinician Actions */}
            <Section title="Actions">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: "note", label: "Add Note", icon: "📝", cls: "border-nhs-blue/30 text-nhs-blue bg-nhs-blue/5 hover:bg-nhs-blue/10", activeCls: "bg-nhs-blue text-white border-transparent" },
                    { id: "probe", label: "Probe Call", icon: "📞", cls: "border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100", activeCls: "bg-purple-600 text-white border-transparent" },
                    { id: "escalate", label: "Escalate", icon: "🚨", cls: "border-red-300 text-red-700 bg-red-50 hover:bg-red-100", activeCls: "bg-red-600 text-white border-transparent" },
                  ].map((btn) => (
                    <button
                      key={btn.id}
                      onClick={() => setActiveAction(activeAction === btn.id ? null : btn.id)}
                      className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border transition ${
                        activeAction === btn.id ? btn.activeCls : btn.cls
                      }`}
                    >
                      <span>{btn.icon}</span>
                      {btn.label}
                    </button>
                  ))}
                </div>

                {activeAction === "note" && (
                  <ActionForm placeholder="Clinical note…" value={noteText} onChange={setNoteText}
                    onSubmit={handleNote} onCancel={() => setActiveAction(null)} loading={actionLoading} label="Save Note" />
                )}
                {activeAction === "probe" && (
                  <ActionForm placeholder="Probe instructions for the AI agent…" value={probeInstructions} onChange={setProbeInstructions}
                    onSubmit={handleProbe} onCancel={() => setActiveAction(null)} loading={actionLoading} label="Schedule Probe" />
                )}
                {activeAction === "escalate" && (
                  <ActionForm placeholder="Escalation reason…" value={escalateNote} onChange={setEscalateNote}
                    onSubmit={handleEscalate} onCancel={() => setActiveAction(null)} loading={actionLoading} label="Confirm Escalation" danger />
                )}

                {patient.clinician_actions?.length > 0 && (
                  <div className="border-t border-gray-100 pt-3">
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Activity Log</div>
                    <div className="space-y-2 max-h-52 overflow-y-auto">
                      {patient.clinician_actions.slice().reverse().map((a) => (
                        <div key={a.action_id} className="flex gap-2 text-xs">
                          <div className="w-1 rounded-full bg-nhs-blue/20 shrink-0 mt-1" />
                          <div>
                            <div className="font-semibold text-gray-700 capitalize">{a.action_type.replace(/_/g, " ")}</div>
                            {a.notes_text && <div className="text-gray-500 mt-0.5">{a.notes_text}</div>}
                            <div className="text-[10px] text-gray-400 mt-0.5">{formatDateTime(a.action_at)}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Section>

            {/* Decision History */}
            {decisions.length > 0 && (
              <Section title="Decision History">
                <div className="space-y-2">
                  {decisions.map((d) => (
                    <div
                      key={d.decision_id}
                      onClick={() => {
                        const call = calls.find((c) => c.call_id === d.call_id);
                        if (call) setSelectedCall(call.call_id);
                      }}
                      className="rounded-xl border border-gray-100 hover:border-nhs-blue/20 hover:bg-blue-50/30 p-3 cursor-pointer transition"
                    >
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-xs font-semibold text-gray-700">{formatDateTime(d.requested_at)}</span>
                        {d.actioned ? (
                          <span className="text-[10px] font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-100">✓ Actioned</span>
                        ) : (
                          <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">Pending</span>
                        )}
                      </div>
                      <p className="text-[11px] text-gray-500 line-clamp-2">{d.risk_assessment}</p>
                    </div>
                  ))}
                </div>
              </Section>
            )}
          </div>
        </div>
      </div>
      <PatientChat patientId={patientId} patientName={patient.full_name} />
    </Layout>
  );
}

function ActionForm({ placeholder, value, onChange, onSubmit, onCancel, loading, label, danger }) {
  return (
    <div className="space-y-2">
      <textarea
        className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-nhs-blue/30 focus:border-nhs-blue transition resize-none"
        rows={3}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="flex gap-2">
        <button
          onClick={onSubmit}
          disabled={loading || !value}
          className={`text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-50 ${
            danger ? "bg-red-600 hover:bg-red-700" : "bg-nhs-blue hover:bg-nhs-blue/90"
          }`}
        >
          {loading ? "Saving…" : label}
        </button>
        <button onClick={onCancel} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
      </div>
    </div>
  );
}

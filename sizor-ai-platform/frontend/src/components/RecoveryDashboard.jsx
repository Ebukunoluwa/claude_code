/**
 * RecoveryDashboard
 * Interactive NICE-baseline vs patient-actual recovery chart.
 * Built with Recharts — fully interactive, live-polled, click-through to calls.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import {
  ComposedChart, Line, Area, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea,
  LineChart,
} from "recharts";
import client from "../api/client";

// ── Design tokens ─────────────────────────────────────────────────────────────
const SCORE = {
  0: { label: "Resolved",  color: "#16a34a", bg: "#dcfce7", text: "#14532d" },
  1: { label: "Expected",  color: "#22c55e", bg: "#f0fdf4", text: "#166534" },
  2: { label: "Monitor",   color: "#eab308", bg: "#fefce8", text: "#713f12" },
  3: { label: "Expedite",  color: "#f97316", bg: "#fff7ed", text: "#7c2d12" },
  4: { label: "Escalate",  color: "#ef4444", bg: "#fef2f2", text: "#7f1d1d" },
};

const ZONE_FILLS = [
  { y1: 0, y2: 1, fill: "#dcfce7" },
  { y1: 1, y2: 2, fill: "#fefce8" },
  { y1: 2, y2: 3, fill: "#ffedd5" },
  { y1: 3, y2: 4, fill: "#fee2e2" },
];

const NHS_BLUE = "#003087";

function scoreColor(s) { return (SCORE[s] ?? SCORE[4]).color; }
function scoreLabel(s) { return (SCORE[s] ?? SCORE[4]).label; }

// ── Helpers ────────────────────────────────────────────────────────────────────
function buildChartData(benchmarkRows, actualPoints, domain) {
  const benchMap = {};
  for (const r of benchmarkRows.filter(r => r.domain === domain)) {
    benchMap[r.day_range_start] = r;
  }
  const actualMap = {};
  for (const p of (actualPoints || [])) {
    actualMap[p.day] = p;
  }

  const allDays = [...new Set([
    ...Object.keys(benchMap).map(Number),
    ...Object.keys(actualMap).map(Number),
  ])].sort((a, b) => a - b);

  return allDays.map(day => ({
    day,
    expected:  benchMap[day]?.expected_score  ?? null,
    upper:     benchMap[day]?.upper_bound_score ?? null,
    niceSource: benchMap[day]?.nice_source ?? null,
    niceQuote:  benchMap[day]?.nice_quote  ?? null,
    actual:    actualMap[day]?.score        ?? null,
    ftp_flag:  actualMap[day]?.ftp_flag     ?? false,
    call_id:   actualMap[day]?.call_id      ?? null,
    date:      actualMap[day]?.date         ?? null,
    assessment: actualMap[day]?.assessment  ?? null,
    subjective: actualMap[day]?.subjective  ?? null,
    ftp_status: actualMap[day]?.ftp_status  ?? null,
  }));
}

// ── Score badge ────────────────────────────────────────────────────────────────
function ScoreBadge({ score, size = "sm" }) {
  if (score === null || score === undefined) return null;
  const s = SCORE[score] ?? SCORE[4];
  const pad = size === "lg" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-semibold ${pad}`}
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
      {score} · {s.label}
    </span>
  );
}

// ── Custom dot on the line ─────────────────────────────────────────────────────
function ActualDot(props) {
  const { cx, cy, payload } = props;
  if (payload.actual === null) return null;
  const col = scoreColor(payload.actual);
  const isFtp = payload.ftp_flag;
  return (
    <g>
      {isFtp && (
        <circle cx={cx} cy={cy} r={16} fill="none" stroke="#ef4444" strokeWidth={3} strokeDasharray="5 3" opacity={0.8} />
      )}
      {/* Outer glow ring */}
      <circle cx={cx} cy={cy} r={11} fill={col} opacity={0.2} />
      {/* Main dot */}
      <circle cx={cx} cy={cy} r={8} fill={col} stroke="#fff" strokeWidth={2.5} />
      {/* Day label above dot */}
      <text x={cx} y={cy - 15} textAnchor="middle" fontSize={9} fill="#6b7280" fontWeight={600}>
        D{payload.day}
      </text>
    </g>
  );
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, onCallSelect }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  const hasActual = d.actual !== null;

  return (
    <div className="bg-white rounded-xl shadow-2xl border border-gray-100 p-4 min-w-[260px] max-w-[320px]"
      style={{ backdropFilter: "blur(8px)" }}>

      {/* Day header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Day in recovery</span>
          <p className="text-2xl font-bold text-gray-900">{d.day}</p>
        </div>
        {hasActual && <ScoreBadge score={d.actual} size="lg" />}
      </div>

      {/* NICE reference */}
      {d.expected !== null && (
        <div className="mb-3 pb-3 border-b border-gray-100">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">NICE Benchmark</p>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1 text-xs text-blue-700 bg-blue-50 rounded-full px-2 py-0.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Expected: {d.expected}
            </div>
            <div className="flex items-center gap-1 text-xs text-amber-700 bg-amber-50 rounded-full px-2 py-0.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Upper bound: {d.upper}
            </div>
          </div>
          {d.niceSource && (
            <p className="text-[10px] text-gray-400 mt-1">{d.niceSource}</p>
          )}
        </div>
      )}

      {/* Actual patient data */}
      {hasActual ? (
        <div className="space-y-2">
          {d.ftp_flag && (
            <div className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 rounded-lg px-2.5 py-1.5">
              <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              Failed to progress
            </div>
          )}
          {d.subjective && (
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-0.5">Patient reported</p>
              <p className="text-xs text-gray-600 leading-relaxed italic">"{d.subjective.slice(0, 160)}{d.subjective.length > 160 ? "…" : ""}"</p>
            </div>
          )}
          {d.assessment && (
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-0.5">Clinical assessment</p>
              <p className="text-xs text-gray-700 leading-relaxed">{d.assessment.slice(0, 160)}{d.assessment.length > 160 ? "…" : ""}</p>
            </div>
          )}
          {d.call_id && onCallSelect && (
            <button
              onMouseDown={() => onCallSelect(d.call_id)}
              className="mt-1 w-full text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center justify-center gap-1 py-1.5 rounded-lg hover:bg-indigo-50 transition-colors"
            >
              View call details →
            </button>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-400 italic">No patient data recorded for this day.</p>
      )}
    </div>
  );
}

// ── Mini sparkline for overview grid ──────────────────────────────────────────
function DomainCard({ domain, benchmarkRows, actualPoints, isActive, onClick, onCallSelect }) {
  const data = buildChartData(benchmarkRows, actualPoints, domain);
  const latest = [...(actualPoints || [])].sort((a, b) => b.day - a.day)[0];
  const lastScore = latest?.score ?? null;
  const hasData = actualPoints && actualPoints.length > 0;

  // Determine status vs NICE
  let statusColor = "#6b7280";
  let statusText = "No data";
  if (lastScore !== null) {
    const bench = benchmarkRows.find(r => r.domain === domain && Math.abs(r.day_range_start - latest.day) < 5);
    if (bench) {
      if (lastScore <= bench.expected_score) { statusColor = "#16a34a"; statusText = "On track"; }
      else if (lastScore <= bench.upper_bound_score) { statusColor = "#eab308"; statusText = "Monitor"; }
      else { statusColor = "#ef4444"; statusText = "Above threshold"; }
    } else {
      statusColor = scoreColor(lastScore);
      statusText = scoreLabel(lastScore);
    }
  }

  return (
    <button
      onClick={onClick}
      className={`group text-left rounded-xl border transition-all duration-200 overflow-hidden ${
        isActive
          ? "border-indigo-400 bg-indigo-50 shadow-md shadow-indigo-100"
          : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
      }`}
    >
      <div className="p-3">
        <div className="flex items-start justify-between mb-2">
          <p className="text-xs font-semibold text-gray-700 leading-tight capitalize pr-2">
            {domain.replace(/_/g, " ")}
          </p>
          {lastScore !== null && <ScoreBadge score={lastScore} />}
        </div>

        <div className="flex items-center gap-1.5 mb-2">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: statusColor }} />
          <span className="text-[10px] font-medium" style={{ color: statusColor }}>{statusText}</span>
          {latest && (
            <span className="text-[10px] text-gray-400 ml-auto">Day {latest.day}</span>
          )}
        </div>

        {/* Mini sparkline */}
        <div style={{ height: 44 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
              {ZONE_FILLS.map(z => (
                <ReferenceArea key={z.y1} y1={z.y1} y2={z.y2} fill={z.fill} fillOpacity={0.5} />
              ))}
              <YAxis domain={[0, 4]} hide />
              <XAxis dataKey="day" hide />
              <Line type="monotone" dataKey="expected" stroke="#93c5fd" strokeWidth={1} dot={false} />
              <Line type="monotone" dataKey="upper" stroke="#fde68a" strokeWidth={1} strokeDasharray="3 2" dot={false} />
              {hasData && (
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke={lastScore !== null ? scoreColor(lastScore) : "#818cf8"}
                  strokeWidth={2}
                  dot={{ r: 3, fill: lastScore !== null ? scoreColor(lastScore) : "#818cf8", stroke: "#fff", strokeWidth: 1 }}
                  connectNulls={false}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </button>
  );
}

// ── Full domain chart ──────────────────────────────────────────────────────────
function DomainChart({ domain, benchmarkRows, actualPoints, onCallSelect }) {
  const data = buildChartData(benchmarkRows, actualPoints, domain);
  const hasActual = actualPoints && actualPoints.length > 0;

  const yTick = ({ x, y, payload }) => {
    const s = SCORE[payload.value];
    if (!s) return null;
    return (
      <g transform={`translate(${x},${y})`}>
        <text x={-4} y={0} dy={4} textAnchor="end" fontSize={10} fill={s.color} fontWeight={600}>
          {payload.value}
        </text>
        <text x={-24} y={0} dy={4} textAnchor="end" fontSize={10} fill="#9ca3af">
          {s.label}
        </text>
      </g>
    );
  };

  return (
    <div>
      {/* ── Visual legend cards — makes each line unmistakable ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-5">
        {/* NICE baseline */}
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-3.5 py-3">
          <div className="flex items-center gap-2 mb-1">
            <svg width="28" height="10">
              <line x1="0" y1="5" x2="28" y2="5" stroke="#3b82f6" strokeWidth="2.5" />
              <circle cx="14" cy="5" r="3" fill="#3b82f6" />
            </svg>
            <span className="text-xs font-bold text-blue-700">NICE Baseline</span>
          </div>
          <p className="text-[11px] text-blue-600 leading-snug">
            The <strong>solid blue line</strong> shows the expected recovery score at each day, sourced from NICE clinical guidelines.
          </p>
        </div>

        {/* Upper bound */}
        <div className="rounded-xl border border-amber-100 bg-amber-50 px-3.5 py-3">
          <div className="flex items-center gap-2 mb-1">
            <svg width="28" height="10">
              <line x1="0" y1="5" x2="28" y2="5" stroke="#f59e0b" strokeWidth="2" strokeDasharray="5 3" />
            </svg>
            <span className="text-xs font-bold text-amber-700">Concern Threshold</span>
          </div>
          <p className="text-[11px] text-amber-700 leading-snug">
            The <strong>dashed amber line</strong> is the upper bound — scores above this need clinical attention.
          </p>
        </div>

        {/* Patient line */}
        <div className={`rounded-xl border px-3.5 py-3 ${hasActual ? "border-indigo-100 bg-indigo-50" : "border-gray-100 bg-gray-50"}`}>
          <div className="flex items-center gap-2 mb-1">
            {hasActual ? (
              <svg width="28" height="10">
                <line x1="0" y1="5" x2="28" y2="5" stroke="#6366f1" strokeWidth="2.5" />
                <circle cx="14" cy="5" r="4.5" fill="#6366f1" stroke="#fff" strokeWidth="1.5" />
              </svg>
            ) : (
              <svg width="28" height="10">
                <line x1="0" y1="5" x2="28" y2="5" stroke="#d1d5db" strokeWidth="2" strokeDasharray="4 3" />
              </svg>
            )}
            <span className={`text-xs font-bold ${hasActual ? "text-indigo-700" : "text-gray-400"}`}>
              {hasActual ? "This Patient" : "Patient (no data yet)"}
            </span>
          </div>
          <p className={`text-[11px] leading-snug ${hasActual ? "text-indigo-600" : "text-gray-400"}`}>
            {hasActual
              ? <>The <strong>purple line with dots</strong> is the patient's actual recorded scores from each call. <strong>Hover dots</strong> to see what they said.</>
              : "Patient scores will appear here after calls are completed."}
          </p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 80 }}>
          <defs>
            <linearGradient id="expectedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
            </linearGradient>
          </defs>

          {/* Score zone backgrounds */}
          {ZONE_FILLS.map(z => (
            <ReferenceArea key={z.y1} y1={z.y1} y2={z.y2} fill={z.fill} fillOpacity={0.45} />
          ))}

          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis
            dataKey="day"
            tickFormatter={d => `D${d}`}
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 4]}
            ticks={[0, 1, 2, 3, 4]}
            tick={yTick}
            axisLine={false}
            tickLine={false}
            width={80}
          />
          <Tooltip
            content={<ChartTooltip onCallSelect={onCallSelect} />}
            cursor={{ stroke: "#e2e8f0", strokeWidth: 1, strokeDasharray: "4 2" }}
          />

          {/* NICE expected area fill */}
          <Area
            type="monotone"
            dataKey="expected"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#expectedGrad)"
            dot={false}
            activeDot={false}
          />

          {/* Upper bound dashed line */}
          <Line
            type="monotone"
            dataKey="upper"
            stroke="#f59e0b"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            dot={false}
            activeDot={false}
          />

          {/* Patient actual — thick purple, large dots, clearly distinct */}
          {hasActual && (
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#4f46e5"
              strokeWidth={4}
              dot={<ActualDot />}
              activeDot={{ r: 11, stroke: "#fff", strokeWidth: 3, fill: "#4f46e5" }}
              connectNulls={false}
              style={{ filter: "drop-shadow(0 2px 6px rgba(79,70,229,0.35))" }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* NICE source table */}
      {benchmarkRows.filter(r => r.domain === domain && r.nice_source).length > 0 && (
        <div className="mt-5 rounded-xl border border-gray-100 overflow-hidden">
          <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">NICE Reference Data</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100">
                  {["Period", "Expected", "Upper bound", "State", "Source"].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 font-semibold text-gray-400 uppercase tracking-wider text-[10px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {benchmarkRows.filter(r => r.domain === domain).map(r => (
                  <tr key={r.day_range_start} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    <td className="px-4 py-2.5 text-gray-600">Day {r.day_range_start}–{r.day_range_end}</td>
                    <td className="px-4 py-2.5"><ScoreBadge score={r.expected_score} /></td>
                    <td className="px-4 py-2.5"><ScoreBadge score={r.upper_bound_score} /></td>
                    <td className="px-4 py-2.5 text-gray-500">{r.expected_state || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                        {r.nice_source || "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function RecoveryDashboard({ opcsCode, patientId, title, onCallSelect }) {
  const [benchmarkRows, setBenchmarkRows] = useState([]);
  const [actualScores, setActualScores]   = useState({});
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState(null);
  const [activeDomain, setActiveDomain]   = useState(null);
  const [lastUpdated, setLastUpdated]     = useState(null);
  const pollRef = useRef(null);

  const fetchBenchmarks = useCallback(() => {
    if (!opcsCode) return;
    return client
      .get(`/benchmarks/${opcsCode}`)
      .then(r => {
        setBenchmarkRows(r.data);
        const domains = [...new Set(r.data.map(x => x.domain))];
        setActiveDomain(prev => prev || domains[0] || null);
      })
      .catch(e => setError(e.response?.data?.detail || "Failed to load benchmarks"));
  }, [opcsCode]);

  const fetchScores = useCallback(() => {
    if (!patientId) return;
    return client
      .get(`/patients/${patientId}/scores`)
      .then(r => {
        setActualScores(r.data);
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, [patientId]);

  useEffect(() => {
    if (!opcsCode) return;
    setLoading(true);
    setError(null);
    Promise.all([fetchBenchmarks(), fetchScores()])
      .finally(() => setLoading(false));
  }, [opcsCode, patientId]);

  // Live poll every 30s
  useEffect(() => {
    if (!patientId) return;
    pollRef.current = setInterval(fetchScores, 30_000);
    return () => clearInterval(pollRef.current);
  }, [fetchScores]);

  const domains = [...new Set(benchmarkRows.map(r => r.domain))];

  if (!opcsCode) return null;

  return (
    <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">

      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-[#003087]/[0.03] to-transparent">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#003087" }}>
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900">
                {title || `Recovery Pathway — ${opcsCode}`}
              </h3>
              <p className="text-[11px] text-gray-400">NICE-sourced benchmarks · patient trajectory overlay</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Updated {lastUpdated.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
          <button
            onClick={() => { fetchBenchmarks(); fetchScores(); }}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-16 gap-3 text-gray-400">
          <svg className="animate-spin w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Loading pathway data…</span>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="m-6 p-4 rounded-xl bg-red-50 border border-red-100 text-sm text-red-600 flex items-center gap-2">
          <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="p-6 space-y-6">

          {/* Domain overview grid */}
          {domains.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Domains — click to explore</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2.5">
                {domains.map(domain => (
                  <DomainCard
                    key={domain}
                    domain={domain}
                    benchmarkRows={benchmarkRows}
                    actualPoints={actualScores[domain]}
                    isActive={activeDomain === domain}
                    onClick={() => setActiveDomain(domain)}
                    onCallSelect={onCallSelect}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Active domain detail chart */}
          {activeDomain && (
            <div className="rounded-xl border border-gray-100 overflow-hidden">
              <div className="px-5 py-3.5 border-b border-gray-100 bg-gray-50/60 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-800 capitalize">
                    {activeDomain.replace(/_/g, " ")}
                  </h4>
                  <p className="text-[11px] text-gray-400 mt-0.5">
                    NICE baseline vs patient trajectory · hover points for call detail
                  </p>
                </div>
                {/* Current score badge */}
                {(() => {
                  const pts = actualScores[activeDomain];
                  if (!pts?.length) return null;
                  const latest = [...pts].sort((a, b) => b.day - a.day)[0];
                  return (
                    <div className="text-right">
                      <p className="text-[10px] text-gray-400 mb-0.5">Latest · Day {latest.day}</p>
                      <ScoreBadge score={latest.score} size="lg" />
                    </div>
                  );
                })()}
              </div>
              <div className="p-5">
                <DomainChart
                  domain={activeDomain}
                  benchmarkRows={benchmarkRows}
                  actualPoints={actualScores[activeDomain]}
                  onCallSelect={onCallSelect}
                />
              </div>
            </div>
          )}

          {/* Score zone legend */}
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-gray-50">
            <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Score scale:</span>
            {Object.entries(SCORE).map(([s, meta]) => (
              <div key={s} className="flex items-center gap-1 text-[10px]">
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: meta.bg, border: `1.5px solid ${meta.color}` }} />
                <span style={{ color: meta.text }} className="font-medium">{s} = {meta.label}</span>
              </div>
            ))}
          </div>

        </div>
      )}
    </div>
  );
}

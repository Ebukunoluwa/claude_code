import { useState, useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { getPatient, getPatientCalls, getPatientTrends, getPatientNotes, actionNote, updatePatient, updateProfile, updatePathway, getPatientPathwayDetails, getPatientRiskHistory } from "../api/patients";
import { getCall } from "../api/calls";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";
import PatientChat from "../components/PatientChat";
import EscalateModal from "../components/EscalateModal";
import PatientScheduleModal from "../components/PatientScheduleModal";

function toRag(sev) {
  if (sev === "red")   return "RED";
  if (sev === "amber") return "AMBER";
  return "GREEN";
}


function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(secs) {
  if (!secs) return "—";
  const m = Math.floor(secs / 60), s = secs % 60;
  return `${m}m ${s}s`;
}

/** Build per-domain chart data from getPatientTrends() response.
 *  Returns { charts: [{name, key, actual:[{day,score}], expected:[{day,score}]}], days: number[] }
 *  Scores are 0-10, higher = worse symptoms.
 */
function buildTrendCharts(trends) {
  const DOMAIN_LABELS = { pain: "Pain", breathlessness: "Breathlessness", mobility: "Mobility", appetite: "Appetite", mood: "Mood" };
  const charts = [];
  const allDays = new Set();
  for (const [key, d] of Object.entries(trends)) {
    if (!d.actual || !d.actual.length) continue;
    d.actual.forEach(p => allDays.add(p.day));
    d.expected.forEach(p => allDays.add(p.day));
    charts.push({ name: DOMAIN_LABELS[key] || key, key, actual: d.actual, expected: d.expected });
  }
  const days = [...allDays].sort((a, b) => a - b);
  return { charts, days };
}

/** Fallback trajectory if no trend data */
function buildFallbackTrajectory(daysAdmitted, rag) {
  const totalDays = Math.max(daysAdmitted + 3, 7);
  const startScore = 8.5;
  return Array.from({ length: totalDays + 1 }, (_, day) => {
    const expected = Math.max(1, startScore - (startScore - 1.5) * (day / totalDays));
    const deviation = rag === "RED" ? 1.15 : rag === "AMBER" ? 1.08 : 0.95;
    const actual = day <= daysAdmitted ? Math.min(10, expected * deviation) : null;
    return { day, expected: parseFloat(expected.toFixed(1)), actual: actual !== null ? parseFloat(actual.toFixed(1)) : null };
  });
}

/** Multi-domain recovery chart.
 *  Each row = one domain. Scores 0-10, lower = better recovery.
 *  Teal dashed = expected, coloured = actual.
 */
function DomainChart({ name, actual, expected, t }) {
  const W = 500, H = 72, PL = 8, PR = 8, PT = 6, PB = 20;
  const iW = W - PL - PR, iH = H - PT - PB;
  const allDays = [...new Set([...actual.map(p=>p.day), ...expected.map(p=>p.day)])].sort((a,b)=>a-b);
  if (!allDays.length) return null;
  const maxDay = allDays[allDays.length - 1] || 1;
  const x = day => PL + (day / maxDay) * iW;
  const y = v => PT + (v / 10) * iH;  // 0=top(good), 10=bottom(bad)
  const expPts = expected.map(p => `${x(p.day)},${y(p.score)}`).join(" ");
  const actPts = actual.map(p => `${x(p.day)},${y(p.score)}`).join(" ");
  const lastAct = actual[actual.length - 1];
  const lastExp = expected.find(p => p.day === lastAct?.day) || expected[expected.length - 1];
  const isFtp = lastAct && lastExp && lastAct.score > lastExp.score + 0.5;
  const actColor = isFtp ? t.red : t.green;
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id={`ag-${name}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={actColor} stopOpacity="0"/>
          <stop offset="100%" stopColor={actColor} stopOpacity="0.15"/>
        </linearGradient>
      </defs>
      {[0, 5, 10].map(v => (
        <line key={v} x1={PL} y1={y(v)} x2={W-PR} y2={y(v)} stroke={t.border} strokeWidth={v===0||v===10?"1.5":"1"} strokeDasharray={v===0||v===10?"none":"3,4"} opacity="0.5"/>
      ))}
      {allDays.map(d => (
        <text key={d} x={x(d)} y={H - 4} fontSize="9" fill={t.textMuted} textAnchor="middle" fontFamily="'DM Mono',monospace">D{d}</text>
      ))}
      {expPts && <polyline points={expPts} fill="none" stroke="#0AAFA8" strokeWidth="1.5" strokeDasharray="5,3" opacity="0.65"/>}
      {actPts && actual.length > 0 && (
        <>
          <polygon points={`${x(actual[0].day)},${PT+iH} ${actPts} ${x(lastAct.day)},${PT+iH}`} fill={`url(#ag-${name})`}/>
          <polyline points={actPts} fill="none" stroke={actColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          {actual.map(p => (<circle key={p.day} cx={x(p.day)} cy={y(p.score)} r="3.5" fill={actColor}/>))}
          <text x={x(lastAct.day)+7} y={y(lastAct.score)+4} fontSize="9" fill={actColor} fontFamily="'Outfit',sans-serif" fontWeight="700">{lastAct.score}</text>
        </>
      )}
      {isFtp && (
        <g>
          <rect x={x(lastAct.day)+20} y={y(lastAct.score)-9} width={36} height={14} rx={3} fill={t.redBg} stroke={t.redBorder} strokeWidth="1"/>
          <text x={x(lastAct.day)+38} y={y(lastAct.score)+1} fontSize="8" fill={t.red} textAnchor="middle" fontFamily="'DM Mono',monospace">FTP</text>
        </g>
      )}
    </svg>
  );
}

function TrajectoryChart({ trends, fallbackData, t }) {
  const [activeDomain, setActiveDomain] = useState(null);
  let domainCharts = [];
  let hasTrends = false;
  if (trends && Object.keys(trends).length > 0) {
    const built = buildTrendCharts(trends);
    domainCharts = built.charts;
    hasTrends = domainCharts.length > 0;
  }
  if (!hasTrends) {
    const data = fallbackData || [];
    if (!data.length) return null;
    const W=500, H=140, PL=36, PR=16, PT=16, PB=28;
    const iW=W-PL-PR, iH=H-PT-PB;
    const maxDay = Math.max(...data.map(d=>d.day), 1);
    const x = d => PL + (d/maxDay)*iW;
    const y = v => PT + (v/10)*iH;
    const expPts = data.map(d=>`${x(d.day)},${y(d.expected)}`).join(" ");
    const actData = data.filter(d=>d.actual!==null);
    const actPts = actData.map(d=>`${x(d.day)},${y(d.actual)}`).join(" ");
    return (
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{overflow:"visible"}}>
        {[0,5,10].map(v=>(
          <g key={v}>
            <line x1={PL} y1={y(v)} x2={W-PR} y2={y(v)} stroke={t.border} strokeWidth="1" strokeDasharray="3,4"/>
            <text x={PL-4} y={y(v)+4} fontSize="9" fill={t.textMuted} textAnchor="end" fontFamily="'DM Mono',monospace">{v}</text>
          </g>
        ))}
        {data.map(d=><text key={d.day} x={x(d.day)} y={H-4} fontSize="9" fill={t.textMuted} textAnchor="middle" fontFamily="'DM Mono',monospace">D{d.day}</text>)}
        {expPts && <polyline points={expPts} fill="none" stroke="#0AAFA8" strokeWidth="1.5" strokeDasharray="5,4" opacity="0.6"/>}
        {actPts && <polyline points={actPts} fill="none" stroke={t.brand} strokeWidth="2" strokeLinecap="round"/>}
        {actData.map(d=><circle key={d.day} cx={x(d.day)} cy={y(d.actual)} r="3.5" fill={t.brand}/>)}
      </svg>
    );
  }
  const DOMAIN_COLORS = { pain: "#FF6B6B", breathlessness: "#FF9F43", mobility: "#26de81", appetite: "#A29BFE", mood: "#74B9FF" };
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:"0px" }}>
      <div style={{ display:"flex", gap:"6px", marginBottom:"14px", flexWrap:"wrap" }}>
        <button onClick={() => setActiveDomain(null)} style={{ padding:"4px 10px", borderRadius:"100px", fontFamily:"'DM Mono',monospace", fontSize:"9px", cursor:"pointer", background:activeDomain===null?t.brandGlow:"transparent", border:"1px solid "+(activeDomain===null?t.brand+"50":t.border), color:activeDomain===null?t.brand:t.textMuted, transition:"all 0.15s" }}>ALL</button>
        {domainCharts.map(dc => (
          <button key={dc.key} onClick={() => setActiveDomain(activeDomain===dc.key?null:dc.key)} style={{ padding:"4px 10px", borderRadius:"100px", fontFamily:"'DM Mono',monospace", fontSize:"9px", cursor:"pointer", background:activeDomain===dc.key?(DOMAIN_COLORS[dc.key]||t.brand)+"20":"transparent", border:"1px solid "+(activeDomain===dc.key?(DOMAIN_COLORS[dc.key]||t.brand)+"60":t.border), color:activeDomain===dc.key?(DOMAIN_COLORS[dc.key]||t.brand):t.textMuted, transition:"all 0.15s" }}>{dc.name.toUpperCase()}</button>
        ))}
        <span style={{ marginLeft:"auto", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, alignSelf:"center" }}>
          <span style={{ display:"inline-block", width:16, borderTop:"1.5px dashed #0AAFA8", marginRight:4, verticalAlign:"middle" }}/>EXPECTED&nbsp;&nbsp;
          <span style={{ display:"inline-block", width:16, borderTop:"2px solid "+t.green, marginRight:4, verticalAlign:"middle" }}/>ACTUAL
        </span>
      </div>
      {domainCharts.filter(dc => !activeDomain || dc.key===activeDomain).map(dc => (
        <div key={dc.key} style={{ display:"grid", gridTemplateColumns:"72px 1fr", alignItems:"center", gap:"8px", padding:"8px 0", borderBottom:"1px solid "+t.border }}>
          <div style={{ textAlign:"right", paddingRight:8 }}>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"0.5px" }}>{dc.name.toUpperCase()}</div>
            <div style={{ width:"100%", height:3, borderRadius:3, background:t.surfaceHigh, marginTop:3, overflow:"hidden" }}>
              <div style={{ width:((dc.actual[dc.actual.length-1]?.score||0)/10*100)+"%", height:"100%", background:DOMAIN_COLORS[dc.key]||t.brand, borderRadius:3, transition:"width 0.4s ease" }}/>
            </div>
          </div>
          <DomainChart name={dc.key} actual={dc.actual} expected={dc.expected} t={t}/>
        </div>
      ))}
    </div>
  );
}

export default function PatientDetailPage() {
  const { t }    = useTheme();
  const navigate = useNavigate();
  const { id }   = useParams();
  const location = useLocation();

  const [tab, setTab]             = useState("timeline");
  const [mounted, setMounted]     = useState(false);

  // Data from API
  const [patient, setPatient]           = useState(location.state?.patient || null);
  const [calls, setCalls]               = useState([]);
  const [latestCall, setLatestCall]     = useState(null);
  const [selectedCall, setSelectedCall] = useState(null); // call selected in history
  const [selectedCallLoading, setSelectedCallLoading] = useState(false);
  const [callPage, setCallPage]         = useState(0);    // 5 per page
  const [trajectory, setTrajectory]     = useState(null);
  const [trends, setTrends]             = useState(null);
  const [riskHistory, setRiskHistory]   = useState([]);
  const [showRiskBreakdown, setShowRiskBreakdown] = useState(false);
  const [loading, setLoading]           = useState(true);
  const [actionBusy, setActionBusy]     = useState(null);
  const [actionMsg, setActionMsg]       = useState("");
  const [showEscalate, setShowEscalate] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [notesPage, setNotesPage]       = useState(0);
  const [clinicianNotes, setClinicianNotes] = useState([]);
  const [newNote, setNewNote]           = useState("");
  const [addingNote, setAddingNote]     = useState(false);
  const [showNoteForm, setShowNoteForm] = useState(false);

  const [showEditModal, setShowEditModal]      = useState(false);

  // Edit modal state
  const [editPhone, setEditPhone]             = useState("");
  const [editCallTime, setEditCallTime]       = useState("");
  const [editDiagnosis, setEditDiagnosis]     = useState("");
  const [editMeds, setEditMeds]               = useState([]);
  const [editAllergies, setEditAllergies]     = useState([]);
  const [editRiskFlags, setEditRiskFlags]     = useState([]);
  const [editRedFlags, setEditRedFlags]       = useState([]);
  const [editDomains, setEditDomains]         = useState([]);
  const [newMed, setNewMed]                   = useState("");
  const [newAllergy, setNewAllergy]           = useState("");
  const [newRiskFlag, setNewRiskFlag]         = useState("");
  const [newRedFlag, setNewRedFlag]           = useState("");
  const [newDomain, setNewDomain]             = useState("");
  const [editSaving, setEditSaving]           = useState(false);
  const [editMsg, setEditMsg]                 = useState({ text: "", ok: true });
  const [pathwayDetails, setPathwayDetails]   = useState(null);

  const pid = id || patient?.id;

  useEffect(() => {
    if (!pid) { setLoading(false); return; }
    setTab("timeline");
    setLoading(true);

    const fetchAll = async () => {
      try {
        // 1. Full patient details
        const patientData = await getPatient(pid);
        setPatient(prev => ({
          // Keep any fields from navigation state, override with real API data
          ...(prev || {}),
          id:              patientData.patient_id,
          name:            patientData.full_name || prev?.name || "Unknown",
          initials:        (patientData.full_name || "?").split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase(),
          nhs:             patientData.nhs_number || "—",
          ward:            patientData.condition || prev?.ward || "General",
          pathway:         patientData.condition || prev?.pathway || "General",
          bed:             prev?.bed || "—",
          admitted:        patientData.discharge_date
                             ? new Date(patientData.discharge_date).toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"})
                             : "—",
          expectedDischarge: "—",
          surgeon:         "—",
          nurse:           "—",
          daysAdmitted:    patientData.day_in_recovery ?? 0,
          rag:             toRag(patientData.urgency_severity),
          score:           patientData.risk_score != null ? Math.round(patientData.risk_score) : null,
          delta:           patientData.risk_score_delta != null ? Math.round(patientData.risk_score_delta) : null,
          riskScoreBreakdown: patientData.risk_score_breakdown ?? null,
          domainScores:      patientData.domain_scores ?? null,
          flag:            patientData.urgency_severity !== "green"
                             ? (patientData.urgency_severity === "red" ? "Red flag — review required" : "Amber watch — monitoring")
                             : null,
          medicalProfile:  patientData.medical_profile,
          longitudinalSummary: patientData.longitudinal_summary,
        }));

        // 2. Call list
        const callList = await getPatientCalls(pid);
        const sorted = Array.isArray(callList) ? [...callList].sort((a,b) => new Date(b.started_at) - new Date(a.started_at)) : [];
        setCalls(sorted);

        // 3. Full detail for latest call (SOAP + urgency flags)
        if (sorted.length > 0 && sorted[0].call_id) {
          const full = await getCall(sorted[0].call_id).catch(() => null);
          setLatestCall(full);
          setSelectedCall(full);
        }

        // 4. Clinician notes
        const notes = await getPatientNotes(pid).catch(() => []);
        setClinicianNotes(notes);

        // 4b. Initialise edit-tab fields from fresh patient data
        setEditPhone(patientData.phone_number || "");
        setEditCallTime(patientData.preferred_call_time || "");
        setEditDiagnosis(patientData.medical_profile?.primary_diagnosis || "");
        setEditMeds(patientData.medical_profile?.current_medications || []);
        setEditAllergies(patientData.medical_profile?.allergies || []);
        const pathDetails = await getPatientPathwayDetails(pid).catch(() => null);
        setPathwayDetails(pathDetails);
        if (pathDetails) {
          setEditRiskFlags(pathDetails.risk_flags || []);
          setEditRedFlags(pathDetails.clinical_red_flags || []);
          setEditDomains(pathDetails.domains || []);
        }

        // 5. Trend data for trajectory chart + risk score history
        const [trendData, riskHist] = await Promise.all([
          getPatientTrends(pid).catch(() => null),
          getPatientRiskHistory(pid).catch(() => []),
        ]);
        const daysAdmitted = patientData.day_in_recovery ?? 0;
        const rag = toRag(patientData.urgency_severity);
        setTrends(trendData);
        setRiskHistory(Array.isArray(riskHist) ? riskHist : []);
        setTrajectory(buildFallbackTrajectory(daysAdmitted, rag));

      } catch (err) {
        console.error("PatientDetail fetch error:", err);
      } finally {
        setLoading(false);
        setTimeout(() => setMounted(true), 50);
      }
    };

    fetchAll();
  }, [pid]);

  if (!pid) {
    return (
      <div style={{ minHeight:"100vh", background:t.bg }}>
        <Nav/>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:"60vh" }}>
          <div style={{ textAlign:"center" }}>
            <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14, marginBottom:16 }}>No patient selected.</div>
            <button onClick={() => navigate("/patients")} style={{ padding:"10px 20px", borderRadius:10, background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:13, cursor:"pointer" }}>← Back to Patient Queue</button>
          </div>
        </div>
      </div>
    );
  }

  if (loading || !patient) {
    return (
      <div style={{ minHeight:"100vh", background:t.bg }}>
        <Nav/>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"center", height:"60vh" }}>
          <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>Loading patient…</div>
        </div>
      </div>
    );
  }

  const p   = patient;
  const cfg = ragCfg(t, p.rag || "GREEN");
  const score = p.score ?? null;   // null until first completed call with data
  const hasRealScore = score != null;
  const delta = p.delta ?? null;
  const traj = trajectory || buildFallbackTrajectory(p.daysAdmitted || 0, p.rag || "GREEN");
  const hasTrends = trends && Object.values(trends).some(d => d.actual && d.actual.length > 0);


  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>
      <div style={{ maxWidth:1200, margin:"0 auto", padding:"32px 24px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"340px 1fr", gap:"20px", opacity:mounted?1:0, transition:"opacity 0.4s ease" }}>

          {/* ── LEFT: Identity + Risk ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>

            {/* Identity card */}
            <div style={{ background:t.surface, border:"1px solid "+cfg.border, borderRadius:"18px", padding:"24px", boxShadow:"0 0 40px "+cfg.glow, position:"relative", overflow:"hidden" }}>
              <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+cfg.dot+",transparent)" }}/>
              <div style={{ display:"flex", alignItems:"center", gap:"14px", marginBottom:"20px" }}>
                <div style={{ width:52, height:52, borderRadius:"50%", background:cfg.bg, border:"2px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:cfg.text }}>{p.initials}</div>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:t.textPrimary }}>{p.name}</div>
                    <button
                      onClick={() => setShowEditModal(true)}
                      style={{ background:"none", border:"none", padding:0, cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"0.5px", textDecoration:"underline", textUnderlineOffset:3 }}
                    >Edit Details</button>
                  </div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>NHS {p.nhs}</div>
                </div>
              </div>
              {p.flag && (
                <div style={{ display:"flex", alignItems:"center", gap:"8px", padding:"8px 12px", borderRadius:"10px", background:cfg.bg, border:"1px solid "+cfg.border, marginBottom:"20px" }}>
                  <span style={{ width:8, height:8, borderRadius:"50%", background:cfg.dot, display:"inline-block", boxShadow:"0 0 8px "+cfg.dot, animation:p.rag==="RED"?"pulse 1.5s infinite":"none" }}/>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", fontWeight:600, color:cfg.text }}>{p.rag} · {p.flag}</span>
                </div>
              )}
              {[["Ward",p.ward],["Pathway",p.pathway],["Discharge",p.admitted],["Day in Recovery",(p.daysAdmitted!=null?p.daysAdmitted+" days":"—")],["NHS Number",p.nhs]].map(([k,v])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:"1px solid "+t.border }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500 }}>{v}</span>
                </div>
              ))}
              {/* Medical profile if available */}
              {p.medicalProfile && (
                <>
                  {p.medicalProfile.primary_diagnosis && (
                    <div style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:"1px solid "+t.border }}>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>DIAGNOSIS</span>
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500, textAlign:"right", maxWidth:180 }}>{p.medicalProfile.primary_diagnosis}</span>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Risk score */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"12px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>CURRENT RISK SCORE</div>
                {p.riskScoreBreakdown && (
                  <button
                    type="button"
                    onClick={() => setShowRiskBreakdown(v => !v)}
                    style={{ background:"none", border:"none", padding:0, cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"0.5px" }}
                  >{showRiskBreakdown ? "HIDE" : "WHY?"}</button>
                )}
              </div>
              {hasRealScore ? (
                <>
                  <div style={{ display:"flex", alignItems:"baseline", gap:"12px" }}>
                    <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"56px", fontWeight:900, color:cfg.text, lineHeight:1, letterSpacing:"-2px" }}>{score}</span>
                    {delta != null && delta !== 0 && (
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"14px", color:delta > 0 ? t.red : t.green }}>
                        {delta > 0 ? "▲" : "▼"} {Math.abs(delta)} prev call
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop:"16px", height:"6px", borderRadius:"6px", background:t.surfaceHigh, overflow:"hidden" }}>
                    <div style={{ height:"100%", width:score+"%", background:"linear-gradient(90deg,#22E676,#FFB020,#FF4D4D)", borderRadius:"6px", transition:"width 1s ease" }}/>
                  </div>
                  <div style={{ display:"flex", justifyContent:"space-between", marginTop:"6px" }}>
                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>LOW RISK</span>
                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>HIGH RISK</span>
                  </div>
                </>
              ) : (
                <div style={{ padding:"20px 0 8px", fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textMuted, fontStyle:"italic" }}>
                  Risk score will appear after the first completed call with data.
                </div>
              )}

              {/* Breakdown panel — pathway domain scores */}
              {hasRealScore && showRiskBreakdown && (() => {
                const domainScores = p.domainScores
                  ? Object.entries(p.domainScores).sort((a, b) => (b[1] || 0) - (a[1] || 0))
                  : [];
                if (domainScores.length === 0) return null;
                return (
                  <div style={{ marginTop:"14px", padding:"12px", borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border }}>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", marginBottom:"8px" }}>
                      PATHWAY DOMAIN SCORES (0-4)
                    </div>
                    {domainScores.map(([domain, val]) => {
                      const pct = Math.min(100, ((val || 0) / 4) * 100);
                      const color = val >= 3 ? t.red : val >= 2 ? "#f59e0b" : t.brand;
                      return (
                        <div key={domain} style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"5px" }}>
                          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, width:100, flexShrink:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                            {domain.replace(/_/g," ").toUpperCase()}
                          </span>
                          <div style={{ flex:1, height:"4px", borderRadius:"3px", background:t.border, overflow:"hidden" }}>
                            <div style={{ height:"100%", width:pct+"%", background:color, borderRadius:"3px", transition:"width 0.4s ease" }}/>
                          </div>
                          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textSecond, width:28, textAlign:"right" }}>{val ?? "—"}/4</span>
                        </div>
                      );
                    })}
                  </div>
                );
              })()}

              {/* Risk history sparkline */}
              {hasRealScore && riskHistory.length > 1 && (() => {
                const W=260, H=44, PL=4, PR=4, PT=4, PB=14;
                const iW=W-PL-PR, iH=H-PT-PB;
                const scores = riskHistory.map(r => r.risk_score);
                const days   = riskHistory.map((r,i) => r.day_in_recovery ?? i);
                const minD=Math.min(...days), maxD=Math.max(...days)||1;
                const x = d => PL + ((d-minD)/(maxD-minD||1))*iW;
                const y = v => PT + (1-(v/100))*iH;
                const pts = riskHistory.map((r,i) => `${x(days[i])},${y(r.risk_score)}`).join(" ");
                const bandColor = s => s >= 70 ? "#ef4444" : s >= 40 ? "#f59e0b" : "#22c55e";
                return (
                  <div style={{ marginTop:"16px" }}>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", marginBottom:"6px" }}>RISK SCORE HISTORY</div>
                    <svg width={W} height={H} style={{ overflow:"visible", display:"block" }}>
                      {/* Zero baseline at 40 (amber threshold) */}
                      <line x1={PL} y1={y(40)} x2={W-PR} y2={y(40)} stroke={t.border} strokeWidth="1" strokeDasharray="3,3"/>
                      <line x1={PL} y1={y(70)} x2={W-PR} y2={y(70)} stroke={t.redBorder||"#fca5a5"} strokeWidth="1" strokeDasharray="3,3"/>
                      <polyline points={pts} fill="none" stroke={t.brand} strokeWidth="2" strokeLinejoin="round"/>
                      {riskHistory.map((r,i) => (
                        <circle key={i} cx={x(days[i])} cy={y(r.risk_score)} r="3"
                          fill={bandColor(r.risk_score)} stroke={t.surface} strokeWidth="1.5"/>
                      ))}
                      {/* Day labels */}
                      {riskHistory.map((r,i) => (
                        <text key={i} x={x(days[i])} y={H} fontSize="7"
                          fill={t.textMuted} textAnchor="middle" fontFamily="'DM Mono',monospace">
                          D{days[i] ?? i}
                        </text>
                      ))}
                    </svg>
                  </div>
                );
              })()}
            </div>

            {/* Clinical summary — longitudinal narrative or latest SOAP assessment */}
            {(p.longitudinalSummary?.narrative_text || latestCall?.soap_note?.assessment) && (
              <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"12px" }}>
                  {p.longitudinalSummary?.narrative_text ? "CLINICAL SUMMARY" : "LATEST ASSESSMENT"}
                </div>
                <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.7 }}>
                  {p.longitudinalSummary?.narrative_text || latestCall?.soap_note?.assessment}
                </div>
              </div>
            )}
          </div>

          {/* ── RIGHT: Trajectory + Tabs ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>

            {/* Trajectory chart — only once we have real trend data */}
            {hasTrends && (
              <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"20px" }}>
                  <div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"16px", color:t.textPrimary }}>Recovery Trajectory</div>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"3px" }}>ACTUAL vs NICE EXPECTED CURVE · {(p.pathway||"PATHWAY").toUpperCase()}</div>
                  </div>
                  {p.flag && (
                    <div style={{ padding:"6px 14px", borderRadius:"8px", background:t.redBg, border:"1px solid "+t.redBorder, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.red }}>
                      FTP DAY {p.daysAdmitted}
                    </div>
                  )}
                </div>
                <TrajectoryChart trends={trends} fallbackData={null} t={t}/>
              </div>
            )}

            {/* Tabs: Call History / SOAP / Notes */}
            {(() => {
              const selSoap  = selectedCall?.soap_note || null;
              const selFlags = selectedCall?.urgency_flags || [];
              const selDay   = selectedCall?.day_in_recovery;
              const selDate  = selectedCall?.started_at;
              const PAGE_SIZE = 5;
              const totalPages = Math.ceil(calls.length / PAGE_SIZE);
              const pageCalls  = calls.slice(callPage * PAGE_SIZE, callPage * PAGE_SIZE + PAGE_SIZE);

              async function selectCall(call) {
                if (selectedCall?.call_id === call.call_id) return;
                setSelectedCallLoading(true);
                const full = await getCall(call.call_id).catch(() => null);
                setSelectedCall(full);
                setSelectedCallLoading(false);
              }

              return (
                <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", overflow:"hidden", boxShadow:"0 2px 12px "+t.shadow }}>
                  <div style={{ display:"flex", borderBottom:"1px solid "+t.border }}>
                    {[["timeline","Call History"],["soap","SOAP Note"],["notes","Clinical Notes"]].map(([key,label])=>(
                      <button key={key} onClick={()=>{ setTab(key); if(key==="notes") setNotesPage(0); }} style={{ flex:1, padding:"14px", background:"none", border:"none", cursor:"pointer", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:tab===key?t.textPrimary:t.textMuted, borderBottom:tab===key?"2px solid "+t.brand:"2px solid transparent", transition:"all 0.15s ease" }}>{label}</button>
                    ))}
                  </div>

                  {/* Selected call context strip */}
                  {selectedCall && (
                    <div style={{ padding:"8px 20px", background:t.surfaceHigh, borderBottom:"1px solid "+t.border, display:"flex", alignItems:"center", gap:"8px" }}>
                      <span style={{ width:6, height:6, borderRadius:"50%", background:t.brand, display:"inline-block", flexShrink:0 }}/>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>VIEWING</span>
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textSecond, fontWeight:600 }}>
                        {selDate ? formatDate(selDate) : "—"}{selDay != null ? " · Day " + selDay : ""}
                      </span>
                      {selectedCallLoading && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, marginLeft:"auto" }}>LOADING…</span>}
                    </div>
                  )}

                  <div style={{ padding:"20px" }}>

                    {/* Call History */}
                    {tab === "timeline" && (
                      <div style={{ display:"flex", flexDirection:"column", gap:"10px" }}>
                        {calls.length === 0 ? (
                          <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>No call records found.</div>
                        ) : (
                          <>
                            {pageCalls.map((call) => {
                              const isSel = selectedCall?.call_id === call.call_id;
                              const isLatest = call.call_id === latestCall?.call_id;
                              const flagSev = isLatest ? (latestCall?.urgency_flags?.[0]?.severity || "green") : "green";
                              const c = ragCfg(t, toRag(flagSev));
                              return (
                                <div
                                  key={call.call_id}
                                  onClick={() => selectCall(call)}
                                  style={{ display:"flex", gap:"14px", padding:"14px 16px", borderRadius:"12px", cursor:"pointer", background:isSel?c.bg:t.surfaceHigh, border:"1px solid "+(isSel?c.border:t.border), transition:"all 0.15s", outline:isSel?"none":"none" }}
                                >
                                  <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:"3px", minWidth:58, flexShrink:0 }}>
                                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"12px", color:t.textPrimary, textAlign:"center" }}>{formatDate(call.started_at)}</div>
                                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{formatTime(call.started_at)}</div>
                                    {call.day_in_recovery != null && (
                                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:isSel?c.text:t.textMuted, marginTop:2 }}>DAY {call.day_in_recovery}</div>
                                    )}
                                  </div>
                                  <div style={{ flex:1, minWidth:0 }}>
                                    <div style={{ display:"flex", alignItems:"center", gap:"6px", marginBottom:"5px" }}>
                                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>{call.trigger_type?.toUpperCase() || "CALL"}</span>
                                      {isLatest && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, padding:"1px 6px", borderRadius:4, background:t.brandGlow, border:"1px solid "+t.brand+"30" }}>LATEST</span>}
                                      {isSel && !isLatest && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:c.text, padding:"1px 6px", borderRadius:4, background:c.bg, border:"1px solid "+c.border }}>SELECTED</span>}
                                    </div>
                                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textSecond, lineHeight:1.5, overflow:"hidden", display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
                                      {isSel && selSoap?.assessment
                                        ? selSoap.assessment
                                        : call.status === "completed" ? "Completed · " + formatDuration(call.duration_seconds) : (call.status || "Recorded")}
                                    </div>
                                  </div>
                                  <div style={{ display:"flex", alignItems:"center", flexShrink:0 }}>
                                    <span style={{ fontSize:"12px", color:isSel?c.text:t.textMuted }}>›</span>
                                  </div>
                                </div>
                              );
                            })}

                            {/* Pagination */}
                            {totalPages > 1 && (
                              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", paddingTop:"10px", borderTop:"1px solid "+t.border }}>
                                <button
                                  onClick={() => setCallPage(p => Math.max(0, p-1))}
                                  disabled={callPage === 0}
                                  style={{ padding:"6px 14px", borderRadius:"8px", background:t.surfaceHigh, border:"1px solid "+t.border, color:callPage===0?t.textMuted:t.textSecond, fontFamily:"'DM Mono',monospace", fontSize:"10px", cursor:callPage===0?"not-allowed":"pointer", opacity:callPage===0?0.4:1 }}
                                >← PREV</button>
                                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>
                                  {callPage * PAGE_SIZE + 1}–{Math.min((callPage+1)*PAGE_SIZE, calls.length)} of {calls.length}
                                </span>
                                <button
                                  onClick={() => setCallPage(p => Math.min(totalPages-1, p+1))}
                                  disabled={callPage >= totalPages-1}
                                  style={{ padding:"6px 14px", borderRadius:"8px", background:t.surfaceHigh, border:"1px solid "+t.border, color:callPage>=totalPages-1?t.textMuted:t.textSecond, fontFamily:"'DM Mono',monospace", fontSize:"10px", cursor:callPage>=totalPages-1?"not-allowed":"pointer", opacity:callPage>=totalPages-1?0.4:1 }}
                                >NEXT →</button>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}

                    {/* SOAP Note — for selected call */}
                    {tab === "soap" && (
                      <div>
                        {selectedCallLoading ? (
                          <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>Loading SOAP note…</div>
                        ) : selectedCall?.status === "missed" || selectedCall?.status === "no_answer" ? (
                          <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>
                            Call did not connect — no SOAP note generated.
                          </div>
                        ) : !selSoap || (!selSoap.subjective && !selSoap.assessment) ? (
                          <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>
                            {calls.length === 0 ? "No calls found." : "No SOAP note available for this call."}
                          </div>
                        ) : (
                          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
                            {[["S","Subjective",selSoap.subjective],["O","Objective",selSoap.objective],["A","Assessment",selSoap.assessment],["P","Plan",selSoap.plan]].map(([key,label,text],i)=>(
                              <div key={key} style={{ display:"flex", gap:"14px" }}>
                                <div style={{ width:36, height:36, borderRadius:"10px", background:i===2?cfg.bg:t.surfaceHigh, border:"1px solid "+(i===2?cfg.border:t.border), display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"15px", color:i===2?cfg.text:t.textSecond, flexShrink:0 }}>{key}</div>
                                <div>
                                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"6px" }}>{label.toUpperCase()}</div>
                                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13.5px", color:t.textSecond, lineHeight:1.7, whiteSpace:"pre-line" }}>{text || "—"}</div>
                                </div>
                              </div>
                            ))}
                            {selFlags.length > 0 && (
                              <div style={{ padding:"12px 16px", borderRadius:"10px", background:cfg.bg, border:"1px solid "+cfg.border }}>
                                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:cfg.text, marginBottom:"6px" }}>URGENCY FLAGS</div>
                                {selFlags.map((f, i) => (
                                  <div key={i} style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:cfg.text, marginBottom:"4px" }}>▲ {f.trigger_description || f.flag_type}</div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Clinical Notes — paginated + add note */}
                    {tab === "notes" && (() => {
                      const NOTES_SIZE  = 5;
                      const notesTotal  = Math.ceil(calls.length / NOTES_SIZE);
                      const safeNP      = Math.min(notesPage, Math.max(0, notesTotal - 1));
                      const pagNotes    = calls.slice(safeNP * NOTES_SIZE, safeNP * NOTES_SIZE + NOTES_SIZE);

                      async function submitNote() {
                        if (!newNote.trim() || addingNote) return;
                        setAddingNote(true);
                        try {
                          await actionNote(pid, { notes_text: newNote.trim() });
                          const updated = await getPatientNotes(pid).catch(() => []);
                          setClinicianNotes(updated);
                          setNewNote("");
                          setShowNoteForm(false);
                        } catch { /* ignore */ }
                        setAddingNote(false);
                      }

                      return (
                        <div style={{ display:"flex", flexDirection:"column", gap:"14px" }}>

                          {/* Longitudinal summary */}
                          {p.longitudinalSummary?.narrative_text && (
                            <div style={{ padding:"14px 16px", borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.7 }}>
                              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1px", marginBottom:"8px" }}>LONGITUDINAL SUMMARY</div>
                              {p.longitudinalSummary.narrative_text}
                            </div>
                          )}

                          {/* AI call notes label */}
                          {calls.length > 0 && (
                            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>AI CALL NOTES ({calls.length})</div>
                          )}

                          {calls.length === 0 ? (
                            <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>No AI call notes available.</div>
                          ) : (
                            <>
                              {pagNotes.map((call) => {
                                const isSel = selectedCall?.call_id === call.call_id;
                                const note  = isSel ? selSoap?.assessment : null;
                                return (
                                  <div
                                    key={call.call_id}
                                    onClick={() => selectCall(call)}
                                    style={{ padding:"12px 14px", borderRadius:"10px", background:isSel?t.surfaceHigh:t.bg, border:"1px solid "+(isSel?t.borderHigh:t.border), cursor:"pointer", transition:"all 0.15s" }}
                                  >
                                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"6px" }}>
                                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>
                                        {formatDate(call.started_at)}{call.day_in_recovery != null ? " · DAY " + call.day_in_recovery : ""}
                                      </span>
                                      {isSel && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand }}>SELECTED</span>}
                                    </div>
                                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.6 }}>
                                      {note || (call.status === "completed" ? "Click to load SOAP note for this call." : "Call " + (call.status || "recorded") + ".")}
                                    </div>
                                  </div>
                                );
                              })}

                              {/* Pagination */}
                              {notesTotal > 1 && (
                                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", paddingTop:"10px", borderTop:"1px solid "+t.border }}>
                                  <button
                                    onClick={() => setNotesPage(p => Math.max(0, p - 1))}
                                    disabled={safeNP === 0}
                                    style={{ padding:"6px 14px", borderRadius:"8px", background:t.surfaceHigh, border:"1px solid "+t.border, color:safeNP===0?t.textMuted:t.textSecond, fontFamily:"'DM Mono',monospace", fontSize:"10px", cursor:safeNP===0?"not-allowed":"pointer", opacity:safeNP===0?0.4:1 }}
                                  >← PREV</button>
                                  <div style={{ display:"flex", gap:"4px" }}>
                                    {Array.from({ length: notesTotal }, (_, i) => (
                                      <button
                                        key={i}
                                        onClick={() => setNotesPage(i)}
                                        style={{ width:28, height:28, borderRadius:"7px", border:"1px solid "+(i===safeNP?t.brand:t.border), background:i===safeNP?t.brandGlow:"transparent", color:i===safeNP?t.brand:t.textMuted, fontFamily:"'DM Mono',monospace", fontSize:"10px", cursor:"pointer", fontWeight:i===safeNP?700:400 }}
                                      >{i + 1}</button>
                                    ))}
                                  </div>
                                  <button
                                    onClick={() => setNotesPage(p => Math.min(notesTotal - 1, p + 1))}
                                    disabled={safeNP >= notesTotal - 1}
                                    style={{ padding:"6px 14px", borderRadius:"8px", background:t.surfaceHigh, border:"1px solid "+t.border, color:safeNP>=notesTotal-1?t.textMuted:t.textSecond, fontFamily:"'DM Mono',monospace", fontSize:"10px", cursor:safeNP>=notesTotal-1?"not-allowed":"pointer", opacity:safeNP>=notesTotal-1?0.4:1 }}
                                  >NEXT →</button>
                                </div>
                              )}
                            </>
                          )}

                          {/* Clinician-added notes */}
                          {clinicianNotes.length > 0 && (
                            <div style={{ display:"flex", flexDirection:"column", gap:"8px", paddingTop:"4px" }}>
                              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>CLINICIAN NOTES ({clinicianNotes.length})</div>
                              {clinicianNotes.map(n => (
                                <div key={n.action_id} style={{ padding:"12px 14px", borderRadius:"10px", background:t.brandGlow, border:"1px solid "+t.brand+"20" }}>
                                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"6px" }}>
                                    <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"12px", color:t.brand }}>{n.clinician_name}</span>
                                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>{formatDate(n.action_at)} {n.action_at ? new Date(n.action_at).toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"}) : ""}</span>
                                  </div>
                                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.6, whiteSpace:"pre-line" }}>{n.notes_text}</div>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Add note toggle + form */}
                          {!showNoteForm ? (
                            <button
                              onClick={() => setShowNoteForm(true)}
                              style={{ display:"flex", alignItems:"center", gap:"8px", padding:"10px 14px", borderRadius:"10px", background:"transparent", border:"1px dashed "+t.border, cursor:"pointer", width:"100%", transition:"all 0.15s" }}
                              onMouseEnter={e=>{ e.currentTarget.style.borderColor=t.brand+"60"; e.currentTarget.style.background=t.brandGlow; }}
                              onMouseLeave={e=>{ e.currentTarget.style.borderColor=t.border; e.currentTarget.style.background="transparent"; }}
                            >
                              <div style={{ width:22, height:22, borderRadius:"6px", background:t.brandGlow, border:"1px solid "+t.brand+"40", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
                                <svg style={{ width:12, height:12 }} fill="none" viewBox="0 0 24 24" stroke={t.brand} strokeWidth={2.5}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
                                </svg>
                              </div>
                              <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", fontWeight:600, color:t.textMuted }}>Add clinical note</span>
                            </button>
                          ) : (
                            <div style={{ background:t.surfaceHigh, border:"1px solid "+t.brand+"40", borderRadius:"12px", padding:"14px" }}>
                              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"10px" }}>
                                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1px" }}>ADD CLINICAL NOTE</div>
                                <button onClick={() => { setShowNoteForm(false); setNewNote(""); }} style={{ background:"none", border:"none", cursor:"pointer", color:t.textMuted, fontSize:"16px", lineHeight:1, padding:"0 2px" }}>×</button>
                              </div>
                              <textarea
                                autoFocus
                                rows={4}
                                value={newNote}
                                onChange={e => setNewNote(e.target.value)}
                                placeholder="Enter your clinical observation, review note, or care decision…"
                                style={{ width:"100%", resize:"vertical", fontFamily:"'Outfit',sans-serif", fontSize:"13px", lineHeight:1.6, color:t.textPrimary, background:t.surface, border:"1px solid "+t.border, borderRadius:"8px", padding:"9px 12px", outline:"none", boxSizing:"border-box", transition:"border-color 0.15s" }}
                                onFocus={e => e.target.style.borderColor = t.brand+"80"}
                                onBlur={e => e.target.style.borderColor = t.border}
                                onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); submitNote(); } }}
                              />
                              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginTop:"8px" }}>
                                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>CTRL+ENTER TO SAVE</span>
                                <div style={{ display:"flex", gap:"8px" }}>
                                  <button onClick={() => { setShowNoteForm(false); setNewNote(""); }} style={{ padding:"7px 14px", borderRadius:"8px", border:"1px solid "+t.border, background:"transparent", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"12px", color:t.textMuted, cursor:"pointer" }}>Cancel</button>
                                  <button
                                    onClick={submitNote}
                                    disabled={!newNote.trim() || addingNote}
                                    style={{ padding:"7px 16px", borderRadius:"8px", border:"none", background: newNote.trim() && !addingNote ? "linear-gradient(135deg,"+t.brand+","+t.brandDark+")" : t.surfaceHigh, color: newNote.trim() && !addingNote ? "#fff" : t.textMuted, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"12px", cursor: newNote.trim() && !addingNote ? "pointer" : "not-allowed", opacity: newNote.trim() && !addingNote ? 1 : 0.5, transition:"all 0.15s" }}
                                  >
                                    {addingNote ? "Saving…" : "Save Note"}
                                  </button>
                                </div>
                              </div>
                            </div>
                          )}

                        </div>
                      );
                    })()}


                  </div>
                </div>
              );
            })()}

            {/* Action feedback */}
            {actionMsg && (
              <div style={{ padding:"10px 14px", borderRadius:9, background:t.greenBg, border:"1px solid "+t.greenBorder, fontFamily:"'Outfit',sans-serif", fontSize:13, color:t.green }}>{actionMsg}</div>
            )}

            {/* Action buttons */}
            <div style={{ display:"flex", gap:"10px", flexDirection:"column" }}>
              <div style={{ display:"flex", gap:"10px" }}>
                <button
                  onClick={() => setShowEscalate(true)}
                  style={{ flex:1, padding:"13px", borderRadius:"11px", background:cfg.bg, border:"1px solid "+cfg.border, color:cfg.text, fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", cursor:"pointer", transition:"all 0.15s" }}>
                  ▲ Escalate to Team
                </button>
                <button
                  onClick={() => navigate("/scheduler", { state: { patient: { id: pid, name: p.name, rag: p.rag, score: p.score, ward: p.ward, pathway: p.pathway } } })}
                  style={{ flex:1, padding:"13px", borderRadius:"11px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", cursor:"pointer", transition:"all 0.15s" }}>
                  ◎ Schedule Probe Call
                </button>
              </div>
              <button
                onClick={() => setShowSchedule(true)}
                style={{ width:"100%", padding:"11px", borderRadius:"11px", background:t.surfaceHigh, border:"1px solid "+t.border, color:t.textSecond, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", transition:"all 0.15s", display:"flex", alignItems:"center", justifyContent:"center", gap:"8px" }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = t.brand; e.currentTarget.style.color = t.brand; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = t.border; e.currentTarget.style.color = t.textSecond; }}
              >
                <svg style={{ width:14, height:14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                View Scheduled Calls
              </button>
            </div>
          </div>
        </div>
      </div>
      <PatientChat patientId={pid} patientName={p.name}/>

      {/* Edit Details Modal */}
      {showEditModal && (() => {
        const inputStyle = {
          width: "100%", fontFamily: "'Outfit',sans-serif", fontSize: "13px",
          color: t.textPrimary, background: t.bg, border: "1px solid " + t.border,
          borderRadius: "8px", padding: "8px 12px", outline: "none",
          boxSizing: "border-box", transition: "border-color 0.15s",
        };
        const labelStyle = {
          fontFamily: "'DM Mono',monospace", fontSize: "10px",
          color: t.textMuted, letterSpacing: "1px", marginBottom: "6px", display: "block",
        };

        async function saveAll() {
          setEditSaving(true);
          setEditMsg({ text: "", ok: true });
          try {
            await updatePatient(pid, { phone_number: editPhone, preferred_call_time: editCallTime || null });
            await updateProfile(pid, {
              primary_diagnosis: editDiagnosis,
              current_medications: editMeds,
              allergies: editAllergies,
            });
            await updatePathway(pid, {
              domains: editDomains,
              risk_flags: editRiskFlags,
              clinical_red_flags: editRedFlags,
            });
            setEditMsg({ text: "Changes saved successfully.", ok: true });
            setTimeout(() => { setEditMsg({ text: "", ok: true }); setShowEditModal(false); }, 1500);
          } catch {
            setEditMsg({ text: "Failed to save. Please try again.", ok: false });
          }
          setEditSaving(false);
        }

        return (
          <div
            onClick={() => setShowEditModal(false)}
            style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.5)", zIndex:1000, display:"flex", alignItems:"center", justifyContent:"center", padding:"24px" }}
          >
            <div
              onClick={e => e.stopPropagation()}
              style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", width:"100%", maxWidth:520, maxHeight:"85vh", overflowY:"auto", boxShadow:"0 24px 80px rgba(0,0,0,0.3)" }}
            >
              {/* Header */}
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"20px 24px", borderBottom:"1px solid "+t.border }}>
                <div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"16px", color:t.textPrimary }}>Edit Patient Details</div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>{p.name} · NHS {p.nhs}</div>
                </div>
                <button onClick={() => setShowEditModal(false)} style={{ background:"none", border:"none", cursor:"pointer", color:t.textMuted, fontSize:"20px", lineHeight:1, padding:"0 4px" }}>×</button>
              </div>

              <div style={{ padding:"24px", display:"flex", flexDirection:"column", gap:"20px" }}>
                {/* Contact */}
                <div style={{ display:"flex", flexDirection:"column", gap:"12px", paddingBottom:"18px", borderBottom:"1px solid "+t.border }}>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1.5px" }}>CONTACT</div>
                  <div>
                    <label style={labelStyle}>PHONE NUMBER</label>
                    <input type="text" value={editPhone} onChange={e => setEditPhone(e.target.value)} style={inputStyle} placeholder="+44 7000 000000" onFocus={e => e.target.style.borderColor = t.brand+"80"} onBlur={e => e.target.style.borderColor = t.border}/>
                  </div>
                  <div>
                    <label style={labelStyle}>PREFERRED CALL TIME</label>
                    <input type="time" value={editCallTime} onChange={e => setEditCallTime(e.target.value)} style={inputStyle} onFocus={e => e.target.style.borderColor = t.brand+"80"} onBlur={e => e.target.style.borderColor = t.border}/>
                  </div>
                </div>

                {/* Medical Profile */}
                <div style={{ display:"flex", flexDirection:"column", gap:"14px", paddingBottom:"18px", borderBottom:"1px solid "+t.border }}>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1.5px" }}>MEDICAL PROFILE</div>
                  <div>
                    <label style={labelStyle}>PRIMARY DIAGNOSIS</label>
                    <input type="text" value={editDiagnosis} onChange={e => setEditDiagnosis(e.target.value)} style={inputStyle} placeholder="Primary diagnosis" onFocus={e => e.target.style.borderColor = t.brand+"80"} onBlur={e => e.target.style.borderColor = t.border}/>
                  </div>
                  <TagField label="CURRENT MEDICATIONS" items={editMeds} setItems={setEditMeds} newVal={newMed} setNewVal={setNewMed} placeholder="e.g. Paracetamol 500mg" t={t} inputStyle={inputStyle} labelStyle={labelStyle}/>
                  <TagField label="ALLERGIES" items={editAllergies} setItems={setEditAllergies} newVal={newAllergy} setNewVal={setNewAllergy} placeholder="e.g. Penicillin" t={t} inputStyle={inputStyle} labelStyle={labelStyle}/>
                </div>

                {/* Pathway Monitoring */}
                <div style={{ display:"flex", flexDirection:"column", gap:"14px" }}>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1.5px" }}>PATHWAY MONITORING</div>
                  <TagField label="MONITORING DOMAINS" items={editDomains} setItems={setEditDomains} newVal={newDomain} setNewVal={setNewDomain} placeholder="e.g. pain_management" t={t} inputStyle={inputStyle} labelStyle={labelStyle}/>
                  <TagField label="RISK FLAGS" items={editRiskFlags} setItems={setEditRiskFlags} newVal={newRiskFlag} setNewVal={setNewRiskFlag} placeholder="e.g. Pain score above 7" t={t} inputStyle={inputStyle} labelStyle={labelStyle}/>
                  <TagField label="CLINICAL RED FLAGS" items={editRedFlags} setItems={setEditRedFlags} newVal={newRedFlag} setNewVal={setNewRedFlag} placeholder="e.g. Sudden chest pain" t={t} inputStyle={inputStyle} labelStyle={labelStyle}/>
                </div>

                {editMsg.text && (
                  <div style={{ padding:"10px 14px", borderRadius:"8px", background:editMsg.ok?t.greenBg:t.redBg, border:"1px solid "+(editMsg.ok?t.greenBorder:t.redBorder), fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:editMsg.ok?t.green:t.red }}>{editMsg.text}</div>
                )}

                <div style={{ display:"flex", gap:"10px" }}>
                  <button onClick={() => setShowEditModal(false)} style={{ flex:1, padding:"12px", borderRadius:"10px", background:"transparent", border:"1px solid "+t.border, color:t.textMuted, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"14px", cursor:"pointer" }}>Cancel</button>
                  <button onClick={saveAll} disabled={editSaving} style={{ flex:2, padding:"12px", borderRadius:"10px", background:editSaving?t.surfaceHigh:"linear-gradient(135deg,"+t.brand+","+t.brandDark+")", border:"none", color:editSaving?t.textMuted:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", cursor:editSaving?"not-allowed":"pointer", opacity:editSaving?0.6:1, transition:"all 0.15s" }}>
                    {editSaving ? "Saving…" : "Save Changes"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
      {showEscalate && (
        <EscalateModal
          patientId={pid}
          patientName={p.name}
          onClose={() => setShowEscalate(false)}
          onDone={() => {
            setActionMsg("Escalation sent successfully.");
            setTimeout(() => setActionMsg(""), 4000);
          }}
        />
      )}
      {showSchedule && (
        <PatientScheduleModal
          patientId={pid}
          patientName={p.name}
          onClose={() => setShowSchedule(false)}
        />
      )}
    </div>
  );
}

function TagField({ label, items, setItems, newVal, setNewVal, placeholder, t, inputStyle, labelStyle }) {
  function add() {
    const v = newVal.trim();
    if (!v || items.includes(v)) return;
    setItems(prev => [...prev, v]);
    setNewVal("");
  }
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      {items.length > 0 && (
        <div style={{ display:"flex", flexWrap:"wrap", gap:"6px", marginBottom:"8px" }}>
          {items.map((item, i) => (
            <span key={i} style={{ display:"flex", alignItems:"center", gap:"4px", padding:"3px 10px", borderRadius:"999px", fontSize:"12px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand }}>
              {item}
              <button type="button" onClick={() => setItems(prev => prev.filter((_, j) => j !== i))} style={{ background:"none", border:"none", cursor:"pointer", color:t.textMuted, fontSize:"14px", lineHeight:1, padding:"0 0 0 2px", transition:"color 0.15s" }} onMouseEnter={e => e.currentTarget.style.color = t.red} onMouseLeave={e => e.currentTarget.style.color = t.textMuted}>×</button>
            </span>
          ))}
        </div>
      )}
      <div style={{ display:"flex", gap:"8px" }}>
        <input type="text" value={newVal} onChange={e => setNewVal(e.target.value)} onKeyDown={e => e.key === "Enter" && (e.preventDefault(), add())} placeholder={placeholder} style={{ ...inputStyle, flex:1, fontSize:"12px", padding:"7px 10px" }} onFocus={e => e.target.style.borderColor = t.brand+"80"} onBlur={e => e.target.style.borderColor = t.border}/>
        <button type="button" onClick={add} style={{ padding:"7px 14px", borderRadius:"8px", background:t.brand, border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"12px", cursor:"pointer", whiteSpace:"nowrap", transition:"opacity 0.15s" }} onMouseEnter={e => e.currentTarget.style.opacity="0.85"} onMouseLeave={e => e.currentTarget.style.opacity="1"}>+ Add</button>
      </div>
    </div>
  );
}

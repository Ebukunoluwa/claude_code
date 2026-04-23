import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { getDashboard } from "../api/decisions";
import { getMe } from "../api/auth";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";
import Sparkline from "../components/Sparkline";
import AddPatientModal from "../components/AddPatientModal";
import PatientScheduleModal from "../components/PatientScheduleModal";

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase();
}

function toRag(sev) {
  if (sev === "red")   return "RED";
  if (sev === "amber") return "AMBER";
  return "GREEN";
}

function timeAgoShort(iso) {
  if (!iso) return "Pending";
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60)    return "Just now";
  if (diff < 3600)  return Math.round(diff / 60) + " min ago";
  if (diff < 86400) return Math.round(diff / 3600) + "h ago";
  return new Date(iso).toLocaleDateString("en-GB", { day:"numeric", month:"short" });
}

function mapWorklist(worklist) {
  return worklist.map(p => {
    const rag   = toRag(p.urgency_severity);
    // Only use real risk_score — never generate fake scores for new patients
    const score = p.risk_score != null ? Math.round(p.risk_score) : null;
    const hasFtp = p.ftp_status && p.ftp_status !== "none" && p.ftp_status !== "green";
    return {
      id:        p.patient_id,
      name:      p.patient_name || "Unknown",
      initials:  getInitials(p.patient_name),
      age:       "—",
      bed:       "—",
      ward:      p.ward_name || p.condition || "General",
      pathway:   p.condition || "General",
      rag,
      score,
      delta:     p.risk_score_delta != null ? Math.round(p.risk_score_delta) : null,
      flag:      hasFtp ? "Failure to Progress — manual review required" : null,
      nhs:       p.nhs_number || "—",
      trend:     score != null
               ? [score - 20, score - 15, score - 10, score - 5, score - 2, score - 1, score].map(v => Math.max(0, Math.min(100, v)))
               : null,
      calls:     0,
      lastCall:  timeAgoShort(p.last_call_at),
      daysAdmitted: p.day_in_recovery || 0,
      admitted:  p.last_call_at ? new Date(p.last_call_at).toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }) : "—",
      expectedDischarge: "—",
      surgeon:   "—",
      nurse:     "—",
      nextScheduledCall: p.next_scheduled_call || null,
      _raw: p,
    };
  });
}

export default function PatientPage() {
  const { t } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const wardFilter = location.state?.ward || null;

  const [patients, setPatients]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [filter, setFilter]         = useState("ALL");
  const [mounted, setMounted]       = useState(false);
  const [search, setSearch]         = useState("");
  const [page, setPage]             = useState(0);
  const [showAddModal, setShowAddModal] = useState(false);
  const [clinician, setClinician]   = useState(null);
  const [scheduleModal, setScheduleModal] = useState(null); // { id, name }

  function changeFilter(f) { setFilter(f); setPage(0); }
  function changeSearch(v) { setSearch(v); setPage(0); }

  function loadPatients() {
    getDashboard()
      .then(data => {
        setPatients(mapWorklist(data.worklist || []));
        setTimeout(() => setMounted(true), 50);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadPatients();
    getMe().then(data => setClinician(data)).catch(() => {});
  }, []);

  // Apply ward filter from navigation state (clicking a ward card on dashboard)
  const wardPatients = wardFilter ? patients.filter(p => p.ward === wardFilter) : patients;

  // Apply RAG filter tab
  const ragFiltered = filter === "ALL" ? wardPatients : wardPatients.filter(p => p.rag === filter);

  // Apply search
  const searchTerm = search.trim().toLowerCase();
  const filtered = searchTerm
    ? ragFiltered.filter(p =>
        p.name.toLowerCase().includes(searchTerm) ||
        p.id.toLowerCase().includes(searchTerm) ||
        p.ward.toLowerCase().includes(searchTerm) ||
        p.pathway.toLowerCase().includes(searchTerm)
      )
    : ragFiltered;

  const sorted = [...filtered].sort((a, b) => ({RED:0,AMBER:1,GREEN:2}[a.rag] - {RED:0,AMBER:1,GREEN:2}[b.rag]));

  const PAGE_SIZE  = 9;
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage   = Math.min(page, totalPages - 1);
  const pageSorted = sorted.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  const counts = {
    ALL:   wardPatients.length,
    RED:   wardPatients.filter(p => p.rag === "RED").length,
    AMBER: wardPatients.filter(p => p.rag === "AMBER").length,
    GREEN: wardPatients.filter(p => p.rag === "GREEN").length,
  };

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>
      <div style={{ maxWidth:1280, margin:"0 auto", padding:"32px 24px" }}>

        {/* Header */}
        <div style={{ marginBottom:"28px", opacity:mounted?1:0, transition:"opacity 0.5s ease" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
            <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
              <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Patient Queue</h1>
              {wardFilter && (
                <div style={{ display:"flex", alignItems:"center", gap:"6px", padding:"4px 12px", borderRadius:"100px", background:t.brandGlow, border:"1px solid "+t.brand+"40" }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"1px" }}>{wardFilter.toUpperCase()}</span>
                  <button onClick={() => navigate("/patients", { replace: true, state: {} })} style={{ background:"none", border:"none", color:t.brand, cursor:"pointer", fontSize:"12px", lineHeight:1, padding:"0 0 0 4px" }}>×</button>
                </div>
              )}
            </div>
            {/* Register Patient button */}
            <button
              onClick={() => setShowAddModal(true)}
              style={{ display:"flex", alignItems:"center", gap:"8px", padding:"10px 18px", borderRadius:"10px", background:"linear-gradient(135deg,#0AAFA8,#076E69)", border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px", cursor:"pointer", boxShadow:"0 4px 16px #0AAFA840", transition:"all 0.15s" }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 8px 24px #0AAFA860"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 4px 16px #0AAFA840"; }}
            >
              <svg style={{ width:14, height:14 }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
              </svg>
              Register Patient
            </button>
          </div>
          <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>Post-discharge monitoring · {new Date().toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long"})}</p>
        </div>

        {/* Stat strip — clickable filters */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"24px" }}>
          {[
            { label:"Total",            val:counts.ALL,   color:t.brand, icon:"◈", bg:t.brand+"15", key:"ALL"   },
            { label:"RED — Escalate",   val:counts.RED,   color:t.red,   icon:"▲", bg:t.red+"15",   key:"RED"   },
            { label:"AMBER — Monitor",  val:counts.AMBER, color:t.amber, icon:"◉", bg:t.amber+"15", key:"AMBER" },
            { label:"GREEN — On Track", val:counts.GREEN, color:t.green, icon:"◎", bg:t.green+"15", key:"GREEN" },
          ].map((s, i) => {
            const active = filter === s.key;
            return (
              <div
                key={i}
                onClick={() => changeFilter(active ? "ALL" : s.key)}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 12px 36px "+t.shadow; e.currentTarget.style.borderColor = s.color+"50"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 2px 12px "+t.shadow; e.currentTarget.style.borderColor = active ? s.color+"60" : t.border; }}
                style={{
                  background: active ? s.bg : t.surface,
                  border: "1px solid " + (active ? s.color+"60" : t.border),
                  borderRadius:"14px", padding:"18px 20px",
                  boxShadow: active ? "0 4px 24px "+s.color+"20" : "0 2px 12px "+t.shadow,
                  animation:"fadeUp 0.4s ease "+(i*60)+"ms both",
                  cursor:"pointer",
                  transition:"all 0.2s ease",
                  position:"relative", overflow:"hidden",
                }}
              >
                {active && <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+s.color+",transparent)" }}/>}
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"10px" }}>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color: active ? s.color : t.textMuted, letterSpacing:"1.5px" }}>{s.label.toUpperCase()}</div>
                  <div style={{ width:30, height:30, borderRadius:"8px", background: active ? s.color+"25" : s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:"13px", color:s.color }}>{s.icon}</div>
                </div>
                <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"42px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{loading?"—":s.val}</div>
                {active && <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:s.color, marginTop:"6px", letterSpacing:"1px" }}>FILTERED ✓</div>}
              </div>
            );
          })}
        </div>

        {/* Search row */}
        <div style={{ display:"flex", gap:"12px", marginBottom:"20px", alignItems:"center" }}>
          <div style={{ position:"relative", flex:1, maxWidth:"380px" }}>
            <svg style={{ position:"absolute", left:"12px", top:"50%", transform:"translateY(-50%)", width:14, height:14, pointerEvents:"none" }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
            </svg>
            <input
              value={search}
              onChange={e => changeSearch(e.target.value)}
              placeholder="Search name, ID, ward…"
              style={{ width:"100%", padding:"9px 12px 9px 36px", borderRadius:"10px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, outline:"none", boxSizing:"border-box", transition:"border-color 0.15s" }}
              onFocus={e => e.target.style.borderColor = t.brand}
              onBlur={e => e.target.style.borderColor = t.border}
            />
            {search && (
              <button onClick={() => changeSearch("")} style={{ position:"absolute", right:"10px", top:"50%", transform:"translateY(-50%)", background:"none", border:"none", color:t.textMuted, cursor:"pointer", fontSize:"14px", lineHeight:1 }}>×</button>
            )}
          </div>

          {/* Active filter pill */}
          {filter !== "ALL" && (
            <div style={{ display:"flex", alignItems:"center", gap:"6px", padding:"6px 12px", borderRadius:"100px", background: filter==="RED"?t.redBg:filter==="AMBER"?t.amberBg:t.greenBg, border:"1px solid "+(filter==="RED"?t.redBorder:filter==="AMBER"?t.amberBorder:t.greenBorder) }}>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color: filter==="RED"?t.red:filter==="AMBER"?t.amber:t.green, fontWeight:600 }}>{filter}</span>
              <button onClick={() => changeFilter("ALL")} style={{ background:"none", border:"none", color: filter==="RED"?t.red:filter==="AMBER"?t.amber:t.green, cursor:"pointer", fontSize:"13px", lineHeight:1, padding:"0 0 0 2px" }}>×</button>
            </div>
          )}

          {search && (
            <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, whiteSpace:"nowrap" }}>
              {sorted.length} result{sorted.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {loading ? (
          <div style={{ padding:24, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>Loading patients…</div>
        ) : sorted.length === 0 ? (
          <div style={{ padding:24, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>
            {search ? `No patients matching "${search}".` : "No patients in this filter."}
          </div>
        ) : (
          <>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))", gap:"16px" }}>
            {pageSorted.map((p, i) => {
              const cfg = ragCfg(t, p.rag);
              return (
                <div key={p.id}
                  onClick={() => navigate("/patients/" + p.id, { state: { patient: p } })}
                  onMouseEnter={e=>{ e.currentTarget.style.transform="translateY(-3px)"; e.currentTarget.style.boxShadow="0 16px 48px "+t.shadow; e.currentTarget.style.borderColor=cfg.border; }}
                  onMouseLeave={e=>{ e.currentTarget.style.transform="translateY(0)"; e.currentTarget.style.boxShadow="0 2px 12px "+t.shadow; e.currentTarget.style.borderColor=p.rag==="RED"?t.redBorder:t.border; }}
                  style={{ background:t.surface, border:"1px solid "+(p.rag==="RED"?t.redBorder:t.border), borderRadius:"16px", padding:"20px 22px", cursor:"pointer", transition:"all 0.2s ease", boxShadow:"0 2px 12px "+t.shadow, position:"relative", overflow:"hidden", animation:"fadeUp 0.4s ease "+(i*60+200)+"ms both" }}
                >
                  {p.rag === "RED" && <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+t.red+",transparent)" }}/>}

                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"12px" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                      <div style={{ width:40, height:40, borderRadius:"50%", background:cfg.bg, border:"1.5px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontSize:"13px", fontWeight:700, color:cfg.text, fontFamily:"'Outfit',sans-serif" }}>{p.initials}</div>
                      <div>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:t.textPrimary }}>{p.name}</div>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>{p.id} · {p.age}y · {p.bed}</div>
                      </div>
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:"5px", padding:"4px 10px", borderRadius:"100px", background:cfg.bg, border:"1px solid "+cfg.border, boxShadow:cfg.glow }}>
                      <span style={{ width:6, height:6, borderRadius:"50%", background:cfg.dot, display:"inline-block", animation:p.rag==="RED"?"pulse 1.5s infinite":"none" }}/>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", fontWeight:700, color:cfg.text }}>{p.rag}</span>
                    </div>
                  </div>

                  <div style={{ display:"flex", alignItems:"center", gap:"6px", marginBottom:"12px" }}>
                    <span style={{ padding:"3px 8px", borderRadius:"6px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{p.ward}</span>
                    <span style={{ color:t.textMuted, fontSize:"12px" }}>→</span>
                    <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500 }}>{p.pathway}</span>
                  </div>

                  {p.flag && (
                    <div style={{ padding:"8px 12px", borderRadius:"8px", background:cfg.bg, border:"1px solid "+cfg.border, fontSize:"11.5px", color:cfg.text, marginBottom:"12px", display:"flex", alignItems:"center", gap:"8px", fontFamily:"'Outfit',sans-serif" }}>
                      <span style={{ fontSize:"8px", flexShrink:0 }}>▲</span>{p.flag}
                    </div>
                  )}

                  <div style={{ display:"flex", alignItems:"flex-end", justifyContent:"space-between" }}>
                    <div>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginBottom:"4px", letterSpacing:"1px" }}>RISK SCORE</div>
                      <div style={{ display:"flex", alignItems:"baseline", gap:"8px" }}>
                        {p.score != null ? (
                          <>
                            <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:cfg.text, lineHeight:1 }}>{p.score}</span>
                            {p.delta != null && p.delta !== 0 && (
                              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:p.delta > 0 ? t.red : t.green }}>{p.delta > 0 ? "▲" : "▼"} {Math.abs(p.delta)}</span>
                            )}
                          </>
                        ) : (
                          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"14px", color:t.textMuted }}>Awaiting first call</span>
                        )}
                      </div>
                    </div>
                    <div style={{ textAlign:"right" }}>
                      {p.trend && <Sparkline data={p.trend} color={cfg.dot}/>}
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"4px" }}>{p.calls} calls · {p.lastCall}</div>
                    </div>
                  </div>

                  <div style={{ marginTop:"12px", paddingTop:"10px", borderTop:"1px solid "+t.border, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <div>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>ADMITTED {p.admitted.toUpperCase()}</span>
                      {p.nextScheduledCall && (
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, marginTop:"2px" }}>
                          NEXT: {new Date(p.nextScheduledCall).toLocaleString("en-GB", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" })}
                        </div>
                      )}
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:"8px" }}>
                      <button
                        onClick={e => { e.stopPropagation(); setScheduleModal({ id: p.id, name: p.name }); }}
                        style={{ padding:"3px 10px", borderRadius:"6px", background:t.brandGlow, border:"1px solid "+t.brand+"40", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, cursor:"pointer", letterSpacing:"0.5px" }}
                        onMouseEnter={e => { e.currentTarget.style.background = t.brand+"20"; }}
                        onMouseLeave={e => { e.currentTarget.style.background = t.brandGlow; }}
                      >SCHEDULE</button>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand }}>VIEW DETAIL →</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"6px", marginTop:"28px" }}>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={safePage === 0}
                style={{ width:32, height:32, borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, color:safePage===0?t.textMuted:t.textPrimary, cursor:safePage===0?"default":"pointer", fontSize:"16px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:safePage===0?0.35:1 }}
              >‹</button>

              {Array.from({ length: totalPages }, (_, i) => {
                const show = i === 0 || i === totalPages - 1 || Math.abs(i - safePage) <= 1;
                if (!show) {
                  if (i === 1 && safePage > 2) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", color:t.textMuted, padding:"0 2px" }}>…</span>;
                  if (i === totalPages - 2 && safePage < totalPages - 3) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", color:t.textMuted, padding:"0 2px" }}>…</span>;
                  return null;
                }
                const active = i === safePage;
                return (
                  <button key={i} onClick={() => setPage(i)}
                    style={{ width:32, height:32, borderRadius:"8px", background:active?t.brand:t.surface, border:"1px solid "+(active?t.brand:t.border), color:active?"#fff":t.textPrimary, cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"12px", fontWeight:active?700:400, transition:"all 0.15s" }}>
                    {i + 1}
                  </button>
                );
              })}

              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={safePage === totalPages - 1}
                style={{ width:32, height:32, borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, color:safePage===totalPages-1?t.textMuted:t.textPrimary, cursor:safePage===totalPages-1?"default":"pointer", fontSize:"16px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:safePage===totalPages-1?0.35:1 }}
              >›</button>

              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginLeft:"8px" }}>
                {safePage * PAGE_SIZE + 1}–{Math.min((safePage + 1) * PAGE_SIZE, sorted.length)} of {sorted.length}
              </span>
            </div>
          )}
          </>
        )}
      </div>

      {showAddModal && (
        <AddPatientModal
          clinician={clinician || { hospital_id: null }}
          onClose={() => setShowAddModal(false)}
          onAdded={() => { setShowAddModal(false); loadPatients(); }}
        />
      )}

      {scheduleModal && (
        <PatientScheduleModal
          patientId={scheduleModal.id}
          patientName={scheduleModal.name}
          onClose={() => setScheduleModal(null)}
        />
      )}
    </div>
  );
}

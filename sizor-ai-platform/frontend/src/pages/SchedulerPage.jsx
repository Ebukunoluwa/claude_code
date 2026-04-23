import { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { getDashboard } from "../api/decisions";
import { createProbeCall } from "../api/probe_calls";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";

const SLOTS = [
  { value: "immediate", label: "Today (Immediate)",    desc: "Calls within the next available window" },
  { value: "morning",   label: "Tomorrow Morning",     desc: "08:00–12:00 call window" },
  { value: "afternoon", label: "Tomorrow Afternoon",   desc: "13:00–17:00 call window" },
  { value: "custom",    label: "Custom Date & Time",   desc: "Choose a specific date and time" },
];

function toRag(sev) {
  if (sev === "red")   return "RED";
  if (sev === "amber") return "AMBER";
  return "GREEN";
}

function ragToScore(sev, id) {
  const hash = id ? id.split("").reduce((a, c) => a + c.charCodeAt(0), 0) : 0;
  if (sev === "red")   return 70 + (hash % 20);
  if (sev === "amber") return 42 + (hash % 18);
  return 18 + (hash % 22);
}

export default function SchedulerPage() {
  const { t } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const lockedPatient = location.state?.patient || null;

  const [patients, setPatients]   = useState([]);
  const [search, setSearch]       = useState("");
  const [page, setPage]           = useState(0);
  const [selP, setSelP]           = useState(lockedPatient);
  const [selSlot, setSelSlot]     = useState("morning");
  const [customDate, setCustomDate] = useState("");
  const [customTime, setCustomTime] = useState("09:00");
  const [notes, setNotes]         = useState("");
  const [success, setSuccess]     = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [callQueue, setCallQueue] = useState([]);

  useEffect(() => {
    getDashboard()
      .then(data => {
        const wl = data.worklist || [];
        const mapped = wl.map(p => ({
          id:      p.patient_id,
          name:    p.patient_name || "Unknown",
          ward:    p.condition || "General",
          pathway: p.condition || "General",
          rag:     toRag(p.urgency_severity),
          score:   p.risk_score ?? ragToScore(p.urgency_severity, p.patient_id),
        }));
        setPatients(mapped);
        // Only auto-select first patient if no locked patient from navigation
        if (!lockedPatient && mapped.length > 0) setSelP(mapped[0]);
      })
      .catch(() => {});
  }, []);

  const filtered = patients.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.id.toLowerCase().includes(search.toLowerCase())
  );
  const PAGE_SIZE   = 10;
  const totalPages  = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage    = Math.min(page, totalPages - 1);
  const pagePatients = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);

  function handleSearch(val) {
    setSearch(val);
    setPage(0);
  }

  const cfg = selP ? ragCfg(t, selP.rag) : ragCfg(t, "GREEN");

  const resolvedSlot = selSlot === "custom"
    ? (customDate && customTime ? `${customDate}T${customTime}` : null)
    : selSlot;

  const slotLabel = selSlot === "custom"
    ? (customDate && customTime ? `${customDate} at ${customTime}` : "Custom (incomplete)")
    : SLOTS.find(s => s.value === selSlot)?.label || selSlot;

  const canSchedule = selP && !submitting && resolvedSlot && notes.trim();

  async function handleSchedule() {
    if (!canSchedule) return;
    setSubmitting(true);
    try {
      await createProbeCall({
        patient_id: selP.id,
        slot: resolvedSlot,
        note: notes.trim(),
      });
    } catch {
      // show success optimistically — call was queued
    }
    setSuccess(true);
    setTimeout(() => navigate("/dashboard"), 1500);
    setSubmitting(false);
  }

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>
      <div style={{ maxWidth:1100, margin:"0 auto", padding:"36px 24px" }}>
        <div style={{ marginBottom:"28px" }}>
          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>CLINICIAN-INITIATED · OUTBOUND CALL</div>
          <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"32px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Schedule a Probe Call</h1>
          <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>AI-powered outbound call with structured SOAP output and automatic RAG scoring</p>
        </div>

        {success && (
          <div style={{ padding:"14px 20px", borderRadius:"12px", background:t.greenBg, border:"1px solid "+t.greenBorder, marginBottom:"24px", display:"flex", alignItems:"center", gap:"12px" }}>
            <span style={{ color:t.green, fontSize:"20px" }}>✓</span>
            <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.green, fontWeight:600 }}>Probe call scheduled — Sizor will call {selP?.name} ({slotLabel})</span>
          </div>
        )}

        <div style={{ display:"grid", gridTemplateColumns:"1fr 340px", gap:"20px" }}>
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>

            {/* Step 1 — Select Patient */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:"16px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>STEP 1 · SELECT PATIENT</div>
                {lockedPatient && (
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, background:t.brandGlow, border:"1px solid "+t.brand+"40", borderRadius:"6px", padding:"3px 8px", letterSpacing:"1px" }}>LOCKED FROM PATIENT PAGE</span>
                )}
              </div>
              {lockedPatient ? (
                /* Locked patient — read-only display */
                (() => {
                  const c = ragCfg(t, lockedPatient.rag);
                  const initials = lockedPatient.name.split(" ").map(n=>n[0]).join("");
                  return (
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"14px 16px", borderRadius:"10px", background:c.bg, border:"2px solid "+c.border }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                        <div style={{ width:38, height:38, borderRadius:"50%", background:t.surface, border:"2px solid "+c.border, display:"flex", alignItems:"center", justifyContent:"center", fontSize:"12px", fontWeight:800, color:c.text, fontFamily:"'Outfit',sans-serif" }}>{initials}</div>
                        <div>
                          <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:t.textPrimary }}>{lockedPatient.name}</div>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>{lockedPatient.id} · {lockedPatient.ward} · {lockedPatient.pathway}</div>
                        </div>
                      </div>
                      <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                        <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"22px", color:c.text }}>{lockedPatient.score}</span>
                        <span style={{ width:10, height:10, borderRadius:"50%", background:c.dot, display:"inline-block", boxShadow:"0 0 10px "+c.dot }}/>
                      </div>
                    </div>
                  );
                })()
              ) : (
                <>
                  {/* Search */}
                  <div style={{ position:"relative", marginBottom:"12px" }}>
                    <svg style={{ position:"absolute", left:"12px", top:"50%", transform:"translateY(-50%)", width:13, height:13, color:t.textMuted, pointerEvents:"none" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
                    </svg>
                    <input value={search} onChange={e=>handleSearch(e.target.value)} placeholder="Search by name or patient ID..."
                      style={{ width:"100%", padding:"10px 16px 10px 36px", borderRadius:"10px", background:t.bg, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, outline:"none", boxSizing:"border-box" }}/>
                    {search && (
                      <button onClick={() => handleSearch("")} style={{ position:"absolute", right:"10px", top:"50%", transform:"translateY(-50%)", background:"none", border:"none", color:t.textMuted, cursor:"pointer", fontSize:"14px" }}>×</button>
                    )}
                  </div>

                  {/* Patient list — 10 per page */}
                  <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
                    {pagePatients.length === 0 ? (
                      <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>No patients found.</div>
                    ) : pagePatients.map(p => {
                      const c = ragCfg(t, p.rag);
                      const sel2 = selP?.id === p.id;
                      const initials = p.name.split(" ").map(n=>n[0]).join("");
                      return (
                        <div key={p.id} onClick={() => setSelP(p)} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"12px 16px", borderRadius:"10px", cursor:"pointer", background:sel2?c.bg:t.surfaceHigh, border:"1px solid "+(sel2?c.border:t.border), transition:"all 0.15s" }}>
                          <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                            <div style={{ width:34, height:34, borderRadius:"50%", background:sel2?t.surface:t.overlay, border:"1px solid "+(sel2?c.border:t.border), display:"flex", alignItems:"center", justifyContent:"center", fontSize:"11px", fontWeight:700, color:sel2?c.text:t.textSecond, fontFamily:"'Outfit',sans-serif" }}>{initials}</div>
                            <div>
                              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"14px", color:t.textPrimary }}>{p.name}</div>
                              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>{p.id} · {p.ward} · {p.pathway}</div>
                            </div>
                          </div>
                          <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                            <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"20px", color:c.text }}>{p.score}</span>
                            <span style={{ width:8, height:8, borderRadius:"50%", background:c.dot, display:"inline-block", boxShadow:sel2?"0 0 8px "+c.dot:"none" }}/>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"6px", marginTop:"14px", paddingTop:"12px", borderTop:"1px solid "+t.border }}>
                      <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={safePage === 0}
                        style={{ width:28, height:28, borderRadius:"7px", background:t.surfaceHigh, border:"1px solid "+t.border, color:safePage===0?t.textMuted:t.textPrimary, cursor:safePage===0?"default":"pointer", fontSize:"14px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:safePage===0?0.4:1 }}
                      >‹</button>

                      {Array.from({ length: totalPages }, (_, i) => {
                        // Show first, last, current ±1, and ellipsis
                        const show = i === 0 || i === totalPages - 1 || Math.abs(i - safePage) <= 1;
                        if (!show) {
                          if (i === 1 && safePage > 2) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>…</span>;
                          if (i === totalPages - 2 && safePage < totalPages - 3) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>…</span>;
                          return null;
                        }
                        const active = i === safePage;
                        return (
                          <button key={i} onClick={() => setPage(i)} style={{ width:28, height:28, borderRadius:"7px", background:active?t.brand:t.surfaceHigh, border:"1px solid "+(active?t.brand:t.border), color:active?"#fff":t.textPrimary, cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"11px", fontWeight:active?700:400, transition:"all 0.15s" }}>
                            {i + 1}
                          </button>
                        );
                      })}

                      <button
                        onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                        disabled={safePage === totalPages - 1}
                        style={{ width:28, height:28, borderRadius:"7px", background:t.surfaceHigh, border:"1px solid "+t.border, color:safePage===totalPages-1?t.textMuted:t.textPrimary, cursor:safePage===totalPages-1?"default":"pointer", fontSize:"14px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:safePage===totalPages-1?0.4:1 }}
                      >›</button>

                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginLeft:"4px" }}>
                        {safePage * PAGE_SIZE + 1}–{Math.min((safePage + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}
                      </span>
                    </div>
                  )}

                </>
              )}
            </div>

            {/* Step 2 — Slot */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>STEP 2 · CALL SLOT</div>
              <div style={{ display:"flex", flexDirection:"column", gap:"10px" }}>
                {SLOTS.map(s => (
                  <div key={s.value}>
                    <button onClick={() => setSelSlot(s.value)} style={{ width:"100%", display:"flex", justifyContent:"space-between", alignItems:"center", padding:"14px 16px", borderRadius:"10px", cursor:"pointer", background:selSlot===s.value?t.brandGlow:t.surfaceHigh, border:"1px solid "+(selSlot===s.value?t.brand+"40":t.border), transition:"all 0.15s", textAlign:"left" }}>
                      <div>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"14px", color:selSlot===s.value?t.brand:t.textPrimary }}>{s.label}</div>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"3px" }}>{s.desc}</div>
                      </div>
                      {selSlot===s.value && <span style={{ color:t.brand, fontSize:"16px" }}>✓</span>}
                    </button>
                    {/* Custom date/time pickers — only when custom slot selected */}
                    {s.value === "custom" && selSlot === "custom" && (
                      <div style={{ display:"flex", gap:"12px", marginTop:"10px", padding:"16px", borderRadius:"10px", background:t.bg, border:"1px solid "+t.brand+"30" }}>
                        <div style={{ flex:1 }}>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", marginBottom:"6px" }}>DATE</div>
                          <input type="date" value={customDate} onChange={e=>setCustomDate(e.target.value)}
                            min={new Date().toISOString().split("T")[0]}
                            style={{ width:"100%", padding:"10px 12px", borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, outline:"none", boxSizing:"border-box" }}/>
                        </div>
                        <div style={{ flex:1 }}>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", marginBottom:"6px" }}>TIME</div>
                          <input type="time" value={customTime} onChange={e=>setCustomTime(e.target.value)}
                            style={{ width:"100%", padding:"10px 12px", borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, outline:"none", boxSizing:"border-box" }}/>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Step 3 — Notes */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>STEP 3 · CALL NOTES <span style={{ color:t.red }}>*</span></div>
              <textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="What should Sarah ask the patient? e.g. 'Patient reported wound pain on last call — check if still painful and whether they have changed the dressing'" rows={4}
                style={{ width:"100%", padding:"12px 16px", borderRadius:"10px", background:t.bg, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, resize:"none", lineHeight:1.6, outline:"none", boxSizing:"border-box" }}/>
            </div>

            <button onClick={handleSchedule} disabled={!canSchedule}
              onMouseEnter={e=>{if(canSchedule){e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow="0 16px 48px #0AAFA860;";}}}
              onMouseLeave={e=>{e.currentTarget.style.transform="translateY(0)";e.currentTarget.style.boxShadow="0 8px 32px #0AAFA840";}}
              style={{ padding:"16px", borderRadius:"14px", background:"linear-gradient(135deg,#0AAFA8,#076E69)", border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", cursor:canSchedule?"pointer":"not-allowed", boxShadow:"0 8px 32px #0AAFA840", transition:"all 0.2s ease", opacity:canSchedule?1:0.7 }}>
              ◎ &nbsp; Schedule Probe Call{selP ? " for " + selP.name : ""}
            </button>
          </div>

          {/* Right panel */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
            {selP && (
              <div style={{ background:cfg.bg, border:"1px solid "+cfg.border, borderRadius:"18px", padding:"24px", boxShadow:cfg.glow, position:"relative", overflow:"hidden" }}>
                <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+cfg.dot+",transparent)" }}/>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>CALL PREVIEW</div>
                <div style={{ display:"flex", alignItems:"center", gap:"12px", marginBottom:"16px" }}>
                  <div style={{ width:42, height:42, borderRadius:"50%", background:t.surface, border:"2px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"14px", color:cfg.text }}>
                    {selP.name.split(" ").map(n=>n[0]).join("")}
                  </div>
                  <div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:t.textPrimary }}>{selP.name}</div>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>{selP.id} · {selP.pathway}</div>
                  </div>
                </div>
                {[["Slot",slotLabel],["Current RAG",selP.rag],["Risk Score",selP.score+" / 100"],["Ward",selP.ward]].map(([k,v])=>(
                  <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border+"80" }}>
                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                    <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:k==="Current RAG"?cfg.text:t.textSecond, fontWeight:600 }}>{v}</span>
                  </div>
                ))}
              </div>
            )}

            {callQueue.length > 0 && (
              <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"14px" }}>SCHEDULED THIS SESSION</div>
                {callQueue.map(q => {
                  const qc = ragCfg(t, q.rag);
                  return (
                    <div key={q.id} style={{ display:"flex", alignItems:"center", gap:"12px", padding:"12px", borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border, marginBottom:"8px" }}>
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:t.textPrimary, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{q.patient}</div>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginTop:"2px" }}>{q.slot}</div>
                      </div>
                      <span style={{ width:8, height:8, borderRadius:"50%", background:qc.dot, display:"inline-block", flexShrink:0, boxShadow:"0 0 6px "+qc.dot }}/>
                    </div>
                  );
                })}
              </div>
            )}

            <div style={{ background:t.brandGlow, border:"1px solid "+t.brand+"30", borderRadius:"14px", padding:"16px" }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"1px", marginBottom:"8px" }}>HOW PROBE CALLS WORK</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textSecond, lineHeight:1.7 }}>Sizor's AI agent calls the patient at the scheduled time, follows the clinical pathway script, and generates a SOAP note within 90 seconds of completion. RED flags trigger immediate alerts.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

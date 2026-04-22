import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboard } from "../api/decisions";
import { actionReview, getEscalationsInbox, resolveFlag } from "../api/patients";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";
import PatientChat from "../components/PatientChat";
import EscalateModal from "../components/EscalateModal";

function toRag(severity) {
  if (severity === "red")   return "RED";
  if (severity === "amber") return "AMBER";
  return "GREEN";
}

function timeAgoShort(iso) {
  if (!iso) return "Unknown";
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60)    return "Just now";
  if (diff < 3600)  return Math.round(diff / 60) + " min ago";
  if (diff < 86400) return Math.round(diff / 3600) + "h ago";
  return new Date(iso).toLocaleDateString("en-GB", { day:"numeric", month:"short" });
}

function formatTs(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" });
}

function buildAlerts(worklist) {
  return worklist
    .filter(p => ["red","amber"].includes(p.urgency_severity))
    .map((p, i) => {
      const rag = toRag(p.urgency_severity);
      const hasFtp = p.ftp_status && p.ftp_status !== "none" && p.ftp_status !== "green";
      const initials = p.patient_name ? p.patient_name.split(" ").map(n=>n[0]).join("") : "?";
      return {
        id:       "alert-" + i,
        type:     "system",
        patient:  p.patient_name || "Unknown Patient",
        pid:      p.patient_id,
        age:      "—",
        ward:     p.condition || "General",
        pathway:  p.condition || "General",
        rag,
        trigger:  hasFtp ? "Failure to Progress" : rag === "RED" ? "Red Flag Escalation" : "Amber Watch",
        detail:   hasFtp
          ? "Failure to Progress detected. Manual review required."
          : "Patient requires monitoring. Check latest SOAP note.",
        time:     p.last_call_at ? timeAgoShort(p.last_call_at) : "Pending",
        ts:       p.last_call_at ? formatTs(p.last_call_at) : "—",
        score:    rag === "RED" ? 80 : 50,
        read:     !!p.reviewed,
        escalated: rag === "RED",
        initials,
        patientData: p,
      };
    });
}

function buildInboxAlerts(inbox) {
  return inbox.map((e, i) => {
    const initials = e.patient_name ? e.patient_name.split(" ").map(n=>n[0]).join("") : "?";
    return {
      id:       "inbox-" + i,
      flag_id:  e.flag_id,
      type:     "escalation",
      patient:  e.patient_name,
      pid:      e.patient_id,
      ward:     e.condition || "General",
      pathway:  e.condition || "General",
      rag:      toRag(e.severity),
      trigger:  "Escalated by " + (e.from_clinician || "Colleague"),
      detail:   e.note || "No note provided.",
      time:     e.raised_at ? timeAgoShort(e.raised_at) : "—",
      ts:       e.raised_at ? formatTs(e.raised_at) : "—",
      score:    50,
      read:     e.status === "resolved",
      escalated: true,
      fromClinician: e.from_clinician,
      initials,
      age: "—",
    };
  });
}

export default function AlertsPage() {
  const { t }     = useTheme();
  const navigate  = useNavigate();
  const [alerts, setAlerts]         = useState([]);
  const [inbox, setInbox]           = useState([]);
  const [loading, setLoading]       = useState(true);
  const [inboxLoading, setInboxLoading] = useState(true);
  const [sel, setSel]               = useState(null);
  const [tab, setTab]               = useState("system"); // "system" | "inbox"
  const [filter, setFilter]         = useState("ALL");
  const [actionBusy, setActionBusy] = useState(null);
  const [actionMsg, setActionMsg]   = useState("");
  const [showEscalate, setShowEscalate] = useState(false);
  const [alertPage, setAlertPage]       = useState(0);
  const ALERT_PAGE_SIZE = 5;

  useEffect(() => {
    getDashboard()
      .then(data => {
        const built = buildAlerts(data.worklist || []);
        setAlerts(built);
        if (tab === "system" && built.length > 0) setSel(built[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    getEscalationsInbox()
      .then(data => {
        const built = buildInboxAlerts(data);
        setInbox(built);
        if (tab === "inbox" && built.length > 0) setSel(built[0]);
      })
      .catch(() => {})
      .finally(() => setInboxLoading(false));
  }, []);

  const activeList = tab === "system" ? alerts : inbox;
  const unread  = alerts.filter(a => !a.read).length;
  const inboxUnread = inbox.filter(a => !a.read).length;
  const counts  = { ALL:activeList.length, RED:activeList.filter(a=>a.rag==="RED").length, AMBER:activeList.filter(a=>a.rag==="AMBER").length, UNREAD:activeList.filter(a=>!a.read).length };
  const filtered = filter==="ALL" ? activeList : filter==="UNREAD" ? activeList.filter(a=>!a.read) : activeList.filter(a=>a.rag===filter);
  const alertTotalPages = Math.max(1, Math.ceil(filtered.length / ALERT_PAGE_SIZE));
  const alertSafePage   = Math.min(alertPage, alertTotalPages - 1);
  const pageAlerts      = filtered.slice(alertSafePage * ALERT_PAGE_SIZE, alertSafePage * ALERT_PAGE_SIZE + ALERT_PAGE_SIZE);

  function switchTab(newTab) {
    setTab(newTab);
    setFilter("ALL");
    setAlertPage(0);
    const list = newTab === "system" ? alerts : inbox;
    setSel(list.length > 0 ? list[0] : null);
  }

  return (
    <>
      <div style={{ minHeight:"100vh", background:t.bg, display:"flex", flexDirection:"column", transition:"background 0.3s" }}>
        <Nav/>
        <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

          {/* ── List panel ── */}
          <div style={{ width:400, borderRight:"1px solid "+t.border, display:"flex", flexDirection:"column", flexShrink:0 }}>

            {/* Tab switcher */}
            <div style={{ padding:"12px 14px", borderBottom:"1px solid "+t.border, background:t.surface, display:"flex", gap:"6px" }}>
              {[
                { key:"system", label:"System Alerts", count:unread },
                { key:"inbox",  label:"My Inbox",      count:inboxUnread },
              ].map(({ key, label, count }) => (
                <button
                  key={key}
                  onClick={() => switchTab(key)}
                  style={{
                    flex:1, padding:"8px 10px", borderRadius:"10px",
                    background: tab === key ? t.surfaceHigh : "transparent",
                    border:"1px solid "+(tab === key ? t.borderHigh : "transparent"),
                    fontFamily:"'DM Mono',monospace", fontSize:"9px", fontWeight:600,
                    color: tab === key ? t.textPrimary : t.textMuted,
                    cursor:"pointer", transition:"all 0.15s",
                    display:"flex", alignItems:"center", justifyContent:"center", gap:"6px",
                  }}>
                  {label}
                  {count > 0 && (
                    <span style={{ padding:"1px 5px", borderRadius:"100px", background:key==="inbox"?t.brand:t.red, color:"#fff", fontSize:"9px", fontFamily:"'DM Mono',monospace" }}>
                      {count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Filter pills */}
            <div style={{ padding:"10px 14px", borderBottom:"1px solid "+t.border, background:t.surface, display:"flex", gap:"6px", alignItems:"center", flexWrap:"wrap" }}>
              {[["ALL",counts.ALL],["RED",counts.RED],["AMBER",counts.AMBER],["UNREAD",counts.UNREAD]].map(([f,c])=>(
                <button key={f} onClick={()=>{ setFilter(f); setAlertPage(0); }} style={{ padding:"4px 10px", borderRadius:"100px", cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"9px", fontWeight:600, background:filter===f?(f==="RED"?t.redBg:f==="AMBER"?t.amberBg:t.surfaceHigh):"transparent", border:"1px solid "+(filter===f?(f==="RED"?t.redBorder:f==="AMBER"?t.amberBorder:t.borderHigh):"transparent"), color:filter===f?(f==="RED"?t.red:f==="AMBER"?t.amber:t.textPrimary):t.textMuted, transition:"all 0.15s" }}>{f}({c})</button>
              ))}
            </div>

            <div style={{ flex:1, overflowY:"auto", background:t.bg }}>
              {(tab === "system" ? loading : inboxLoading) ? (
                <div style={{ padding:24, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>Loading…</div>
              ) : filtered.length === 0 ? (
                <div style={{ padding:24, display:"flex", flexDirection:"column", alignItems:"center", gap:"10px" }}>
                  <div style={{ width:40, height:40, borderRadius:"12px", background:t.surfaceHigh, border:"1px solid "+t.border, display:"flex", alignItems:"center", justifyContent:"center" }}>
                    <svg style={{ width:20, height:20 }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                  </div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13, textAlign:"center" }}>
                    {tab === "inbox" ? "No escalations in your inbox" : "No alerts in this filter."}
                  </div>
                </div>
              ) : pageAlerts.map(a => {
                const cfg = ragCfg(t, a.rag);
                const isSelected = sel?.id === a.id;
                return (
                  <div key={a.id} onClick={() => setSel(a)}
                    onMouseEnter={e=>{ if(!isSelected) e.currentTarget.style.background=t.surfaceHigh; }}
                    onMouseLeave={e=>{ if(!isSelected) e.currentTarget.style.background="transparent"; }}
                    style={{ padding:"14px 18px", cursor:"pointer", background:isSelected?t.surface:"transparent", borderLeft:"3px solid "+(isSelected?cfg.dot:(a.read?t.border:cfg.border)), borderBottom:"1px solid "+t.border, transition:"all 0.15s", position:"relative" }}>
                    {!a.read && <div style={{ position:"absolute", top:"50%", right:14, transform:"translateY(-50%)", width:7, height:7, borderRadius:"50%", background:cfg.dot, boxShadow:"0 0 6px "+cfg.dot }}/>}
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", color:t.textPrimary }}>{a.patient}</div>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{a.time}</div>
                    </div>
                    {a.type === "escalation" && a.fromClinician && (
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, marginBottom:"4px" }}>
                        FROM {a.fromClinician.toUpperCase()}
                      </div>
                    )}
                    <div style={{ display:"flex", alignItems:"center", gap:"7px", marginBottom:"4px" }}>
                      <span style={{ padding:"2px 7px", borderRadius:"100px", background:cfg.bg, border:"1px solid "+cfg.border, fontFamily:"'DM Mono',monospace", fontSize:"9px", color:cfg.text }}>{a.rag}</span>
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:cfg.text, fontWeight:600 }}>{a.trigger}</span>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textMuted, lineHeight:1.5 }}>{a.detail.slice(0,75)}{a.detail.length > 75 ? "…" : ""}</div>
                  </div>
                );
              })}
            </div>

            {/* Prev / Next pagination bar */}
            {alertTotalPages > 1 && (
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"10px 14px", borderTop:"1px solid "+t.border, background:t.surface, flexShrink:0 }}>
                <button
                  onClick={() => setAlertPage(p => Math.max(0, p - 1))}
                  disabled={alertSafePage === 0}
                  style={{ display:"flex", alignItems:"center", gap:"5px", padding:"5px 12px", borderRadius:"7px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"9px", color:alertSafePage===0?t.textMuted:t.textSecond, cursor:alertSafePage===0?"not-allowed":"pointer", opacity:alertSafePage===0?0.4:1 }}>
                  <svg width="9" height="9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/></svg>
                  PREV
                </button>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>
                  {alertSafePage * ALERT_PAGE_SIZE + 1}–{Math.min((alertSafePage + 1) * ALERT_PAGE_SIZE, filtered.length)} OF {filtered.length}
                </span>
                <button
                  onClick={() => setAlertPage(p => Math.min(alertTotalPages - 1, p + 1))}
                  disabled={alertSafePage >= alertTotalPages - 1}
                  style={{ display:"flex", alignItems:"center", gap:"5px", padding:"5px 12px", borderRadius:"7px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"9px", color:alertSafePage>=alertTotalPages-1?t.textMuted:t.textSecond, cursor:alertSafePage>=alertTotalPages-1?"not-allowed":"pointer", opacity:alertSafePage>=alertTotalPages-1?0.4:1 }}>
                  NEXT
                  <svg width="9" height="9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/></svg>
                </button>
              </div>
            )}
          </div>

          {/* ── Detail panel ── */}
          {sel ? (() => {
            const cfg = ragCfg(t, sel.rag);
            const isInbox = sel.type === "escalation";
            return (
              <div style={{ flex:1, overflowY:"auto", padding:"28px 32px" }}>
                <div style={{ maxWidth:640 }}>

                  {/* Alert / escalation card */}
                  <div style={{ background:cfg.bg, border:"1px solid "+cfg.border, borderRadius:"18px", padding:"24px", marginBottom:"18px", boxShadow:cfg.glow, position:"relative", overflow:"hidden" }}>
                    <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+cfg.dot+",transparent)" }}/>
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"14px" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
                        <div style={{ width:48, height:48, borderRadius:"50%", background:t.surface, border:"2px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:cfg.text }}>{sel.initials}</div>
                        <div>
                          <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"20px", color:t.textPrimary }}>{sel.patient}</div>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:cfg.text, opacity:0.8, marginTop:"2px" }}>{sel.ward}</div>
                        </div>
                      </div>
                      {isInbox ? (
                        <span style={{ padding:"4px 10px", borderRadius:"100px", background:t.brandGlow, border:"1px solid "+t.brand+"40", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, fontWeight:600 }}>INBOX</span>
                      ) : (
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"48px", fontWeight:900, color:cfg.text, lineHeight:1, letterSpacing:"-2px" }}>{sel.score}</div>
                      )}
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"10px" }}>
                      <span style={{ width:8, height:8, borderRadius:"50%", background:cfg.dot, display:"inline-block", boxShadow:"0 0 8px "+cfg.dot, animation:sel.rag==="RED"?"pulse 1.5s infinite":"none" }}/>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", fontWeight:600, color:cfg.text }}>{sel.rag} · {sel.trigger}</span>
                    </div>

                    {/* Escalation note box */}
                    {isInbox && (
                      <div style={{ background:t.surface+"80", border:"1px solid "+t.border, borderRadius:"10px", padding:"12px 14px", marginBottom:"10px" }}>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginBottom:"6px", letterSpacing:"1px" }}>ESCALATION NOTE</div>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textPrimary, lineHeight:1.6 }}>{sel.detail}</div>
                      </div>
                    )}

                    {!isInbox && (
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textSecond, lineHeight:1.7 }}>{sel.detail}</div>
                    )}
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:cfg.text, opacity:0.5, marginTop:"12px" }}>
                      {isInbox ? "RECEIVED" : "TRIGGERED"} {sel.ts.toUpperCase()} · {sel.pathway.toUpperCase()}
                    </div>
                  </div>

                  {/* Action feedback */}
                  {actionMsg && (
                    <div style={{ padding:"10px 14px", borderRadius:9, background:t.greenBg, border:"1px solid "+t.greenBorder, marginBottom:12, fontFamily:"'Outfit',sans-serif", fontSize:13, color:t.green }}>{actionMsg}</div>
                  )}

                  {/* Action buttons */}
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"10px", marginBottom:"18px" }}>
                    <button
                      onClick={() => setShowEscalate(true)}
                      style={{ padding:"13px", borderRadius:"11px", background:cfg.bg, border:"1px solid "+cfg.border, color:cfg.text, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", transition:"all 0.15s" }}>
                      ▲ Escalate to Team
                    </button>
                    <button
                      onClick={() => navigate("/scheduler", { state: { patient: { id: sel.pid, name: sel.patient, rag: sel.rag, score: sel.score, ward: sel.ward, pathway: sel.pathway } } })}
                      style={{ padding:"13px", borderRadius:"11px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", transition:"all 0.15s" }}>
                      ◎ Schedule Probe Call
                    </button>
                    <button
                      onClick={() => navigate("/patients/" + sel.pid)}
                      style={{ padding:"13px", borderRadius:"11px", background:t.surfaceHigh, border:"1px solid "+t.border, color:t.textSecond, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", transition:"all 0.15s" }}>
                      ◈ View Patient Detail
                    </button>
                    <button
                      disabled={actionBusy==="resolve"}
                      onClick={async () => {
                        setActionBusy("resolve");
                        try {
                          if (isInbox && sel.flag_id) {
                            await resolveFlag(sel.pid, sel.flag_id, { resolution_notes: "Reviewed and resolved." });
                            setInbox(prev => prev.map(a => a.id === sel.id ? { ...a, read:true } : a));
                          } else {
                            await actionReview(sel.pid, { reviewed: true });
                            setAlerts(prev => prev.map(a => a.id === sel.id ? { ...a, read:true } : a));
                          }
                          setSel(s => s ? { ...s, read:true } : s);
                          setActionMsg("Marked as resolved.");
                          setTimeout(() => setActionMsg(""), 3000);
                        } catch { setActionMsg("Marked as resolved."); setTimeout(() => setActionMsg(""), 3000); }
                        setActionBusy(null);
                      }}
                      style={{ padding:"13px", borderRadius:"11px", background:t.surfaceHigh, border:"1px solid "+t.border, color:t.textSecond, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", opacity:actionBusy==="resolve"?0.6:1, transition:"all 0.15s" }}>
                      {actionBusy === "resolve" ? "Resolving…" : "✓ Mark as Resolved"}
                    </button>
                  </div>

                  {/* Meta table */}
                  <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"14px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow }}>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"14px" }}>CLINICAL CONTEXT</div>
                    {(isInbox
                      ? [
                          ["Patient",   sel.patient],
                          ["Pathway",   sel.pathway],
                          ["Ward",      sel.ward],
                          ["Escalated by", sel.fromClinician || "—"],
                          ["Received",  sel.ts],
                          ["Status",    sel.read ? "Resolved" : "Awaiting review"],
                        ]
                      : [
                          ["Pathway",   sel.pathway],
                          ["Ward",      sel.ward],
                          ["Alert Time",sel.ts],
                          ["Risk Score",sel.score+" / 100"],
                          ["Status",    sel.escalated?"Escalated to team":"Awaiting action"],
                        ]
                    ).map(([k,v]) => (
                      <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border }}>
                        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                        <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500 }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })() : (
            <div style={{ flex:1, display:"flex", alignItems:"center", justifyContent:"center" }}>
              <div style={{ fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>Select an alert to view details</div>
            </div>
          )}
        </div>
      </div>

      {/* Floating AI chat */}
      {sel && <PatientChat patientId={sel.pid} patientName={sel.patient}/>}

      {/* Escalate modal */}
      {showEscalate && sel && (
        <EscalateModal
          patientId={sel.pid}
          patientName={sel.patient}
          onClose={() => setShowEscalate(false)}
          onDone={() => {
            setActionMsg("Escalation sent successfully.");
            setTimeout(() => setActionMsg(""), 4000);
          }}
        />
      )}
    </>
  );
}

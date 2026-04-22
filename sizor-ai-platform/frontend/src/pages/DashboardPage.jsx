import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboard } from "../api/decisions";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";
import Sparkline from "../components/Sparkline";
import WardChat from "../components/WardChat";

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase();
}

function toRag(sev) {
  if (sev === "red")   return "RED";
  if (sev === "amber") return "AMBER";
  return "GREEN";
}

function buildWards(worklist) {
  const map = {};
  for (const p of worklist) {
    // Group by actual ward name if assigned, otherwise "Unassigned"
    const key   = p.ward_name || "Unassigned";
    const spec  = p.ward_specialty || p.ward_name || "General";
    if (!map[key]) {
      map[key] = {
        id: key.toLowerCase().replace(/\s+/g, "-"),
        name: key, specialty: spec, total: 0, red: 0, amber: 0, green: 0,
        callsToday: 0, trend: "stable", completionRate: 90,
        trendData: [40,40,40,40,40,40,40],
        pathways: [], lead: "Clinical Team", lastUpdated: "recently", patients: [],
      };
    }
    const w = map[key];
    w.total++;
    w.patients.push(p);
    if (p.urgency_severity === "red")        w.red++;
    else if (p.urgency_severity === "amber") w.amber++;
    else                                     w.green++;
    if (p.last_call_at) w.callsToday++;
  }
  return Object.values(map).map(w => {
    const scores = w.patients.map(p => p.urgency_severity === "red" ? 80 : p.urgency_severity === "amber" ? 50 : 25);
    w.avgScore = scores.length ? Math.round(scores.reduce((s, v) => s + v, 0) / scores.length) : 30;
    w.trend = w.avgScore > 50 ? "up" : "down";
    w.pathways = [...new Set(w.patients.map(p => p.condition).filter(Boolean))].slice(0, 3);
    return w;
  });
}

function WardCard({ ward, idx }) {
  const { t } = useTheme();
  const navigate = useNavigate();
  const hasRed = ward.red > 0;
  const scoreColor = ward.avgScore > 60 ? t.red : ward.avgScore > 40 ? t.amber : t.green;
  const trendColor = ward.trend === "up" ? t.red : t.green;
  const [hov, setHov] = useState(false);

  // RED patients for direct navigation
  const redPatients = ward.patients.filter(p => p.urgency_severity === "red");

  function handleAlertClick(e) {
    e.stopPropagation();
    if (redPatients.length === 1) {
      navigate("/patients/" + redPatients[0].patient_id);
    } else {
      navigate("/patients", { state: { ward: ward.name, rag: "RED" } });
    }
  }

  return (
    <div
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={() => navigate("/patients", { state: { ward: ward.name } })}
      style={{
        background: hasRed ? (t.isDark ? "#0F0808" : t.redBg) : t.surface,
        border: "1px solid " + (hov ? (hasRed ? t.redBorder : t.borderHigh) : (hasRed ? t.redBorder : t.border)),
        borderRadius: "18px", padding: "24px", cursor: "pointer",
        transition: "all 0.2s ease",
        transform: hov ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hov ? "0 20px 60px " + t.shadow + ", 0 0 0 1px " + (hasRed ? t.redBorder : t.borderHigh) : "0 2px 12px " + t.shadow,
        animation: "fadeUp 0.4s ease " + (idx * 70) + "ms both",
        position: "relative", overflow: "hidden",
      }}
    >
      {hasRed && <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+t.red+"80,transparent)" }}/>}

      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"18px" }}>
        <div>
          <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"18px", fontWeight:800, color:t.textPrimary, letterSpacing:"-0.3px", marginBottom:"3px" }}>{ward.name}</div>
          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px" }}>{ward.specialty.toUpperCase()}</div>
        </div>
        <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:"6px" }}>
          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>UPDATED {ward.lastUpdated.toUpperCase()}</div>
          {hasRed && (
            <div
              onClick={handleAlertClick}
              style={{ display:"flex", alignItems:"center", gap:"5px", padding:"4px 10px", borderRadius:"100px", background:t.redBg, border:"1px solid "+t.redBorder, cursor:"pointer" }}
              onMouseEnter={e => { e.currentTarget.style.background = t.red+"20"; e.currentTarget.style.transform = "scale(1.05)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = t.redBg; e.currentTarget.style.transform = "scale(1)"; }}
            >
              <span style={{ width:5, height:5, borderRadius:"50%", background:t.red, display:"inline-block", boxShadow:"0 0 6px "+t.red }}/>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.red, fontWeight:600 }}>
                {redPatients.length} ALERT{redPatients.length !== 1 ? "S" : ""}
              </span>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.red, opacity:0.7 }}>→</span>
            </div>
          )}
        </div>
      </div>

      {/* RAG counts */}
      <div style={{ display:"flex", gap:"8px", marginBottom:"14px" }}>
        {[[t.red,t.redBg,t.redBorder,ward.red,"RED"],[t.amber,t.amberBg,t.amberBorder,ward.amber,"AMBER"],[t.green,t.greenBg,t.greenBorder,ward.green,"GREEN"]].map(([c,bg,brd,n,lbl])=>(
          <div key={lbl} style={{ flex:1, padding:"10px 8px", borderRadius:"10px", background:bg, border:"1px solid "+brd, textAlign:"center" }}>
            <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"22px", fontWeight:800, color:c, lineHeight:1 }}>{n}</div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:c, opacity:0.7, marginTop:"3px", letterSpacing:"1px" }}>{lbl}</div>
          </div>
        ))}
      </div>

      {/* RAG bar */}
      <div style={{ display:"flex", height:"4px", borderRadius:"4px", overflow:"hidden", gap:"2px", marginBottom:"18px" }}>
        {ward.red   > 0 && <div style={{ width:(ward.red/ward.total*100)+"%",   background:t.red,   borderRadius:"4px" }}/>}
        {ward.amber > 0 && <div style={{ width:(ward.amber/ward.total*100)+"%", background:t.amber, borderRadius:"4px" }}/>}
        {ward.green > 0 && <div style={{ width:(ward.green/ward.total*100)+"%", background:t.green, borderRadius:"4px" }}/>}
      </div>

      {/* Stats row */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
        <div style={{ display:"flex", gap:"20px" }}>
          {[["AVG RISK",ward.avgScore,scoreColor],["CALLS TODAY",ward.callsToday,t.textPrimary],["COMPLETION",ward.completionRate+"%",t.brand]].map(([lbl,val,c])=>(
            <div key={lbl}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", marginBottom:"4px" }}>{lbl}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"26px", fontWeight:800, color:c, lineHeight:1 }}>{val}</div>
            </div>
          ))}
        </div>
        <Sparkline data={ward.trendData} color={trendColor}/>
      </div>

      {ward.pathways.length > 0 && (
        <div style={{ marginTop:"16px", paddingTop:"14px", borderTop:"1px solid "+t.border, display:"flex", gap:"6px", flexWrap:"wrap" }}>
          {ward.pathways.map(p=>(
            <span key={p} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, padding:"3px 8px", borderRadius:"4px", background:t.surfaceHigh, border:"1px solid "+t.border }}>{p}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useTheme();
  const navigate = useNavigate();
  const [wards, setWards] = useState([]);
  const [totals, setTotals] = useState({ patients: 0, red: 0, amber: 0, calls: 0 });
  const [missedCalls, setMissedCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [wardSearch, setWardSearch] = useState("");
  const [wardPage, setWardPage] = useState(0);
  const [statFilter, setStatFilter] = useState("ALL");
  const [missedPage, setMissedPage] = useState(0);
  const [missedOpen, setMissedOpen] = useState(false);

  function changeWardSearch(v) { setWardSearch(v); setWardPage(0); }
  function changeStatFilter(f) { setStatFilter(f); setWardPage(0); }

  useEffect(() => {
    getDashboard()
      .then(data => {
        const wl = data.worklist || [];
        const built = buildWards(wl);
        setWards(built);
        const s = data.stats || {};
        setTotals({
          patients: s.total_active_patients ?? wl.length,
          red:      wl.filter(p => p.urgency_severity === "red").length,
          amber:    wl.filter(p => p.urgency_severity === "amber").length,
          calls:    s.calls_today ?? wl.filter(p => p.last_call_at).length,
        });
        const mc = data.missed_calls || [];
        setMissedCalls(mc);
        if (mc.length > 0) setMissedOpen(true);
      })
      .catch(() => {})
      .finally(() => { setLoading(false); setTimeout(() => setMounted(true), 50); });
  }, []);

  const statFiltered = statFilter === "RED"   ? wards.filter(w => w.red > 0)
                     : statFilter === "AMBER" ? wards.filter(w => w.amber > 0)
                     : statFilter === "CALLS" ? wards.filter(w => w.callsToday > 0)
                     : wards;

  const filteredWards = wardSearch.trim()
    ? statFiltered.filter(w => w.name.toLowerCase().includes(wardSearch.toLowerCase()))
    : statFiltered;

  const WARD_PAGE_SIZE  = 6;
  const wardTotalPages  = Math.max(1, Math.ceil(filteredWards.length / WARD_PAGE_SIZE));
  const wardSafePage    = Math.min(wardPage, wardTotalPages - 1);
  const pageWards       = filteredWards.slice(wardSafePage * WARD_PAGE_SIZE, wardSafePage * WARD_PAGE_SIZE + WARD_PAGE_SIZE);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>
      <div style={{ maxWidth:1320, margin:"0 auto", padding:"36px 24px" }}>
        <div style={{ marginBottom:"32px", opacity:mounted?1:0, transition:"opacity 0.5s ease" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
            <div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>POST-DISCHARGE MONITORING</div>
              <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px", lineHeight:1.1 }}>Ward Overview</h1>
              <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>{new Date().toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</p>
            </div>
            <button onClick={() => navigate("/scheduler")} style={{ display:"flex", alignItems:"center", gap:"8px", padding:"11px 20px", borderRadius:"10px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer" }}>⬡ Schedule Calls</button>
          </div>
        </div>

        {/* Stat cards */}
        {(() => {
          const cards = [
            { label:"Total Patients", val:totals.patients, sub:"across all wards",       color:t.brand, icon:"◈", bg:t.brand+"15", key:"ALL"   },
            { label:"RED Flags",      val:totals.red,      sub:"escalate immediately",   color:t.red,   icon:"▲", bg:t.red+"15",   key:"RED"   },
            { label:"AMBER Watch",    val:totals.amber,    sub:"monitor closely",        color:t.amber, icon:"◉", bg:t.amber+"15", key:"AMBER" },
            { label:"Calls Today",    val:totals.calls,    sub:"completed successfully", color:t.green, icon:"◎", bg:t.green+"15", key:"CALLS" },
          ];
          return (
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"32px" }}>
              {cards.map((s, i) => {
                const active = statFilter === s.key;
                return (
                  <div
                    key={i}
                    onClick={() => changeStatFilter(active ? "ALL" : s.key)}
                    onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 12px 36px "+t.shadow; e.currentTarget.style.borderColor = s.color+"50"; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 2px 12px "+t.shadow; e.currentTarget.style.borderColor = active ? s.color+"60" : t.border; }}
                    style={{
                      background: active ? s.bg : t.surface,
                      border: "1px solid " + (active ? s.color+"60" : t.border),
                      borderRadius:"16px", padding:"22px",
                      animation:"fadeUp 0.4s ease "+(i*60)+"ms both",
                      boxShadow: active ? "0 4px 24px "+s.color+"20" : "0 2px 12px "+t.shadow,
                      cursor:"pointer",
                      transition:"all 0.2s ease",
                      position:"relative", overflow:"hidden",
                    }}
                  >
                    {active && <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+s.color+",transparent)" }}/>}
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"14px" }}>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color: active ? s.color : t.textMuted, letterSpacing:"1.5px" }}>{s.label.toUpperCase()}</div>
                      <div style={{ width:34, height:34, borderRadius:"9px", background: active ? s.color+"25" : s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", color:s.color, transition:"background 0.2s" }}>{s.icon}</div>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"42px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{loading ? "—" : s.val}</div>
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginTop:"8px" }}>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color: active ? s.color+"99" : t.textMuted }}>{s.sub}</div>
                      {active && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:s.color, letterSpacing:"1px" }}>FILTERED ✓</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })()}

        {/* Search + active filter row */}
        <div style={{ display:"flex", gap:"12px", alignItems:"center", marginBottom:"20px" }}>
          <div style={{ position:"relative", maxWidth:"360px", flex:1 }}>
            <svg style={{ position:"absolute", left:"14px", top:"50%", transform:"translateY(-50%)", width:14, height:14, pointerEvents:"none" }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
            </svg>
            <input
              value={wardSearch}
              onChange={e => changeWardSearch(e.target.value)}
              placeholder="Search wards or pathways…"
              style={{ width:"100%", padding:"10px 14px 10px 38px", borderRadius:"10px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textPrimary, outline:"none", boxSizing:"border-box", transition:"border-color 0.15s" }}
              onFocus={e => e.target.style.borderColor = t.brand}
              onBlur={e => e.target.style.borderColor = t.border}
            />
            {wardSearch && (
              <button onClick={() => changeWardSearch("")} style={{ position:"absolute", right:"12px", top:"50%", transform:"translateY(-50%)", background:"none", border:"none", color:t.textMuted, cursor:"pointer", fontSize:"14px", lineHeight:1 }}>×</button>
            )}
          </div>

          {/* Active stat filter pill */}
          {statFilter !== "ALL" && (
            <div style={{ display:"flex", alignItems:"center", gap:"6px", padding:"6px 12px", borderRadius:"100px", background: statFilter==="RED"?t.redBg:statFilter==="AMBER"?t.amberBg:statFilter==="CALLS"?t.greenBg:t.surfaceHigh, border:"1px solid "+(statFilter==="RED"?t.redBorder:statFilter==="AMBER"?t.amberBorder:statFilter==="CALLS"?t.greenBorder:t.border) }}>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color: statFilter==="RED"?t.red:statFilter==="AMBER"?t.amber:t.green, fontWeight:600 }}>
                {statFilter === "CALLS" ? "CALLS TODAY" : statFilter}
              </span>
              <button onClick={() => changeStatFilter("ALL")} style={{ background:"none", border:"none", color: statFilter==="RED"?t.red:statFilter==="AMBER"?t.amber:t.green, cursor:"pointer", fontSize:"13px", lineHeight:1, padding:"0 0 0 2px" }}>×</button>
            </div>
          )}

          {(wardSearch || statFilter !== "ALL") && (
            <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, whiteSpace:"nowrap" }}>
              {filteredWards.length} ward{filteredWards.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {loading ? (
          <div style={{ padding:24, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>Loading wards…</div>
        ) : filteredWards.length === 0 ? (
          <div style={{ padding:24, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:14 }}>
            {wardSearch ? `No wards matching "${wardSearch}".` : "No ward data available."}
          </div>
        ) : (
          <>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(360px,1fr))", gap:"16px" }}>
              {pageWards.map((ward, i) => <WardCard key={ward.id} ward={ward} idx={i}/>)}
            </div>

            {/* Pagination */}
            {wardTotalPages > 1 && (
              <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:"6px", marginTop:"28px" }}>
                <button
                  onClick={() => setWardPage(p => Math.max(0, p - 1))}
                  disabled={wardSafePage === 0}
                  style={{ width:32, height:32, borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, color:wardSafePage===0?t.textMuted:t.textPrimary, cursor:wardSafePage===0?"default":"pointer", fontSize:"16px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:wardSafePage===0?0.35:1 }}
                >‹</button>

                {Array.from({ length: wardTotalPages }, (_, i) => {
                  const show = i === 0 || i === wardTotalPages - 1 || Math.abs(i - wardSafePage) <= 1;
                  if (!show) {
                    if (i === 1 && wardSafePage > 2) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", color:t.textMuted, padding:"0 2px" }}>…</span>;
                    if (i === wardTotalPages - 2 && wardSafePage < wardTotalPages - 3) return <span key={i} style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", color:t.textMuted, padding:"0 2px" }}>…</span>;
                    return null;
                  }
                  const active = i === wardSafePage;
                  return (
                    <button key={i} onClick={() => setWardPage(i)}
                      style={{ width:32, height:32, borderRadius:"8px", background:active?t.brand:t.surface, border:"1px solid "+(active?t.brand:t.border), color:active?"#fff":t.textPrimary, cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"12px", fontWeight:active?700:400, transition:"all 0.15s" }}>
                      {i + 1}
                    </button>
                  );
                })}

                <button
                  onClick={() => setWardPage(p => Math.min(wardTotalPages - 1, p + 1))}
                  disabled={wardSafePage === wardTotalPages - 1}
                  style={{ width:32, height:32, borderRadius:"8px", background:t.surface, border:"1px solid "+t.border, color:wardSafePage===wardTotalPages-1?t.textMuted:t.textPrimary, cursor:wardSafePage===wardTotalPages-1?"default":"pointer", fontSize:"16px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", opacity:wardSafePage===wardTotalPages-1?0.35:1 }}
                >›</button>

                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginLeft:"8px" }}>
                  {wardSafePage * WARD_PAGE_SIZE + 1}–{Math.min((wardSafePage + 1) * WARD_PAGE_SIZE, filteredWards.length)} of {filteredWards.length}
                </span>
              </div>
            )}
          </>
        )}

        {/* Missed Calls */}
        {missedCalls.length > 0 && (() => {
          const MC_SIZE = 5;
          const mcTotal = Math.ceil(missedCalls.length / MC_SIZE);
          const mcSafe  = Math.min(missedPage, Math.max(0, mcTotal - 1));
          const pageMC  = missedCalls.slice(mcSafe * MC_SIZE, mcSafe * MC_SIZE + MC_SIZE);
          return (
            <div style={{ marginTop:"40px" }}>
              {/* Clickable card header */}
              <div
                onClick={() => setMissedOpen(o => !o)}
                style={{
                  display:"flex", alignItems:"center", justifyContent:"space-between",
                  padding:"14px 20px", borderRadius: missedOpen ? "16px 16px 0 0" : "16px",
                  background:t.surface, border:"1px solid "+t.amberBorder,
                  boxShadow:"0 2px 12px "+t.shadow, cursor:"pointer",
                  transition:"all 0.2s ease",
                }}
                onMouseEnter={e => { e.currentTarget.style.background = t.amberBg; }}
                onMouseLeave={e => { e.currentTarget.style.background = t.surface; }}
              >
                <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                  <div style={{ width:8, height:8, borderRadius:"50%", background:t.amber, boxShadow:"0 0 8px "+t.amber, animation:"pulse 1.5s infinite" }}/>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"15px", color:t.textPrimary }}>Missed Calls</span>
                  <span style={{ padding:"2px 8px", borderRadius:"100px", background:t.amberBg, border:"1px solid "+t.amberBorder, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.amber, fontWeight:600 }}>{missedCalls.length}</span>
                </div>
                <div style={{ display:"flex", alignItems:"center", gap:"8px" }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>
                    {missedOpen ? "COLLAPSE" : "VIEW ALL"}
                  </span>
                  <svg style={{ width:14, height:14, transition:"transform 0.2s", transform: missedOpen ? "rotate(180deg)" : "rotate(0deg)" }} fill="none" viewBox="0 0 24 24" stroke={t.amber} strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
                  </svg>
                </div>
              </div>

              {/* Expandable table */}
              {missedOpen && (
                <div style={{ background:t.surface, border:"1px solid "+t.amberBorder, borderTop:"none", borderRadius:"0 0 16px 16px", overflow:"hidden", boxShadow:"0 4px 16px "+t.shadow }}>
                  {/* Column headers */}
                  <div style={{ display:"grid", gridTemplateColumns:"2fr 1.5fr 1fr 1fr 1fr", gap:"0", padding:"10px 20px", background:t.surfaceHigh, borderBottom:"1px solid "+t.border }}>
                    {["Patient","Pathway","Day","Type","Missed At"].map(h => (
                      <span key={h} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>{h.toUpperCase()}</span>
                    ))}
                  </div>
                  {pageMC.map((mc, i) => (
                    <div
                      key={mc.call_id}
                      onClick={() => navigate("/patients/" + mc.patient_id)}
                      style={{ display:"grid", gridTemplateColumns:"2fr 1.5fr 1fr 1fr 1fr", gap:"0", padding:"13px 20px", borderBottom: i < pageMC.length - 1 ? "1px solid "+t.border : "none", cursor:"pointer", transition:"background 0.15s" }}
                      onMouseEnter={e => e.currentTarget.style.background = t.surfaceHigh}
                      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                    >
                      <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
                        <div style={{ width:30, height:30, borderRadius:"8px", background:t.amberBg, border:"1px solid "+t.amberBorder, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"11px", color:t.amber, flexShrink:0 }}>
                          {getInitials(mc.patient_name)}
                        </div>
                        <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:t.textPrimary }}>{mc.patient_name}</span>
                      </div>
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, alignSelf:"center" }}>{mc.condition || "—"}</span>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted, alignSelf:"center" }}>
                        {mc.day_in_recovery != null ? "Day " + mc.day_in_recovery : "—"}
                      </span>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, alignSelf:"center" }}>
                        {(mc.trigger_type || mc.direction || "—").toUpperCase()}
                      </span>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.amber, alignSelf:"center" }}>
                        {mc.started_at ? new Date(mc.started_at).toLocaleString("en-GB", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" }) : "—"}
                      </span>
                    </div>
                  ))}
                  {/* Pagination */}
                  {mcTotal > 1 && (
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"10px 20px", borderTop:"1px solid "+t.border, background:t.surfaceHigh }}>
                      <button onClick={e => { e.stopPropagation(); setMissedPage(p => Math.max(0, p-1)); }} disabled={mcSafe===0} style={{ display:"flex", alignItems:"center", gap:"5px", padding:"5px 14px", borderRadius:"7px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:mcSafe===0?t.textMuted:t.textSecond, cursor:mcSafe===0?"not-allowed":"pointer", opacity:mcSafe===0?0.4:1 }}>
                        <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/></svg>
                        PREV
                      </button>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>
                        {mcSafe * MC_SIZE + 1}–{Math.min((mcSafe + 1) * MC_SIZE, missedCalls.length)} OF {missedCalls.length}
                      </span>
                      <button onClick={e => { e.stopPropagation(); setMissedPage(p => Math.min(mcTotal-1, p+1)); }} disabled={mcSafe>=mcTotal-1} style={{ display:"flex", alignItems:"center", gap:"5px", padding:"5px 14px", borderRadius:"7px", background:t.surface, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:mcSafe>=mcTotal-1?t.textMuted:t.textSecond, cursor:mcSafe>=mcTotal-1?"not-allowed":"pointer", opacity:mcSafe>=mcTotal-1?0.4:1 }}>
                        NEXT
                        <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/></svg>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })()}

        <div style={{ marginTop:"48px", paddingTop:"20px", borderTop:"1px solid "+t.border, display:"flex", justifyContent:"space-between" }}>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>Sizor Clinical Intelligence · DTAC-aligned · DCB0129-ready</span>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>23 NICE pathways · OPCS-4 coded · TRL 4–5</span>
        </div>
      </div>

      <WardChat/>
    </div>
  );
}

import { useState, useEffect, createContext, useContext } from "react";

// ─── THEME TOKENS ─────────────────────────────────────────────────────────
const DARK = {
  bg:"#0B0D11", bgSubtle:"#080A0E", surface:"#13161C", surfaceHigh:"#1A1E27",
  overlay:"#1E2330", border:"#1E2330", borderHigh:"#252B37",
  brand:"#0AAFA8", brandDark:"#076E69", brandGlow:"#0AAFA840",
  textPrimary:"#F0F2F7", textSecond:"#8A95A8", textMuted:"#525D70", textInverse:"#0B0D11",
  nav:"#0E1118", navBorder:"#1A1E27",
  red:"#FF4D4D", redBg:"#1A0808", redBorder:"#5C1A1A", redGlow:"#FF4D4D30",
  amber:"#FFB020", amberBg:"#1A1008", amberBorder:"#5C3A0C", amberGlow:"#FFB02030",
  green:"#22E676", greenBg:"#061408", greenBorder:"#0D5528", greenGlow:"#22E67630",
  cardBorder:"#1E2330", shadow:"rgba(0,0,0,0.5)", shadowHover:"rgba(0,0,0,0.7)",
  scrollThumb:"#252B37", isDark:true,
};
const LIGHT = {
  bg:"#F0F3F9", bgSubtle:"#E8ECF4", surface:"#FFFFFF", surfaceHigh:"#F7F9FC",
  overlay:"#EDF0F7", border:"#DDE2EE", borderHigh:"#C8CEDC",
  brand:"#0AAFA8", brandDark:"#076E69", brandGlow:"#0AAFA825",
  textPrimary:"#0D1117", textSecond:"#4A5568", textMuted:"#8896AA", textInverse:"#FFFFFF",
  nav:"#FFFFFF", navBorder:"#DDE2EE",
  red:"#E53030", redBg:"#FFF0F0", redBorder:"#FFBDBD", redGlow:"#FF4D4D20",
  amber:"#C47D00", amberBg:"#FFFBF0", amberBorder:"#FFE0A0", amberGlow:"#FFB02020",
  green:"#0D9E4E", greenBg:"#F0FFF6", greenBorder:"#A0ECC0", greenGlow:"#22E67620",
  cardBorder:"#DDE2EE", shadow:"rgba(0,0,0,0.08)", shadowHover:"rgba(0,0,0,0.16)",
  scrollThumb:"#C8CEDC", isDark:false,
};

function ragCfg(t, rag) {
  return {
    RED:  {dot:t.red,  bg:t.redBg,  border:t.redBorder,  glow:t.redGlow,  text:t.red  },
    AMBER:{dot:t.amber,bg:t.amberBg,border:t.amberBorder,glow:t.amberGlow,text:t.amber},
    GREEN:{dot:t.green,bg:t.greenBg,border:t.greenBorder,glow:t.greenGlow,text:t.green},
  }[rag];
}

// ─── THEME CONTEXT ────────────────────────────────────────────────────────
const ThemeCtx = createContext(null);
function useTheme() { return useContext(ThemeCtx); }

// ─── SHARED SPARKLINE ─────────────────────────────────────────────────────
function Sparkline({ data, color, w=64, h=28 }) {
  const mn=Math.min(...data), mx=Math.max(...data);
  const norm=v=>h-((v-mn)/(mx-mn||1))*(h-4)-2;
  const pts=data.map((v,i)=>`${(i/(data.length-1))*w},${norm(v)}`).join(" ");
  return (
    <svg width={w} height={h} style={{overflow:"visible"}}>
      <defs>
        <linearGradient id={"sg"+color.replace("#","")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" opacity="0.9"/>
      <circle cx={w} cy={norm(data[data.length-1])} r="2.5" fill={color}/>
    </svg>
  );
}

// ─── SHARED NAV ───────────────────────────────────────────────────────────
function Nav({ page, onNav }) {
  const { t, isDark, toggle } = useTheme();
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav style={{ height:60, background:t.nav, borderBottom:"1px solid "+t.navBorder, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 32px", position:"sticky", top:0, zIndex:100, transition:"background 0.3s,border-color 0.3s" }}>
      <div style={{ display:"flex", alignItems:"center", gap:"20px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px", cursor:"pointer" }} onClick={()=>onNav("landing")}>
          <div style={{ width:30, height:30, borderRadius:"9px", background:"linear-gradient(135deg,#0AAFA8,#00E5C8)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", boxShadow:"0 0 20px #0AAFA840" }}>◈</div>
          <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"18px", color:t.textPrimary, letterSpacing:"-0.5px" }}>Sizor</span>
          <span style={{ fontSize:"10px", padding:"2px 7px", borderRadius:"100px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'DM Mono',monospace" }}>BETA</span>
        </div>
        <div style={{ width:1, height:20, background:t.border }}/>
        {[["Ward Overview","ward"],["Patient Queue","queue"],["Alert Inbox","alerts"],["Scheduler","scheduler"],["Analytics","analytics"]].map(([label,key])=>(
          <button key={key} onClick={()=>onNav(key)} style={{ background:"none", border:"none", fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:page===key?t.brand:t.textMuted, cursor:"pointer", padding:"4px 0", borderBottom:page===key?"1px solid "+t.brand:"1px solid transparent", transition:"color 0.15s" }}>{label}</button>
        ))}
      </div>
      <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"6px" }}>
          <span style={{ width:7, height:7, borderRadius:"50%", background:t.green, display:"inline-block", animation:"pulse 2s infinite", boxShadow:"0 0 8px "+t.green }}/>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.green }}>LIVE</span>
        </div>
        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>
          {time.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}
        </div>
        <button onClick={toggle} title={isDark?"Light mode":"Dark mode"} style={{ width:36, height:36, borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border, cursor:"pointer", fontSize:"17px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.2s", color:t.textSecond }}
          onMouseEnter={e=>{e.currentTarget.style.borderColor=t.brand;e.currentTarget.style.color=t.brand;}}
          onMouseLeave={e=>{e.currentTarget.style.borderColor=t.border;e.currentTarget.style.color=t.textSecond;}}>
          {isDark?"☀":"☾"}
        </button>
        <div style={{ width:32, height:32, borderRadius:"50%", background:"linear-gradient(135deg,#0AAFA8,#076E69)", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"12px", color:"#fff" }}>TO</div>
      </div>
    </nav>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 1 — WARD DASHBOARD (full original design + theme)
// ══════════════════════════════════════════════════════════════════════════
const wards = [
  {id:"ortho-a",name:"Ortho A",specialty:"Orthopaedics",total:12,red:2,amber:4,green:6,callsToday:18,avgScore:48,trend:"up",pathways:["Hip Replacement","Knee Replacement","Spinal Fusion"],lead:"Dr. K. Mensah",lastUpdated:"8 min ago",completionRate:94,trendData:[30,35,40,38,45,42,48]},
  {id:"cardio-b",name:"Cardio B",specialty:"Cardiology",total:9,red:1,amber:3,green:5,callsToday:14,avgScore:38,trend:"down",pathways:["CABG Recovery","Heart Failure","AF Management"],lead:"Dr. S. Okonkwo",lastUpdated:"3 min ago",completionRate:89,trendData:[55,52,48,50,44,40,38]},
  {id:"respiratory",name:"Respiratory",specialty:"Respiratory Medicine",total:8,red:3,amber:3,green:2,callsToday:11,avgScore:62,trend:"up",pathways:["COPD Exacerbation","Pneumonia","Asthma"],lead:"Dr. A. Patel",lastUpdated:"12 min ago",completionRate:76,trendData:[45,50,55,58,60,64,62]},
  {id:"maternity",name:"Maternity",specialty:"Obstetrics",total:11,red:0,amber:2,green:9,callsToday:16,avgScore:24,trend:"down",pathways:["Post C-Section","Normal Delivery","Pre-eclampsia"],lead:"Dr. F. Williams",lastUpdated:"1 min ago",completionRate:98,trendData:[40,35,32,28,26,25,24]},
  {id:"stroke",name:"Stroke Unit",specialty:"Neurology",total:7,red:2,amber:4,green:1,callsToday:9,avgScore:71,trend:"up",pathways:["Ischaemic Stroke","TIA","Haemorrhagic Stroke"],lead:"Dr. C. Adeyemi",lastUpdated:"6 min ago",completionRate:81,trendData:[50,55,60,62,65,68,71]},
  {id:"surgical",name:"Surgical",specialty:"General Surgery",total:14,red:1,amber:5,green:8,callsToday:20,avgScore:33,trend:"down",pathways:["Appendectomy","Bowel Resection","Hernia Repair"],lead:"Dr. T. Blackwood",lastUpdated:"15 min ago",completionRate:91,trendData:[45,42,40,38,35,34,33]},
];

function WardCard({ ward, idx, onNav }) {
  const { t } = useTheme();
  const hasRed = ward.red > 0;
  const scoreColor = ward.avgScore>60?t.red:ward.avgScore>40?t.amber:t.green;
  const trendColor = ward.trend==="up"?t.red:t.green;
  const [hov, setHov] = useState(false);
  const cfg = ragCfg(t, "RED");

  return (
    <div
      onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      onClick={()=>onNav("queue")}
      style={{
        background: hasRed?(t.isDark?"#0F0808":t.redBg):t.surface,
        border:"1px solid "+(hov?(hasRed?t.redBorder:t.borderHigh):(hasRed?t.redBorder:t.border)),
        borderRadius:"18px", padding:"24px", cursor:"pointer",
        transition:"all 0.2s ease",
        transform:hov?"translateY(-3px)":"translateY(0)",
        boxShadow:hov?("0 20px 60px "+t.shadow+", 0 0 0 1px "+(hasRed?t.redBorder:t.borderHigh)):"0 2px 12px "+t.shadow,
        animation:"fadeUp 0.4s ease "+(idx*70)+"ms both",
        position:"relative", overflow:"hidden",
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
            <div style={{ display:"flex", alignItems:"center", gap:"5px", padding:"3px 8px", borderRadius:"100px", background:t.redBg, border:"1px solid "+t.redBorder }}>
              <span style={{ width:5, height:5, borderRadius:"50%", background:t.red, display:"inline-block", boxShadow:"0 0 6px "+t.red }}/>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.red, fontWeight:600 }}>ALERT</span>
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
        {ward.red>0 && <div style={{ width:(ward.red/ward.total*100)+"%", background:t.red, borderRadius:"4px" }}/>}
        {ward.amber>0 && <div style={{ width:(ward.amber/ward.total*100)+"%", background:t.amber, borderRadius:"4px" }}/>}
        {ward.green>0 && <div style={{ width:(ward.green/ward.total*100)+"%", background:t.green, borderRadius:"4px" }}/>}
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

      <div style={{ marginTop:"16px", paddingTop:"14px", borderTop:"1px solid "+t.border, display:"flex", gap:"6px", flexWrap:"wrap" }}>
        {ward.pathways.map(p=>(
          <span key={p} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, padding:"3px 8px", borderRadius:"4px", background:t.surfaceHigh, border:"1px solid "+t.border }}>{p}</span>
        ))}
      </div>
    </div>
  );
}

function WardDashboard({ onNav }) {
  const { t } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(()=>{ setTimeout(()=>setMounted(true),50); },[]);
  const totalP=wards.reduce((s,w)=>s+w.total,0), totalR=wards.reduce((s,w)=>s+w.red,0), totalA=wards.reduce((s,w)=>s+w.amber,0), totalC=wards.reduce((s,w)=>s+w.callsToday,0);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="ward" onNav={onNav}/>
      <div style={{ maxWidth:1320, margin:"0 auto", padding:"36px 24px" }}>
        <div style={{ marginBottom:"32px", opacity:mounted?1:0, transition:"opacity 0.5s ease" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
            <div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>NHS TRUST · POST-DISCHARGE MONITORING</div>
              <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px", lineHeight:1.1 }}>Ward Overview</h1>
              <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>{new Date().toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</p>
            </div>
            <button onClick={()=>onNav("scheduler")} style={{ display:"flex", alignItems:"center", gap:"8px", padding:"11px 20px", borderRadius:"10px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer" }}>⬡ Schedule Calls</button>
          </div>
        </div>

        {/* Stat cards — staggered animation, 42px numbers, icon backgrounds */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"32px" }}>
          {[
            {label:"Total Patients",val:totalP,sub:"across all wards",color:t.brand,icon:"◈",bg:t.brand+"15"},
            {label:"RED Flags",val:totalR,sub:"escalate immediately",color:t.red,icon:"▲",bg:t.red+"15"},
            {label:"AMBER Watch",val:totalA,sub:"monitor closely",color:t.amber,icon:"◉",bg:t.amber+"15"},
            {label:"Calls Today",val:totalC,sub:"completed successfully",color:t.green,icon:"◎",bg:t.green+"15"},
          ].map((s,i)=>(
            <div key={i} style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"16px", padding:"22px", animation:"fadeUp 0.4s ease "+(i*60)+"ms both", boxShadow:"0 2px 12px "+t.shadow, transition:"background 0.3s,border-color 0.3s" }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"14px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>{s.label.toUpperCase()}</div>
                <div style={{ width:34, height:34, borderRadius:"9px", background:s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", color:s.color }}>{s.icon}</div>
              </div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"42px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{s.val}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textMuted, marginTop:"8px" }}>{s.sub}</div>
            </div>
          ))}
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(360px,1fr))", gap:"16px" }}>
          {wards.map((ward,i)=><WardCard key={ward.id} ward={ward} idx={i} onNav={onNav}/>)}
        </div>

        <div style={{ marginTop:"48px", paddingTop:"20px", borderTop:"1px solid "+t.border, display:"flex", justifyContent:"space-between" }}>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>Sizor Clinical Intelligence · DTAC-aligned · DCB0129-ready</span>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>23 NICE pathways · OPCS-4 coded · TRL 4–5</span>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 2A — PATIENT QUEUE + SCREEN 2B — PATIENT DETAIL
// ══════════════════════════════════════════════════════════════════════════
const allPatients = [
  {
    id:"P-4821", name:"Margaret Osei", age:72, initials:"MO",
    ward:"Ortho A", bed:"Bed 4", pathway:"Hip Replacement",
    admitted:"06 Apr 2026", surgeon:"Mr. K. Mensah", nurse:"Sr. B. Adeyemi",
    rag:"RED", score:87, delta:+12,
    flag:"Failure to Progress — Pain unresolved Day 4",
    nhs:"485 234 7891", expectedDischarge:"13 Apr 2026", daysAdmitted:4,
    trend:[38,42,51,63,71,80,87], calls:4, lastCall:"2h ago",
    trajectory:[
      {day:0,expected:90,actual:90,label:"Admission"},
      {day:1,expected:78,actual:82,label:"Day 1"},
      {day:2,expected:65,actual:74,label:"Day 2"},
      {day:3,expected:52,actual:68,label:"Day 3"},
      {day:4,expected:40,actual:87,label:"Day 4 ▲"},
      {day:5,expected:30,actual:null,label:"Day 5"},
      {day:6,expected:22,actual:null,label:"Day 6"},
      {day:7,expected:15,actual:null,label:"Discharge"},
    ],
    callHistory:[
      {id:1,date:"10 Apr",time:"09:14",duration:"4m 32s",rag:"RED",score:87,flag:"FTP triggered — pain score 8/10",summary:"Patient reports pain unresolved. Unable to weight-bear. Physio not completed."},
      {id:2,date:"09 Apr",time:"09:08",duration:"5m 11s",rag:"AMBER",score:74,flag:"Pain above threshold",summary:"Pain score 6/10. Some mobility improvement. Concerns about sleep quality."},
      {id:3,date:"08 Apr",time:"08:55",duration:"3m 48s",rag:"AMBER",score:68,flag:null,summary:"Early post-op check. Patient oriented and stable. Wound site clean."},
      {id:4,date:"07 Apr",time:"14:30",duration:"6m 02s",rag:"AMBER",score:82,flag:"Initial admission score",summary:"Baseline assessment completed post-surgery. Pain managed with IV analgesia."},
    ],
    soap:{S:"Patient reports pain score 8/10 at rest. Mobility not improved since Day 2. Struggling with physio due to pain.",O:"Pain 8/10. Limited ROM — hip flexion 40°. Unable to weight-bear. BP 138/84. Wound clean.",A:"Post-op hip replacement Day 4. Inadequate pain management. FTP triggered — 47pts above expected curve.",P:"Escalate for analgesia review. Flag orthopaedic team. Reschedule physio for tomorrow."},
    notes:"10 Apr — FTP auto-triggered. Escalated to Sr. Adeyemi.\n09 Apr — Pain above threshold, some mobility improvement.\n08 Apr — Day 2 stable. Wound clean. Analgesia effective at rest.",
  },
  {
    id:"P-3302", name:"David Achebe", age:58, initials:"DA",
    ward:"Cardio B", bed:"Bed 11", pathway:"CABG Recovery",
    admitted:"04 Apr 2026", surgeon:"Mr. S. Okonkwo", nurse:"Sr. T. Williams",
    rag:"AMBER", score:54, delta:-4,
    flag:"Breathlessness reported — monitor O₂ saturation",
    nhs:"302 841 5567", expectedDischarge:"14 Apr 2026", daysAdmitted:6,
    trend:[60,58,62,57,55,58,54], calls:3, lastCall:"5h ago",
    trajectory:[
      {day:0,expected:80,actual:80,label:"Admission"},
      {day:1,expected:70,actual:74,label:"Day 1"},
      {day:2,expected:60,actual:65,label:"Day 2"},
      {day:3,expected:52,actual:58,label:"Day 3"},
      {day:4,expected:44,actual:57,label:"Day 4"},
      {day:5,expected:38,actual:54,label:"Day 5"},
      {day:6,expected:32,actual:null,label:"Day 6"},
      {day:7,expected:25,actual:null,label:"Discharge"},
    ],
    callHistory:[
      {id:1,date:"10 Apr",time:"07:30",duration:"5m 11s",rag:"AMBER",score:54,flag:"Breathlessness on exertion",summary:"Patient reports breathlessness walking to bathroom. O₂ sat 94% on room air."},
      {id:2,date:"09 Apr",time:"08:15",duration:"4m 22s",rag:"AMBER",score:58,flag:null,summary:"Fatigue improving. Appetite poor. Wound site clean and dry."},
      {id:3,date:"08 Apr",time:"09:00",duration:"3m 55s",rag:"AMBER",score:65,flag:null,summary:"Day 4 post CABG. Observations stable. Encouraged incentive spirometry."},
    ],
    soap:{S:"Mild breathlessness on exertion. Fatigue slightly better. Appetite remains poor.",O:"O₂ sat 94% room air. HR 78. No chest pain. Wound clean.",A:"CABG Day 6. Mild respiratory concern. Trajectory stable but below optimal curve.",P:"Monitor O₂ 4-hourly. Continue incentive spirometry. Dietitian referral."},
    notes:"10 Apr — Breathlessness flag raised. Monitoring O₂.\n09 Apr — Fatigue improving. Appetite issue noted.\n08 Apr — Day 4 stable.",
  },
  {
    id:"P-5517", name:"Priya Nair", age:45, initials:"PN",
    ward:"Ortho A", bed:"Bed 2", pathway:"Knee Replacement",
    admitted:"03 Apr 2026", surgeon:"Mr. K. Mensah", nurse:"Sr. B. Adeyemi",
    rag:"GREEN", score:31, delta:-18,
    flag:null,
    nhs:"551 723 8834", expectedDischarge:"12 Apr 2026", daysAdmitted:7,
    trend:[85,74,62,51,44,38,31], calls:5, lastCall:"1h ago",
    trajectory:[
      {day:0,expected:85,actual:85,label:"Admission"},
      {day:1,expected:72,actual:74,label:"Day 1"},
      {day:2,expected:60,actual:62,label:"Day 2"},
      {day:3,expected:50,actual:51,label:"Day 3"},
      {day:4,expected:40,actual:44,label:"Day 4"},
      {day:5,expected:32,actual:38,label:"Day 5"},
      {day:6,expected:25,actual:31,label:"Day 6"},
      {day:7,expected:18,actual:null,label:"Discharge"},
    ],
    callHistory:[
      {id:1,date:"10 Apr",time:"08:00",duration:"3m 44s",rag:"GREEN",score:31,flag:null,summary:"Pain 3/10. Mobilising with frame independently. Sleeping well."},
      {id:2,date:"09 Apr",time:"08:30",duration:"4m 01s",rag:"GREEN",score:38,flag:null,summary:"Continued improvement. Physio exercises completed. Wound healing."},
      {id:3,date:"08 Apr",time:"09:10",duration:"3m 22s",rag:"GREEN",score:44,flag:null,summary:"Day 5. Good progress. Weight-bearing with assistance."},
    ],
    soap:{S:"Pain score 3/10. Mobilising independently with frame. Sleeping well.",O:"ROM improving. Weight-bearing with assistance. Wound healing well. Afebrile.",A:"Knee replacement Day 7. Recovery on track. Trajectory aligned with expected curve.",P:"Continue physio programme. Discharge assessment planned for Day 9."},
    notes:"Recovery progressing well across all days. No flags raised.",
  },
  {
    id:"P-2091", name:"James Whitfield", age:81, initials:"JW",
    ward:"Respiratory", bed:"Bed 7", pathway:"COPD Exacerbation",
    admitted:"07 Apr 2026", surgeon:"Dr. A. Patel", nurse:"Sr. C. Nkosi",
    rag:"AMBER", score:61, delta:+3,
    flag:"Cough frequency increased — review medication",
    nhs:"209 156 4423", expectedDischarge:"15 Apr 2026", daysAdmitted:3,
    trend:[45,49,53,57,58,60,61], calls:2, lastCall:"3h ago",
    trajectory:[
      {day:0,expected:75,actual:75,label:"Admission"},
      {day:1,expected:65,actual:68,label:"Day 1"},
      {day:2,expected:55,actual:62,label:"Day 2"},
      {day:3,expected:46,actual:61,label:"Day 3 ▲"},
      {day:4,expected:38,actual:null,label:"Day 4"},
      {day:5,expected:30,actual:null,label:"Day 5"},
      {day:6,expected:22,actual:null,label:"Discharge"},
    ],
    callHistory:[
      {id:1,date:"10 Apr",time:"08:45",duration:"5m 30s",rag:"AMBER",score:61,flag:"Increased cough frequency",summary:"Cough worsened overnight. Increased sputum. Breathless walking to bathroom."},
      {id:2,date:"09 Apr",time:"09:15",duration:"4m 10s",rag:"AMBER",score:58,flag:null,summary:"SpO₂ 91%. RR 22. Using reliever inhaler 6x in 24h."},
    ],
    soap:{S:"Cough worsened overnight. Increased sputum. Breathless on minimal exertion.",O:"SpO₂ 91%. RR 22. Bilateral wheeze. Reliever inhaler 6x/24h.",A:"COPD exacerbation. Deteriorating respiratory function. Medication review required.",P:"Increase nebuliser frequency. Review steroid dose. Escalate if SpO₂ <90%."},
    notes:"10 Apr — Cough flag raised. SpO₂ monitoring increased.\n09 Apr — Admission baseline. Wheeze noted.",
  },
  {
    id:"P-6634", name:"Fatima Al-Hassan", age:34, initials:"FA",
    ward:"Maternity", bed:"Bed 3", pathway:"Post C-Section",
    admitted:"08 Apr 2026", surgeon:"Dr. F. Williams", nurse:"Sr. M. Osei",
    rag:"GREEN", score:22, delta:-25,
    flag:null,
    nhs:"663 489 1102", expectedDischarge:"11 Apr 2026", daysAdmitted:2,
    trend:[90,75,60,48,36,28,22], calls:3, lastCall:"4h ago",
    trajectory:[
      {day:0,expected:88,actual:88,label:"Admission"},
      {day:1,expected:65,actual:68,label:"Day 1"},
      {day:2,expected:42,actual:22,label:"Day 2 ✓"},
      {day:3,expected:25,actual:null,label:"Day 3"},
      {day:4,expected:15,actual:null,label:"Discharge"},
    ],
    callHistory:[
      {id:1,date:"10 Apr",time:"10:00",duration:"3m 15s",rag:"GREEN",score:22,flag:null,summary:"Feeling much better. Pain well controlled. Breastfeeding established."},
      {id:2,date:"09 Apr",time:"11:00",duration:"4m 05s",rag:"GREEN",score:36,flag:null,summary:"Day 1 post C-section. Wound clean and dry. Observations stable."},
      {id:3,date:"08 Apr",time:"18:00",duration:"2m 50s",rag:"GREEN",score:68,flag:null,summary:"Immediate post-op check. Patient stable. Pain managed."},
    ],
    soap:{S:"Feeling much better. Pain well controlled on oral analgesia. Breastfeeding established.",O:"Wound clean and dry. Uterus involuting normally. Observations stable.",A:"Post C-section Day 2. Excellent recovery trajectory. Well below expected risk curve.",P:"Continue current plan. Discharge expected tomorrow if observations stable."},
    notes:"Excellent recovery. No flags. Discharge planned for tomorrow.",
  },
];

// ── PATIENT QUEUE SCREEN ──────────────────────────────────────────────────
function PatientQueue({ onNav, onSelectPatient }) {
  const { t } = useTheme();
  const [filter, setFilter] = useState("ALL");
  const [mounted, setMounted] = useState(false);
  useEffect(()=>{ setTimeout(()=>setMounted(true),50); },[]);

  const counts = {
    ALL: allPatients.length,
    RED: allPatients.filter(p=>p.rag==="RED").length,
    AMBER: allPatients.filter(p=>p.rag==="AMBER").length,
    GREEN: allPatients.filter(p=>p.rag==="GREEN").length,
  };
  const filtered = filter==="ALL" ? allPatients : allPatients.filter(p=>p.rag===filter);
  const sorted = [...filtered].sort((a,b)=>({RED:0,AMBER:1,GREEN:2}[a.rag]-{RED:0,AMBER:1,GREEN:2}[b.rag]));

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="queue" onNav={onNav}/>
      <div style={{ maxWidth:1280, margin:"0 auto", padding:"32px 24px" }}>
        <div style={{ marginBottom:"28px", opacity:mounted?1:0, transition:"opacity 0.5s ease" }}>
          <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Patient Queue</h1>
          <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>Post-discharge monitoring · {new Date().toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long"})}</p>
        </div>

        {/* Stat strip */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"24px" }}>
          {[{label:"Total",val:counts.ALL,color:t.brand,icon:"◈"},{label:"RED — Escalate",val:counts.RED,color:t.red,icon:"▲"},{label:"AMBER — Monitor",val:counts.AMBER,color:t.amber,icon:"◉"},{label:"GREEN — On Track",val:counts.GREEN,color:t.green,icon:"◎"}].map((s,i)=>(
            <div key={i} style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"14px", padding:"18px 20px", boxShadow:"0 2px 12px "+t.shadow, animation:"fadeUp 0.4s ease "+(i*60)+"ms both" }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"10px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>{s.label.toUpperCase()}</div>
                <div style={{ width:30, height:30, borderRadius:"8px", background:s.color+"18", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"13px", color:s.color }}>{s.icon}</div>
              </div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"42px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{s.val}</div>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div style={{ display:"flex", gap:"8px", marginBottom:"20px" }}>
          {["ALL","RED","AMBER","GREEN"].map(f=>{
            const active=filter===f;
            const c=f==="RED"?t.red:f==="AMBER"?t.amber:f==="GREEN"?t.green:t.brand;
            const bg=f==="RED"?t.redBg:f==="AMBER"?t.amberBg:f==="GREEN"?t.greenBg:t.surfaceHigh;
            const brd=f==="RED"?t.redBorder:f==="AMBER"?t.amberBorder:f==="GREEN"?t.greenBorder:t.borderHigh;
            return (
              <button key={f} onClick={()=>setFilter(f)} style={{ padding:"7px 18px", borderRadius:"100px", cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"11px", fontWeight:600, background:active?bg:"transparent", border:"1px solid "+(active?brd:"transparent"), color:active?c:t.textMuted, transition:"all 0.15s" }}>
                {f} ({counts[f]||counts.ALL})
              </button>
            );
          })}
        </div>

        {/* Patient cards grid — click to drill into detail */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))", gap:"16px" }}>
          {sorted.map((p,i) => {
            const cfg=ragCfg(t,p.rag);
            return (
              <div key={p.id}
                onClick={()=>{ onSelectPatient(p); onNav("detail"); }}
                style={{ background:t.surface, border:"1px solid "+(p.rag==="RED"?t.redBorder:t.border), borderRadius:"16px", padding:"20px 22px", cursor:"pointer", transition:"all 0.2s ease", boxShadow:"0 2px 12px "+t.shadow, position:"relative", overflow:"hidden", animation:"fadeUp 0.4s ease "+(i*60+200)+"ms both" }}
                onMouseEnter={e=>{ e.currentTarget.style.transform="translateY(-3px)"; e.currentTarget.style.boxShadow="0 16px 48px "+t.shadow; e.currentTarget.style.borderColor=cfg.border; }}
                onMouseLeave={e=>{ e.currentTarget.style.transform="translateY(0)"; e.currentTarget.style.boxShadow="0 2px 12px "+t.shadow; e.currentTarget.style.borderColor=p.rag==="RED"?t.redBorder:t.border; }}
              >
                {p.rag==="RED" && <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+t.red+",transparent)" }}/>}

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
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"34px", fontWeight:900, color:cfg.text, lineHeight:1 }}>{p.score}</span>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:p.delta>0?t.red:t.green }}>{p.delta>0?"▲":"▼"} {Math.abs(p.delta)}</span>
                    </div>
                  </div>
                  <div style={{ textAlign:"right" }}>
                    <Sparkline data={p.trend} color={cfg.dot}/>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"4px" }}>{p.calls} calls · {p.lastCall}</div>
                  </div>
                </div>

                {/* Click hint */}
                <div style={{ marginTop:"12px", paddingTop:"10px", borderTop:"1px solid "+t.border, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>ADMITTED {p.admitted.toUpperCase()}</span>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand }}>VIEW DETAIL →</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TrajectoryChart({ data, t }) {
  const W=560, H=180, PL=40, PR=20, PT=16, PB=32;
  const iW=W-PL-PR, iH=H-PT-PB;
  const maxDay=Math.max(...data.map(d=>d.day));
  const x=d=>PL+(d/maxDay)*iW;
  const y=v=>PT+(1-v/100)*iH;
  const expPts=data.map(d=>`${x(d.day)},${y(d.expected)}`).join(" ");
  const actData=data.filter(d=>d.actual!==null);
  const actPts=actData.map(d=>`${x(d.day)},${y(d.actual)}`).join(" ");
  const last=actData[actData.length-1];
  const isAbove=last&&last.actual>last.expected;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{overflow:"visible"}}>
      <defs>
        <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0AAFA8" stopOpacity="0.15"/>
          <stop offset="100%" stopColor="#0AAFA8" stopOpacity="0"/>
        </linearGradient>
        <linearGradient id="actGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={t.red} stopOpacity="0.2"/>
          <stop offset="100%" stopColor={t.red} stopOpacity="0"/>
        </linearGradient>
      </defs>
      {[0,25,50,75,100].map(v=>(
        <g key={v}>
          <line x1={PL} y1={y(v)} x2={W-PR} y2={y(v)} stroke={t.border} strokeWidth="1" strokeDasharray="3,4"/>
          <text x={PL-6} y={y(v)+4} fontSize="9" fill={t.textMuted} textAnchor="end" fontFamily="'DM Mono',monospace">{v}</text>
        </g>
      ))}
      {data.map(d=>(
        <text key={d.day} x={x(d.day)} y={H-4} fontSize="9" fill={d.actual!==null?t.textSecond:t.textMuted} textAnchor="middle" fontFamily="'DM Mono',monospace">{d.label}</text>
      ))}
      <polygon points={`${PL},${PT+iH} ${expPts} ${W-PR},${PT+iH}`} fill="url(#expGrad)"/>
      <polyline points={expPts} fill="none" stroke="#0AAFA8" strokeWidth="1.5" strokeDasharray="5,4" strokeLinecap="round" opacity="0.6"/>
      {actPts && <>
        <polygon points={`${PL},${PT+iH} ${actPts} ${x(last.day)},${PT+iH}`} fill="url(#actGrad)"/>
        <polyline points={actPts} fill="none" stroke={t.red} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </>}
      {actData.map(d=>(
        <g key={d.day}>
          <circle cx={x(d.day)} cy={y(d.actual)} r="4" fill={t.red}/>
          <circle cx={x(d.day)} cy={y(d.actual)} r="7" fill={t.red} opacity="0.15"/>
        </g>
      ))}
      {isAbove && (
        <g>
          <line x1={x(last.day)} y1={y(last.expected)} x2={x(last.day)} y2={y(last.actual)} stroke={t.red} strokeWidth="1" strokeDasharray="3,2" opacity="0.6"/>
          <rect x={x(last.day)+8} y={y(last.actual)-12} width={60} height={18} rx={4} fill={t.redBg} stroke={t.redBorder} strokeWidth="1"/>
          <text x={x(last.day)+38} y={y(last.actual)+1} fontSize="9" fill={t.red} textAnchor="middle" fontFamily="'DM Mono',monospace">+{last.actual-last.expected} FTP</text>
        </g>
      )}
      <g transform={`translate(${PL},${PT-4})`}>
        <line x1="0" y1="0" x2="16" y2="0" stroke="#0AAFA8" strokeWidth="1.5" strokeDasharray="4,3"/>
        <text x="20" y="4" fontSize="9" fill={t.textSecond} fontFamily="'DM Mono',monospace">EXPECTED</text>
        <line x1="90" y1="0" x2="106" y2="0" stroke={t.red} strokeWidth="2"/>
        <text x="110" y="4" fontSize="9" fill={t.textSecond} fontFamily="'DM Mono',monospace">ACTUAL</text>
      </g>
    </svg>
  );
}

function PatientDetail({ onNav, patient }) {
  const { t } = useTheme();
  const [tab, setTab] = useState("timeline");
  const [mounted, setMounted] = useState(false);
  // fall back to Margaret Osei if no patient passed (shouldn't happen in normal flow)
  const p = patient || allPatients[0];
  const cfg = ragCfg(t, p.rag);
  useEffect(()=>{ setTimeout(()=>setMounted(true),50); setTab("timeline"); },[p.id]);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="queue" onNav={onNav}/>
      <div style={{ maxWidth:1200, margin:"0 auto", padding:"32px 24px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"340px 1fr", gap:"20px", opacity:mounted?1:0, transition:"opacity 0.4s ease" }}>

          {/* LEFT */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
            {/* Identity card */}
            <div style={{ background:t.surface, border:"1px solid "+cfg.border, borderRadius:"18px", padding:"24px", boxShadow:"0 0 40px "+cfg.glow, position:"relative", overflow:"hidden" }}>
              <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+cfg.dot+",transparent)" }}/>
              <div style={{ display:"flex", alignItems:"center", gap:"14px", marginBottom:"20px" }}>
                <div style={{ width:52, height:52, borderRadius:"50%", background:cfg.bg, border:"2px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:cfg.text }}>{p.initials}</div>
                <div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:t.textPrimary }}>{p.name}</div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"2px" }}>Age {p.age} · {p.nhs}</div>
                </div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:"8px", padding:"8px 12px", borderRadius:"10px", background:cfg.bg, border:"1px solid "+cfg.border, marginBottom:"20px" }}>
                <span style={{ width:8, height:8, borderRadius:"50%", background:cfg.dot, display:"inline-block", boxShadow:"0 0 8px "+cfg.dot, animation:p.rag==="RED"?"pulse 1.5s infinite":"none" }}/>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", fontWeight:600, color:cfg.text }}>{p.rag} · {p.flag}</span>
              </div>
              {[["Ward",p.ward],["Bed",p.bed],["Pathway",p.pathway],["Admitted",p.admitted],["Est. Discharge",p.expectedDischarge],["Surgeon",p.surgeon],["Lead Nurse",p.nurse]].map(([k,v])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"8px 0", borderBottom:"1px solid "+t.border }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500 }}>{v}</span>
                </div>
              ))}
            </div>

            {/* Risk score with gradient bar */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"12px" }}>CURRENT RISK SCORE</div>
              <div style={{ display:"flex", alignItems:"baseline", gap:"12px" }}>
                <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"56px", fontWeight:900, color:cfg.text, lineHeight:1, letterSpacing:"-2px" }}>{p.score}</span>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"14px", color:t.red }}>▲ {p.delta} since yesterday</span>
              </div>
              <div style={{ marginTop:"16px", height:"6px", borderRadius:"6px", background:t.surfaceHigh, overflow:"hidden" }}>
                <div style={{ height:"100%", width:p.score+"%", background:"linear-gradient(90deg,#22E676,#FFB020,#FF4D4D)", borderRadius:"6px", transition:"width 1s ease" }}/>
              </div>
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:"6px" }}>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>LOW RISK</span>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>HIGH RISK</span>
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
            {/* Trajectory chart */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"20px" }}>
                <div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"16px", color:t.textPrimary }}>Recovery Trajectory</div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"3px" }}>ACTUAL vs NICE EXPECTED CURVE · {p.pathway.toUpperCase()}</div>
                </div>
                <div style={{ padding:"6px 14px", borderRadius:"8px", background:t.redBg, border:"1px solid "+t.redBorder, fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.red }}>FTP DAY {p.daysAdmitted}</div>
              </div>
              <TrajectoryChart data={p.trajectory} t={t}/>
            </div>

            {/* Tabs: Call History / SOAP / Clinical Notes */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", overflow:"hidden", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", borderBottom:"1px solid "+t.border }}>
                {[["timeline","Call History"],["soap","Latest SOAP"],["notes","Clinical Notes"]].map(([key,label])=>(
                  <button key={key} onClick={()=>setTab(key)} style={{ flex:1, padding:"14px", background:"none", border:"none", cursor:"pointer", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:tab===key?t.textPrimary:t.textMuted, borderBottom:tab===key?"2px solid "+t.brand:"2px solid transparent", transition:"all 0.15s ease" }}>{label}</button>
                ))}
              </div>
              <div style={{ padding:"20px" }}>
                {tab==="timeline" && (
                  <div style={{ display:"flex", flexDirection:"column", gap:"12px" }}>
                    {p.callHistory.map((call,i)=>{
                      const c=ragCfg(t,call.rag);
                      return (
                        <div key={call.id} style={{ display:"flex", gap:"14px", padding:"16px", borderRadius:"12px", background:i===0?c.bg:t.surfaceHigh, border:"1px solid "+(i===0?c.border:t.border) }}>
                          <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:"4px", minWidth:60 }}>
                            <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px", color:t.textPrimary }}>{call.date}</div>
                            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{call.time}</div>
                            <div style={{ display:"flex", alignItems:"center", gap:"4px", marginTop:"4px" }}>
                              <span style={{ width:6, height:6, borderRadius:"50%", background:c.dot, display:"inline-block" }}/>
                              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:c.text }}>{call.rag}</span>
                            </div>
                          </div>
                          <div style={{ flex:1 }}>
                            {call.flag && <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:c.text, marginBottom:"6px" }}>▲ {call.flag}</div>}
                            <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.6 }}>{call.summary}</div>
                            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"8px" }}>Score: {call.score} · Duration: {call.duration}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                {tab==="soap" && (
                  <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
                    {[["S","Subjective",p.soap.S],["O","Objective",p.soap.O],["A","Assessment",p.soap.A],["P","Plan",p.soap.P]].map(([key,label,text],i)=>(
                      <div key={key} style={{ display:"flex", gap:"14px" }}>
                        <div style={{ width:36, height:36, borderRadius:"10px", background:i===2?cfg.bg:t.surfaceHigh, border:"1px solid "+(i===2?cfg.border:t.border), display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"15px", color:i===2?cfg.text:t.textSecond, flexShrink:0 }}>{key}</div>
                        <div>
                          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"6px" }}>{label.toUpperCase()}</div>
                          <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13.5px", color:t.textSecond, lineHeight:1.7 }}>{text}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {tab==="notes" && (
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textSecond, lineHeight:1.8, padding:"8px 0" }}>
                    {p.notes.split("\n").map((line,i)=>(
                      <p key={i} style={{ marginBottom:"14px" }}>{line}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display:"flex", gap:"10px" }}>
              <button style={{ flex:1, padding:"13px", borderRadius:"11px", background:cfg.bg, border:"1px solid "+cfg.border, color:cfg.text, fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", cursor:"pointer" }}>▲ Escalate to Team</button>
              <button style={{ flex:1, padding:"13px", borderRadius:"11px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", cursor:"pointer" }} onClick={()=>onNav("scheduler")}>◎ Schedule Probe Call</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 3 — ALERT INBOX
// ══════════════════════════════════════════════════════════════════════════
const alerts = [
  {id:1,patient:"Margaret Osei",pid:"P-4821",age:72,ward:"Ortho A",pathway:"Hip Replacement",rag:"RED",trigger:"Failure to Progress",detail:"Pain score 8/10 — Day 4 post-op. Trajectory 47pts above expected NICE curve.",time:"2 min ago",ts:"10 Apr · 09:14",score:87,read:false,escalated:false},
  {id:2,patient:"James Whitfield",pid:"P-2091",age:81,ward:"Respiratory",pathway:"COPD Exacerbation",rag:"RED",trigger:"Respiratory Deterioration",detail:"SpO₂ dropped to 89%. Cough frequency increased significantly overnight.",time:"18 min ago",ts:"10 Apr · 08:58",score:79,read:false,escalated:true},
  {id:3,patient:"Kwame Asante",pid:"P-3887",age:65,ward:"Stroke Unit",pathway:"Ischaemic Stroke",rag:"RED",trigger:"Neurological Change",detail:"Patient reports new onset confusion and difficulty finding words during call.",time:"1h ago",ts:"10 Apr · 08:16",score:91,read:false,escalated:false},
  {id:4,patient:"David Achebe",pid:"P-3302",age:58,ward:"Cardio B",pathway:"CABG Recovery",rag:"AMBER",trigger:"Breathlessness Flag",detail:"Breathlessness on exertion reported. O₂ saturation 94% — monitoring required.",time:"5h ago",ts:"09 Apr · 22:08",score:54,read:true,escalated:false},
  {id:5,patient:"Blessing Nwosu",pid:"P-4102",age:44,ward:"Surgical",pathway:"Bowel Resection",rag:"AMBER",trigger:"Pain Above Threshold",detail:"Abdominal pain score 7/10 at Day 3 post-op. Above expected recovery threshold.",time:"6h ago",ts:"09 Apr · 21:30",score:61,read:true,escalated:false},
  {id:6,patient:"Priya Nair",pid:"P-5517",age:45,ward:"Ortho A",pathway:"Knee Replacement",rag:"GREEN",trigger:"Routine Check Passed",detail:"Recovery on track. Pain 3/10. Mobilising independently with frame.",time:"1h ago",ts:"10 Apr · 08:16",score:31,read:true,escalated:false},
];

function AlertInbox({ onNav }) {
  const { t } = useTheme();
  const [sel, setSel] = useState(alerts[0]);
  const [filter, setFilter] = useState("ALL");
  const unread = alerts.filter(a=>!a.read).length;
  const counts = {ALL:alerts.length, RED:alerts.filter(a=>a.rag==="RED").length, AMBER:alerts.filter(a=>a.rag==="AMBER").length, UNREAD:unread};
  const filtered = filter==="ALL"?alerts:filter==="UNREAD"?alerts.filter(a=>!a.read):alerts.filter(a=>a.rag===filter);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, display:"flex", flexDirection:"column", transition:"background 0.3s" }}>
      <Nav page="alerts" onNav={onNav}/>
      <div style={{ flex:1, display:"flex", overflow:"hidden" }}>
        {/* List panel */}
        <div style={{ width:400, borderRight:"1px solid "+t.border, display:"flex", flexDirection:"column", flexShrink:0 }}>
          <div style={{ padding:"14px 18px", borderBottom:"1px solid "+t.border, background:t.surface, display:"flex", gap:"6px", alignItems:"center" }}>
            <div style={{ display:"flex", alignItems:"center", gap:"6px", marginRight:"8px" }}>
              <span style={{ width:6, height:6, borderRadius:"50%", background:t.red, display:"inline-block", animation:"pulse 1.5s infinite" }}/>
              <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.red, fontWeight:600 }}>{unread} UNREAD</span>
            </div>
            {[["ALL",counts.ALL],["RED",counts.RED],["AMBER",counts.AMBER],["UNREAD",counts.UNREAD]].map(([f,c])=>(
              <button key={f} onClick={()=>setFilter(f)} style={{ padding:"4px 10px", borderRadius:"100px", cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"9px", fontWeight:600, background:filter===f?(f==="RED"?t.redBg:f==="AMBER"?t.amberBg:t.surfaceHigh):"transparent", border:"1px solid "+(filter===f?(f==="RED"?t.redBorder:f==="AMBER"?t.amberBorder:t.borderHigh):"transparent"), color:filter===f?(f==="RED"?t.red:f==="AMBER"?t.amber:t.textPrimary):t.textMuted, transition:"all 0.15s" }}>{f}({c})</button>
            ))}
          </div>
          <div style={{ flex:1, overflowY:"auto", background:t.bg }}>
            {filtered.map(a=>{
              const cfg=ragCfg(t,a.rag);
              const isSelected=sel?.id===a.id;
              return (
                <div key={a.id} onClick={()=>setSel(a)} style={{ padding:"16px 18px", cursor:"pointer", background:isSelected?t.surface:"transparent", borderLeft:"3px solid "+(isSelected?cfg.dot:(a.read?t.border:cfg.border)), borderBottom:"1px solid "+t.border, transition:"all 0.15s", position:"relative" }}
                  onMouseEnter={e=>{ if(!isSelected) e.currentTarget.style.background=t.surfaceHigh; }}
                  onMouseLeave={e=>{ if(!isSelected) e.currentTarget.style.background="transparent"; }}>
                  {!a.read && <div style={{ position:"absolute", top:"50%", right:14, transform:"translateY(-50%)", width:7, height:7, borderRadius:"50%", background:cfg.dot, boxShadow:"0 0 6px "+cfg.dot }}/>}
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"6px" }}>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", color:t.textPrimary }}>{a.patient}</div>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{a.time}</div>
                  </div>
                  <div style={{ display:"flex", alignItems:"center", gap:"7px", marginBottom:"5px" }}>
                    <span style={{ padding:"2px 7px", borderRadius:"100px", background:cfg.bg, border:"1px solid "+cfg.border, fontFamily:"'DM Mono',monospace", fontSize:"9px", color:cfg.text }}>{a.rag}</span>
                    <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:cfg.text, fontWeight:600 }}>{a.trigger}</span>
                    {a.escalated && <span style={{ padding:"2px 6px", borderRadius:"100px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>ESCALATED</span>}
                  </div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textMuted, lineHeight:1.5 }}>{a.detail.slice(0,80)}...</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        {sel && (()=>{
          const cfg=ragCfg(t,sel.rag);
          return (
            <div style={{ flex:1, overflowY:"auto", padding:"28px 32px" }}>
              <div style={{ maxWidth:640 }}>
                <div style={{ background:cfg.bg, border:"1px solid "+cfg.border, borderRadius:"18px", padding:"24px", marginBottom:"18px", boxShadow:cfg.glow, position:"relative", overflow:"hidden" }}>
                  <div style={{ position:"absolute", top:0, left:0, right:0, height:"2px", background:"linear-gradient(90deg,transparent,"+cfg.dot+",transparent)" }}/>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"14px" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
                      <div style={{ width:48, height:48, borderRadius:"50%", background:t.surface, border:"2px solid "+cfg.border, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:cfg.text }}>
                        {sel.patient.split(" ").map(n=>n[0]).join("")}
                      </div>
                      <div>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"20px", color:t.textPrimary }}>{sel.patient}</div>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:cfg.text, opacity:0.8, marginTop:"2px" }}>{sel.pid} · Age {sel.age} · {sel.ward}</div>
                      </div>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"48px", fontWeight:900, color:cfg.text, lineHeight:1, letterSpacing:"-2px" }}>{sel.score}</div>
                  </div>
                  <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"10px" }}>
                    <span style={{ width:8, height:8, borderRadius:"50%", background:cfg.dot, display:"inline-block", boxShadow:"0 0 8px "+cfg.dot, animation:sel.rag==="RED"?"pulse 1.5s infinite":"none" }}/>
                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"12px", fontWeight:600, color:cfg.text }}>{sel.rag} · {sel.trigger}</span>
                  </div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textSecond, lineHeight:1.7 }}>{sel.detail}</div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:cfg.text, opacity:0.5, marginTop:"12px" }}>TRIGGERED {sel.ts.toUpperCase()} · {sel.pathway.toUpperCase()}</div>
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"10px", marginBottom:"18px" }}>
                  {[["▲ Escalate to Team",cfg.bg,cfg.border,cfg.text],["◎ Schedule Probe Call",t.brandGlow,t.brand+"40",t.brand],["◈ View Patient Detail",t.surfaceHigh,t.border,t.textSecond],["✓ Mark as Resolved",t.surfaceHigh,t.border,t.textSecond]].map(([lbl,bg,brd,c])=>(
                    <button key={lbl} onClick={lbl.includes("Probe")?()=>onNav("scheduler"):lbl.includes("Patient")?()=>onNav("queue"):undefined} style={{ padding:"13px", borderRadius:"11px", background:bg, border:"1px solid "+brd, color:c, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", cursor:"pointer", transition:"all 0.15s" }}>{lbl}</button>
                  ))}
                </div>
                <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"14px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow }}>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"14px" }}>CLINICAL CONTEXT</div>
                  {[["Pathway",sel.pathway],["Ward",sel.ward],["Alert Time",sel.ts],["Risk Score",sel.score+" / 100"],["Status",sel.escalated?"Escalated to team":"Awaiting action"]].map(([k,v])=>(
                    <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border }}>
                      <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                      <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:500 }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 4 — PROBE CALL SCHEDULER (full original design + theme)
// ══════════════════════════════════════════════════════════════════════════
const schedPatients = [
  {id:"P-4821",name:"Margaret Osei",ward:"Ortho A",pathway:"Hip Replacement",rag:"RED",score:87},
  {id:"P-3302",name:"David Achebe",ward:"Cardio B",pathway:"CABG Recovery",rag:"AMBER",score:54},
  {id:"P-5517",name:"Priya Nair",ward:"Ortho A",pathway:"Knee Replacement",rag:"GREEN",score:31},
  {id:"P-2091",name:"James Whitfield",ward:"Respiratory",pathway:"COPD Exacerbation",rag:"AMBER",score:61},
  {id:"P-6634",name:"Fatima Al-Hassan",ward:"Maternity",pathway:"Post C-Section",rag:"GREEN",score:22},
];
const times2=["08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30","14:00","14:30","15:00","15:30","16:00","16:30"];
const reasons2=["Routine Check-in","FTP Follow-up","Pain Review","Medication Query","Respiratory Check","Wound Concern","Escalation Follow-up","Discharge Planning"];
const callQueue=[{id:"S-001",patient:"Margaret Osei",time:"08:00",date:"Tomorrow",type:"FTP Follow-up",rag:"RED"},{id:"S-002",patient:"James Whitfield",time:"09:30",date:"Tomorrow",type:"Respiratory Check",rag:"AMBER"},{id:"S-003",patient:"David Achebe",time:"14:00",date:"Today",type:"Routine",rag:"AMBER"}];

function ProbeScheduler({ onNav }) {
  const { t } = useTheme();
  const [search, setSearch] = useState("");
  const [selP, setSelP] = useState(schedPatients[0]);
  const [selTime, setSelTime] = useState("08:00");
  const [selDate, setSelDate] = useState("tomorrow");
  const [selReason, setSelReason] = useState("Routine Check-in");
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState(false);
  const cfg = ragCfg(t, selP.rag);
  const filtered2 = schedPatients.filter(p=>p.name.toLowerCase().includes(search.toLowerCase())||p.id.toLowerCase().includes(search.toLowerCase()));

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="scheduler" onNav={onNav}/>
      <div style={{ maxWidth:1100, margin:"0 auto", padding:"36px 24px" }}>
        <div style={{ marginBottom:"28px" }}>
          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>CLINICIAN-INITIATED · OUTBOUND CALL</div>
          <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"32px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Schedule a Probe Call</h1>
          <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textMuted, marginTop:"6px" }}>AI-powered outbound call with structured SOAP output and automatic RAG scoring</p>
        </div>

        {success && (
          <div style={{ padding:"14px 20px", borderRadius:"12px", background:t.greenBg, border:"1px solid "+t.greenBorder, marginBottom:"24px", display:"flex", alignItems:"center", gap:"12px" }}>
            <span style={{ color:t.green, fontSize:"20px" }}>✓</span>
            <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.green, fontWeight:600 }}>Probe call scheduled — Sizor will call {selP.name} at {selTime}</span>
          </div>
        )}

        <div style={{ display:"grid", gridTemplateColumns:"1fr 340px", gap:"20px" }}>
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
            {/* Step 1 */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>STEP 1 · SELECT PATIENT</div>
              <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search by name or patient ID..." style={{ width:"100%", padding:"11px 16px", borderRadius:"10px", background:t.bg, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"14px", color:t.textPrimary, marginBottom:"12px", outline:"none" }}/>
              <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
                {filtered2.map(p=>{
                  const c=ragCfg(t,p.rag); const sel2=selP?.id===p.id;
                  return (
                    <div key={p.id} onClick={()=>setSelP(p)} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"12px 16px", borderRadius:"10px", cursor:"pointer", background:sel2?c.bg:t.surfaceHigh, border:"1px solid "+(sel2?c.border:t.border), transition:"all 0.15s" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                        <div style={{ width:34, height:34, borderRadius:"50%", background:sel2?t.surface:t.overlay, border:"1px solid "+(sel2?c.border:t.border), display:"flex", alignItems:"center", justifyContent:"center", fontSize:"11px", fontWeight:700, color:sel2?c.text:t.textSecond, fontFamily:"'Outfit',sans-serif" }}>
                          {p.name.split(" ").map(n=>n[0]).join("")}
                        </div>
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
            </div>

            {/* Step 2 */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>STEP 2 · SCHEDULE DATE & TIME</div>
              <div style={{ display:"flex", gap:"10px", marginBottom:"16px" }}>
                {[["today","Today"],["tomorrow","Tomorrow"],["custom","Custom Date"]].map(([val,label])=>(
                  <button key={val} onClick={()=>setSelDate(val)} style={{ flex:1, padding:"10px", borderRadius:"10px", cursor:"pointer", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", background:selDate===val?t.brandGlow:t.surfaceHigh, border:"1px solid "+(selDate===val?t.brand+"40":t.border), color:selDate===val?t.brand:t.textMuted, transition:"all 0.15s" }}>{label}</button>
                ))}
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:"8px" }}>
                {times2.map(tm=>(
                  <button key={tm} onClick={()=>setSelTime(tm)} style={{ padding:"9px 4px", borderRadius:"8px", cursor:"pointer", fontFamily:"'DM Mono',monospace", fontSize:"11px", background:selTime===tm?t.brandGlow:t.surfaceHigh, border:"1px solid "+(selTime===tm?t.brand+"40":t.border), color:selTime===tm?t.brand:t.textMuted, transition:"all 0.15s" }}>{tm}</button>
                ))}
              </div>
            </div>

            {/* Step 3 */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"16px" }}>STEP 3 · CALL REASON & CONTEXT</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"8px", marginBottom:"16px" }}>
                {reasons2.map(r=>(
                  <button key={r} onClick={()=>setSelReason(r)} style={{ padding:"10px 14px", borderRadius:"8px", cursor:"pointer", textAlign:"left", fontFamily:"'Outfit',sans-serif", fontWeight:500, fontSize:"13px", background:selReason===r?t.brandGlow:t.surfaceHigh, border:"1px solid "+(selReason===r?t.brand+"40":t.border), color:selReason===r?t.brand:t.textSecond, transition:"all 0.15s" }}>{r}</button>
                ))}
              </div>
              <textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Additional context for the AI call agent (optional)..." rows={3} style={{ width:"100%", padding:"12px 16px", borderRadius:"10px", background:t.bg, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textPrimary, resize:"none", lineHeight:1.6, outline:"none" }}/>
            </div>

            <button onClick={()=>{setSuccess(true);setTimeout(()=>setSuccess(false),3500);}}
              onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow="0 16px 48px #0AAFA860";}}
              onMouseLeave={e=>{e.currentTarget.style.transform="translateY(0)";e.currentTarget.style.boxShadow="0 8px 32px #0AAFA840";}}
              style={{ padding:"16px", borderRadius:"14px", background:"linear-gradient(135deg,#0AAFA8,#076E69)", border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", cursor:"pointer", boxShadow:"0 8px 32px #0AAFA840", transition:"all 0.2s ease" }}>
              ◎ &nbsp; Schedule Probe Call for {selP?.name}
            </button>
          </div>

          {/* Right panel */}
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
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
              {[["Date",selDate==="today"?"Today":"Tomorrow"],["Time",selTime],["Reason",selReason],["Current RAG",selP.rag],["Risk Score",selP.score+" / 100"],["Ward",selP.ward]].map(([k,v])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border+"80" }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:k==="Current RAG"?cfg.text:t.textSecond, fontWeight:600 }}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"14px" }}>CALL QUEUE · NEXT 24H</div>
              {callQueue.map(q=>{
                const qc=ragCfg(t,q.rag);
                return (
                  <div key={q.id} style={{ display:"flex", alignItems:"center", gap:"12px", padding:"12px", borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border, marginBottom:"8px" }}>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"13px", fontWeight:500, color:t.brand, width:44, flexShrink:0 }}>{q.time}</div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:t.textPrimary, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{q.patient}</div>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginTop:"2px" }}>{q.date} · {q.type}</div>
                    </div>
                    <span style={{ width:8, height:8, borderRadius:"50%", background:qc.dot, display:"inline-block", flexShrink:0, boxShadow:"0 0 6px "+qc.dot }}/>
                  </div>
                );
              })}
            </div>

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

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 5 — ANALYTICS (original bar chart + table + pathway detail)
// ══════════════════════════════════════════════════════════════════════════
const pathwayData=[
  {name:"Hip Replacement",code:"W37",calls:284,completion:94,avgScore:41,ftpRate:12,redRate:8,improvement:+18,trend:[48,45,43,41,39,41,41]},
  {name:"Knee Replacement",code:"W40",calls:216,completion:91,avgScore:35,ftpRate:9,redRate:5,improvement:+22,trend:[55,50,44,40,37,35,35]},
  {name:"CABG Recovery",code:"K40",calls:178,completion:89,avgScore:38,ftpRate:14,redRate:11,improvement:+9,trend:[44,42,41,40,39,38,38]},
  {name:"COPD Exacerbation",code:"J44",calls:142,completion:76,avgScore:58,ftpRate:22,redRate:18,improvement:-4,trend:[52,54,55,57,56,59,58]},
  {name:"Post C-Section",code:"R17",calls:198,completion:98,avgScore:22,ftpRate:3,redRate:1,improvement:+31,trend:[60,50,40,32,27,23,22]},
  {name:"Ischaemic Stroke",code:"I63",calls:124,completion:81,avgScore:64,ftpRate:19,redRate:15,improvement:+6,trend:[70,68,67,65,65,63,64]},
];
const weekly=[{day:"Mon",calls:42,red:6},{day:"Tue",calls:58,red:9},{day:"Wed",calls:51,red:7},{day:"Thu",calls:63,red:11},{day:"Fri",calls:48,red:8},{day:"Sat",calls:31,red:4},{day:"Sun",calls:24,red:3}];

function Analytics({ onNav }) {
  const { t } = useTheme();
  const [selPath, setSelPath] = useState(pathwayData[0]);
  const maxC = Math.max(...weekly.map(d=>d.calls));

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="analytics" onNav={onNav}/>
      <div style={{ maxWidth:1280, margin:"0 auto", padding:"32px 24px" }}>
        <div style={{ marginBottom:"28px", display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
          <div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>TRUST-WIDE · PAST 7 DAYS</div>
            <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"32px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Pathway Analytics</h1>
          </div>
          <div style={{ display:"flex", gap:"8px" }}>
            {["7D","30D","90D"].map((r,i)=>(
              <button key={r} style={{ padding:"6px 14px", borderRadius:"8px", background:i===0?t.brandGlow:t.surfaceHigh, border:"1px solid "+(i===0?t.brand+"40":t.border), color:i===0?t.brand:t.textMuted, fontFamily:"'DM Mono',monospace", fontSize:"11px", cursor:"pointer" }}>{r}</button>
            ))}
          </div>
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"24px" }}>
          {[{label:"Total Calls",val:"1,142",color:t.brand},{label:"Avg Completion",val:"88%",color:t.green},{label:"RED Escalations",val:"58",color:t.red},{label:"Pathways Active",val:"23",color:t.amber}].map((s,i)=>(
            <div key={i} style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"16px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow, animation:"fadeUp 0.4s ease "+(i*60)+"ms both" }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"10px" }}>{s.label.toUpperCase()}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"38px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{s.val}</div>
            </div>
          ))}
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 300px", gap:"18px" }}>
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>
            {/* Weekly volume bar chart */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px", marginBottom:"20px" }}>WEEKLY CALL VOLUME</div>
              <div style={{ display:"flex", alignItems:"flex-end", gap:"8px", height:120 }}>
                {weekly.map((d,i)=>(
                  <div key={d.day} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:"6px", height:"100%" }}>
                    <div style={{ flex:1, width:"100%", display:"flex", flexDirection:"column", justifyContent:"flex-end", gap:"2px" }}>
                      <div style={{ height:(d.red/maxC*100)+"%", background:t.red+"60", borderRadius:"3px 3px 0 0", minHeight:2 }}/>
                      <div style={{ height:((d.calls-d.red)/maxC*100)+"%", background:i===6?t.textMuted:t.brand, borderRadius:"3px 3px 0 0", minHeight:4 }}/>
                    </div>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>{d.day}</div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"11px", color:t.textSecond, fontWeight:600 }}>{d.calls}</div>
                  </div>
                ))}
              </div>
              <div style={{ display:"flex", gap:"16px", marginTop:"14px" }}>
                {[[t.brand,"CALLS COMPLETED"],[t.red+"60","RED FLAGS"]].map(([c,l])=>(
                  <div key={l} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
                    <div style={{ width:10, height:10, borderRadius:"2px", background:c }}/>
                    <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Pathway table */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", overflow:"hidden", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ padding:"18px 24px", borderBottom:"1px solid "+t.border }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>PATHWAY PERFORMANCE</div>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"2fr 70px 80px 80px 80px 80px", padding:"10px 24px", borderBottom:"1px solid "+t.border }}>
                {["PATHWAY","CALLS","COMPLT","AVG RISK","FTP%","TREND"].map(h=>(
                  <div key={h} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>{h}</div>
                ))}
              </div>
              {pathwayData.map((p,i)=>{
                const sc=p.avgScore>55?t.red:p.avgScore>40?t.amber:t.green;
                const sel3=selPath.name===p.name;
                return (
                  <div key={p.name} onClick={()=>setSelPath(p)} style={{ display:"grid", gridTemplateColumns:"2fr 70px 80px 80px 80px 80px", padding:"14px 24px", cursor:"pointer", background:sel3?t.surfaceHigh:"transparent", borderBottom:i<pathwayData.length-1?"1px solid "+t.border:"none", borderLeft:sel3?"2px solid "+t.brand:"2px solid transparent", transition:"all 0.15s" }}>
                    <div>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:t.textPrimary }}>{p.name}</div>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginTop:"2px" }}>OPCS {p.code}</div>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:t.textSecond, alignSelf:"center" }}>{p.calls}</div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:p.completion>=90?t.green:p.completion>=80?t.amber:t.red, alignSelf:"center" }}>{p.completion}%</div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:sc, alignSelf:"center" }}>{p.avgScore}</div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:p.ftpRate>15?t.red:p.ftpRate>10?t.amber:t.green, alignSelf:"center" }}>{p.ftpRate}%</div>
                    <div style={{ alignSelf:"center" }}><Sparkline data={p.trend} color={p.improvement>=0?t.red:t.green} w={60} h={24}/></div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pathway detail */}
          <div style={{ display:"flex", flexDirection:"column", gap:"14px" }}>
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"22px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"14px" }}>SELECTED PATHWAY</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:t.textPrimary, marginBottom:"4px" }}>{selPath.name}</div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, marginBottom:"20px" }}>OPCS-4 · {selPath.code}</div>
              <div style={{ textAlign:"center", marginBottom:"20px" }}>
                <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"52px", fontWeight:900, color:selPath.avgScore>55?t.red:selPath.avgScore>40?t.amber:t.green, lineHeight:1, letterSpacing:"-2px" }}>{selPath.avgScore}</div>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"4px" }}>AVG RISK SCORE</div>
              </div>
              {[["Calls This Week",selPath.calls],["Completion Rate",selPath.completion+"%"],["FTP Rate",selPath.ftpRate+"%"],["RED Flag Rate",selPath.redRate+"%"],["Score Change",(selPath.improvement>0?"▲ ":"▼ ")+Math.abs(selPath.improvement)+"pts"]].map(([k,v])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:600 }}>{v}</span>
                </div>
              ))}
            </div>
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"22px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"14px" }}>RISK TREND · 7 DAYS</div>
              <Sparkline data={selPath.trend} color={selPath.improvement>0?t.red:t.green} w={240} h={40}/>
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:"6px" }}>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>7 DAYS AGO</span>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>TODAY</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 6 — LANDING PAGE (full original with scroll ticker + how it works)
// ══════════════════════════════════════════════════════════════════════════
const pathwayPills=["Hip Replacement","Knee Replacement","CABG Recovery","COPD Exacerbation","Post C-Section","Ischaemic Stroke","TIA","Bowel Resection","Heart Failure","Pneumonia","AF Management","Spinal Fusion","Pre-eclampsia","Haemorrhagic Stroke","Hernia Repair","Asthma","DVT","PE Management","Diabetic Foot","Renal Transplant","Liver Resection","Bariatric Surgery","Appendectomy"];

function Landing({ onNav }) {
  const { t } = useTheme();
  const [hov, setHov] = useState(null);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav page="landing" onNav={onNav}/>

      {/* Hero */}
      <div style={{ paddingTop:80, paddingBottom:80, textAlign:"center", position:"relative", overflow:"hidden" }}>
        <div style={{ position:"absolute", top:"30%", left:"50%", transform:"translateX(-50%)", width:600, height:400, background:"radial-gradient(ellipse,"+t.brand+"18 0%,transparent 70%)", pointerEvents:"none" }}/>
        <div style={{ display:"inline-flex", alignItems:"center", gap:"8px", padding:"6px 16px", borderRadius:"100px", background:t.brandGlow, border:"1px solid "+t.brand+"30", marginBottom:"28px", animation:"fadeUp 0.5s ease 0.1s both" }}>
          <span style={{ width:6, height:6, borderRadius:"50%", background:t.green, display:"inline-block", animation:"pulse 2s infinite" }}/>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.brand }}>DTAC-aligned · DCB0129-ready · NHS-compatible</span>
        </div>
        <h1 style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"clamp(38px,6vw,68px)", color:t.textPrimary, letterSpacing:"-2px", lineHeight:1.05, marginBottom:"20px", animation:"fadeUp 0.5s ease 0.2s both" }}>
          AI-powered post-discharge<br/>
          <span style={{ background:"linear-gradient(90deg,#0AAFA8,#00E5C8)", WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>patient monitoring</span>
        </h1>
        <p style={{ fontFamily:"'Outfit',sans-serif", fontSize:"18px", color:t.textSecond, maxWidth:520, margin:"0 auto 36px", lineHeight:1.7, animation:"fadeUp 0.5s ease 0.3s both" }}>
          Sizor makes intelligent outbound calls to NHS patients after discharge, generates structured SOAP notes, and flags clinical risk — automatically.
        </p>
        <div style={{ display:"flex", justifyContent:"center", gap:"12px", animation:"fadeUp 0.5s ease 0.4s both" }}>
          <button onClick={()=>onNav("ward")}
            onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow="0 20px 60px #0AAFA860";}}
            onMouseLeave={e=>{e.currentTarget.style.transform="translateY(0)";e.currentTarget.style.boxShadow="0 12px 40px #0AAFA840";}}
            style={{ padding:"14px 32px", borderRadius:"12px", background:"linear-gradient(135deg,#0AAFA8,#076E69)", border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"16px", cursor:"pointer", boxShadow:"0 12px 40px #0AAFA840", transition:"all 0.2s", letterSpacing:"-0.3px" }}>
            View Live Demo →
          </button>
          <button style={{ padding:"14px 32px", borderRadius:"12px", background:"transparent", border:"1px solid "+t.border, color:t.textSecond, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"16px", cursor:"pointer" }}>View Pathways</button>
        </div>

        {/* Floating dashboard preview */}
        <div style={{ maxWidth:860, margin:"64px auto 0", animation:"fadeUp 0.6s ease 0.5s both", position:"relative" }}>
          <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"20px", padding:"20px", boxShadow:"0 40px 100px "+t.shadow+", 0 0 0 1px "+t.border }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"16px" }}>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:t.textPrimary }}>Ward Overview · Ortho A</div>
              <div style={{ display:"flex", gap:"8px" }}>
                {[[t.red,t.redBg,t.redBorder,"2"],[t.amber,t.amberBg,t.amberBorder,"4"],[t.green,t.greenBg,t.greenBorder,"6"]].map(([c,bg,brd,n],i)=>(
                  <div key={i} style={{ padding:"4px 12px", borderRadius:"100px", background:bg, border:"1px solid "+brd, fontFamily:"'DM Mono',monospace", fontSize:"12px", color:c, fontWeight:700 }}>{n}</div>
                ))}
              </div>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:"10px" }}>
              {[{name:"M. Osei",score:87,rag:"RED"},{name:"D. Achebe",score:54,rag:"AMBER"},{name:"P. Nair",score:31,rag:"GREEN"}].map((p,i)=>{
                const c=ragCfg(t,p.rag);
                return (
                  <div key={i} style={{ padding:"14px", borderRadius:"12px", background:c.bg, border:"1px solid "+c.border }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"8px" }}>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px", color:t.textPrimary }}>{p.name}</div>
                      <div style={{ width:8, height:8, borderRadius:"50%", background:c.dot, boxShadow:"0 0 8px "+c.dot }}/>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"28px", fontWeight:900, color:c.text, lineHeight:1 }}>{p.score}</div>
                  </div>
                );
              })}
            </div>
          </div>
          <div style={{ position:"absolute", bottom:-40, left:"10%", right:"10%", height:60, background:"radial-gradient(ellipse,"+t.brand+"30,transparent)", filter:"blur(20px)" }}/>
        </div>
      </div>

      {/* Scrolling pathway ticker */}
      <div style={{ padding:"28px 0", overflow:"hidden", borderTop:"1px solid "+t.border, borderBottom:"1px solid "+t.border, background:t.surface }}>
        <div style={{ display:"flex", gap:"10px", animation:"scroll 35s linear infinite", width:"max-content" }}>
          {[...pathwayPills,...pathwayPills].map((p,i)=>(
            <div key={i} style={{ padding:"7px 16px", borderRadius:"100px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted, whiteSpace:"nowrap" }}>{p}</div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div style={{ maxWidth:900, margin:"0 auto", padding:"70px 24px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"16px" }}>
          {[{v:"23",l:"Clinical Pathways",s:"NICE-coded"},{v:"98%",l:"Call Completion",s:"Across pilots"},{v:"<2min",l:"SOAP Generation",s:"Post-call"},{v:"RAG",l:"Risk Stratification",s:"Automated"}].map((s,i)=>(
            <div key={i} style={{ textAlign:"center", padding:"28px 16px", background:t.surface, border:"1px solid "+t.border, borderRadius:"16px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"34px", color:t.brand, letterSpacing:"-1px", lineHeight:1 }}>{s.v}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"14px", color:t.textPrimary, marginTop:"8px" }}>{s.l}</div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"4px" }}>{s.s.toUpperCase()}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div style={{ maxWidth:900, margin:"0 auto", padding:"0 24px 80px" }}>
        <div style={{ textAlign:"center", marginBottom:"48px" }}>
          <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"10px" }}>THE SIZOR WORKFLOW</div>
          <h2 style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"36px", color:t.textPrimary, letterSpacing:"-1px" }}>From discharge to insight in under 10 minutes</h2>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px" }}>
          {[{n:"01",title:"Patient Discharged",desc:"Sizor automatically schedules post-discharge calls based on OPCS-4 procedure code and clinical pathway.",icon:"◈"},{n:"02",title:"AI Outbound Call",desc:"Voice agent calls patient using natural British English, following SOCRATES-style probing for structured symptom capture.",icon:"◎"},{n:"03",title:"SOAP Note Generated",desc:"Structured SOAP note with clinical risk score and RAG flag available within 90 seconds of call completion.",icon:"◉"},{n:"04",title:"Clinician Alerted",desc:"RED flags trigger immediate escalation. AMBER schedules a follow-up probe call. GREEN continues monitoring.",icon:"▲"}].map((s,i)=>(
            <div key={i} onMouseEnter={()=>setHov(i)} onMouseLeave={()=>setHov(null)} style={{ padding:"24px", borderRadius:"16px", background:hov===i?t.surfaceHigh:t.surface, border:"1px solid "+(hov===i?t.borderHigh:t.border), transition:"all 0.2s", transform:hov===i?"translateY(-3px)":"translateY(0)", boxShadow:hov===i?"0 16px 48px "+t.shadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:"14px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.brand }}>STEP {s.n}</div>
                <div style={{ width:34, height:34, borderRadius:"9px", background:t.brandGlow, border:"1px solid "+t.brand+"30", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", color:t.brand }}>{s.icon}</div>
              </div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:t.textPrimary, marginBottom:"8px" }}>{s.title}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, lineHeight:1.7 }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{ textAlign:"center", padding:"60px 24px", borderTop:"1px solid "+t.border, position:"relative" }}>
        <div style={{ position:"absolute", top:"50%", left:"50%", transform:"translate(-50%,-50%)", width:500, height:300, background:"radial-gradient(ellipse,"+t.brand+"15,transparent 70%)", pointerEvents:"none" }}/>
        <h2 style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"40px", color:t.textPrimary, letterSpacing:"-1px", marginBottom:"14px" }}>Ready to transform post-discharge care?</h2>
        <p style={{ fontSize:"17px", color:t.textSecond, marginBottom:"32px", fontFamily:"'Outfit',sans-serif" }}>Join NHS trusts using Sizor to reduce readmissions and free up clinical time.</p>
        <button onClick={()=>onNav("ward")}
          onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-3px)";e.currentTarget.style.boxShadow="0 24px 60px #0AAFA860";}}
          onMouseLeave={e=>{e.currentTarget.style.transform="translateY(0)";e.currentTarget.style.boxShadow="0 16px 48px #0AAFA850";}}
          style={{ padding:"15px 36px", borderRadius:"12px", background:"linear-gradient(135deg,#0AAFA8,#076E69)", border:"none", color:"#fff", fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"17px", cursor:"pointer", boxShadow:"0 16px 48px #0AAFA850", transition:"all 0.2s" }}>
          Request an NHS Demo
        </button>
        <div style={{ marginTop:"16px", fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>DTAC-aligned · DCB0129-ready · NHS Digital compliant</div>
      </div>

      <div style={{ padding:"20px 32px", borderTop:"1px solid "+t.border, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"8px" }}>
          <div style={{ width:22, height:22, borderRadius:"6px", background:"linear-gradient(135deg,#0AAFA8,#00E5C8)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"11px" }}>◈</div>
          <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", color:t.textPrimary }}>Sizor</span>
        </div>
        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>© 2026 Sizor Health Ltd · Built for the NHS</span>
        <div style={{ display:"flex", gap:"20px" }}>
          {["Privacy","Terms","DTAC","Contact"].map(l=>(
            <button key={l} style={{ background:"none", border:"none", fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, cursor:"pointer" }}>{l}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════
// ROOT — wires all screens together
// ══════════════════════════════════════════════════════════════════════════
export default function SizorApp() {
  const [isDark, setIsDark] = useState(true);
  const [page, setPage] = useState("landing");
  const [selectedPatient, setSelectedPatient] = useState(null);
  const t = isDark ? DARK : LIGHT;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-thumb { background:${t.scrollThumb}; border-radius:4px; }
        @keyframes fadeUp { from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);} }
        @keyframes pulse { 0%,100%{opacity:1;}50%{opacity:0.3;} }
        @keyframes scroll { 0%{transform:translateX(0);}100%{transform:translateX(-50%);} }
        button { outline:none; }
        input, textarea { outline:none; }
      `}</style>
      <ThemeCtx.Provider value={{ t, isDark, toggle:()=>setIsDark(d=>!d) }}>
        {page==="landing"   && <Landing        onNav={setPage}/>}
        {page==="ward"      && <WardDashboard   onNav={setPage}/>}
        {page==="queue"     && <PatientQueue    onNav={setPage} onSelectPatient={setSelectedPatient}/>}
        {page==="detail"    && <PatientDetail   onNav={setPage} patient={selectedPatient}/>}
        {page==="alerts"    && <AlertInbox      onNav={setPage}/>}
        {page==="scheduler" && <ProbeScheduler  onNav={setPage}/>}
        {page==="analytics" && <Analytics       onNav={setPage}/>}
      </ThemeCtx.Provider>
    </>
  );
}

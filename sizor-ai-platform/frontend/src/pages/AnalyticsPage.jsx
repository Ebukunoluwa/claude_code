import { useState, useEffect } from "react";
import { getDashboard } from "../api/decisions";
import { useTheme } from "../theme/ThemeContext";
import Nav from "../components/Nav";
import Sparkline from "../components/Sparkline";

// ---------- static demo data per range ----------

const BASE_PATHWAYS = [
  { name:"Hip Replacement",   code:"W37", completion:94, ftpRate:12, redRate:8,  improvement:+18 },
  { name:"Knee Replacement",  code:"W40", completion:91, ftpRate:9,  redRate:5,  improvement:+22 },
  { name:"CABG Recovery",     code:"K40", completion:89, ftpRate:14, redRate:11, improvement:+9  },
  { name:"COPD Exacerbation", code:"J44", completion:76, ftpRate:22, redRate:18, improvement:-4  },
  { name:"Post C-Section",    code:"R17", completion:98, ftpRate:3,  redRate:1,  improvement:+31 },
  { name:"Ischaemic Stroke",  code:"I63", completion:81, ftpRate:19, redRate:15, improvement:+6  },
];

const PATHWAY_RANGES = {
  "7D": [
    { calls:284, avgScore:41, trend:[48,45,43,41,39,41,41] },
    { calls:216, avgScore:35, trend:[55,50,44,40,37,35,35] },
    { calls:178, avgScore:38, trend:[44,42,41,40,39,38,38] },
    { calls:142, avgScore:58, trend:[52,54,55,57,56,59,58] },
    { calls:198, avgScore:22, trend:[60,50,40,32,27,23,22] },
    { calls:124, avgScore:64, trend:[70,68,67,65,65,63,64] },
  ],
  "30D": [
    { calls:1142, avgScore:43, trend:[50,47,45,43,42,43,43,44,42,41,40,41,41,42,40,39,41,43,42,41,39,40,41,42,41,40,41,42,41,41] },
    { calls:864,  avgScore:37, trend:[57,54,51,48,45,43,40,38,37,36,35,36,37,38,36,35,36,37,36,35,35,36,37,37,36,35,36,37,37,37] },
    { calls:712,  avgScore:40, trend:[46,45,44,43,42,41,40,40,39,39,38,39,40,40,39,38,39,40,40,39,38,39,40,40,39,38,39,40,40,40] },
    { calls:568,  avgScore:60, trend:[53,55,57,58,59,60,61,60,59,60,61,60,59,60,61,61,60,60,59,60,60,60,59,60,60,60,60,61,60,60] },
    { calls:792,  avgScore:24, trend:[62,58,54,50,46,42,38,34,30,28,26,24,23,24,24,24,23,24,24,24,24,24,24,24,24,23,24,24,24,24] },
    { calls:496,  avgScore:66, trend:[72,71,70,69,68,67,66,65,66,66,65,65,66,66,66,65,65,65,66,66,66,65,65,66,66,66,66,66,66,66] },
  ],
  "90D": [
    { calls:3428, avgScore:44, trend:[52,50,48,46,44,43,44] },
    { calls:2592, avgScore:38, trend:[58,55,50,45,41,38,38] },
    { calls:2136, avgScore:41, trend:[47,46,44,43,42,41,41] },
    { calls:1704, avgScore:61, trend:[55,56,58,60,61,61,61] },
    { calls:2376, avgScore:25, trend:[63,55,45,35,28,25,25] },
    { calls:1488, avgScore:67, trend:[73,71,70,69,68,67,67] },
  ],
};

const CHART_DATA = {
  "7D": {
    bars: [
      {label:"Mon",calls:42,red:6},{label:"Tue",calls:58,red:9},{label:"Wed",calls:51,red:7},
      {label:"Thu",calls:63,red:11},{label:"Fri",calls:48,red:8},{label:"Sat",calls:31,red:4},{label:"Sun",calls:24,red:3},
    ],
    xLabel: "DAY",
  },
  "30D": {
    bars: [
      {label:"Wk 1",calls:317,red:48},{label:"Wk 2",calls:298,red:41},{label:"Wk 3",calls:341,red:55},
      {label:"Wk 4",calls:322,red:50},{label:"Wk 5",calls:196,red:30},
    ],
    xLabel: "WEEK",
  },
  "90D": {
    bars: [
      {label:"Jan",calls:1142,red:178},{label:"Feb",calls:1287,red:196},{label:"Mar",calls:1399,red:214},
    ],
    xLabel: "MONTH",
  },
};

const RANGE_LABELS = { "7D":"PAST 7 DAYS", "30D":"PAST 30 DAYS", "90D":"PAST 90 DAYS" };

export default function AnalyticsPage() {
  const { t } = useTheme();
  const [range, setRange]     = useState("7D");
  const [selIdx, setSelIdx]   = useState(0);
  const [totals, setTotals]   = useState({ calls:"—", completion:"—", red:"—", pathways:"—" });

  useEffect(() => {
    getDashboard()
      .then(data => {
        const wl = data.worklist || [];
        const s  = data.stats || {};
        const red = wl.filter(p => p.urgency_severity === "red").length;
        const pathways = new Set(wl.map(p => p.condition).filter(Boolean)).size;
        setTotals({
          calls:      s.calls_today ?? (wl.filter(p => p.last_call_at).length || "—"),
          completion: "88%",
          red:        s.open_escalations ?? (red || "—"),
          pathways:   pathways || 23,
        });
      })
      .catch(() => {});
  }, []);

  const pathwayData = BASE_PATHWAYS.map((p, i) => ({ ...p, ...PATHWAY_RANGES[range][i] }));
  const selPath     = pathwayData[selIdx];
  const chartData   = CHART_DATA[range];
  const maxC        = Math.max(...chartData.bars.map(d => d.calls));

  // Scale live totals for 30D / 90D
  const mult   = range === "30D" ? 4 : range === "90D" ? 13 : 1;
  const scCalls = typeof totals.calls === "number" ? totals.calls * mult : totals.calls;
  const scRed   = typeof totals.red   === "number" ? totals.red   * mult : totals.red;

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>
      <div style={{ maxWidth:1280, margin:"0 auto", padding:"32px 24px" }}>

        {/* Header */}
        <div style={{ marginBottom:"28px", display:"flex", justifyContent:"space-between", alignItems:"flex-end" }}>
          <div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, letterSpacing:"2px", marginBottom:"8px" }}>
              TRUST-WIDE · {RANGE_LABELS[range]}
            </div>
            <h1 style={{ fontFamily:"'Outfit',sans-serif", fontSize:"32px", fontWeight:900, color:t.textPrimary, letterSpacing:"-0.8px" }}>Pathway Analytics</h1>
          </div>
          <div style={{ display:"flex", gap:"8px" }}>
            {["7D","30D","90D"].map(r => (
              <button key={r} onClick={() => setRange(r)} style={{
                padding:"6px 14px", borderRadius:"8px",
                background: r === range ? t.brandGlow : t.surfaceHigh,
                border:"1px solid " + (r === range ? t.brand+"40" : t.border),
                color: r === range ? t.brand : t.textMuted,
                fontFamily:"'DM Mono',monospace", fontSize:"11px", cursor:"pointer",
                transition:"all 0.15s",
              }}>{r}</button>
            ))}
          </div>
        </div>

        {/* Stat cards */}
        <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:"14px", marginBottom:"24px" }}>
          {[
            { label:"Total Calls",     val: scCalls,           color:t.brand  },
            { label:"Avg Completion",  val: totals.completion, color:t.green  },
            { label:"RED Escalations", val: scRed,             color:t.red    },
            { label:"Pathways Active", val: totals.pathways,   color:t.amber  },
          ].map((s,i) => (
            <div key={i} style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"16px", padding:"20px", boxShadow:"0 2px 12px "+t.shadow, animation:"fadeUp 0.4s ease "+(i*60)+"ms both" }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"10px" }}>{s.label.toUpperCase()}</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"38px", fontWeight:900, color:s.color, lineHeight:1, letterSpacing:"-1px" }}>{s.val}</div>
            </div>
          ))}
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 300px", gap:"18px" }}>
          <div style={{ display:"flex", flexDirection:"column", gap:"16px" }}>

            {/* Bar chart */}
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"24px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"20px" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>
                  {range === "7D" ? "DAILY CALL VOLUME" : range === "30D" ? "WEEKLY CALL VOLUME" : "MONTHLY CALL VOLUME"}
                </div>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1px" }}>{RANGE_LABELS[range]}</div>
              </div>
              <div style={{ display:"flex", alignItems:"flex-end", gap:"8px", height:120 }}>
                {chartData.bars.map((d, i) => (
                  <div key={d.label} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:"6px", height:"100%" }}>
                    <div style={{ flex:1, width:"100%", display:"flex", flexDirection:"column", justifyContent:"flex-end", gap:"2px" }}>
                      <div style={{ height:(d.red/maxC*100)+"%", background:t.red+"60", borderRadius:"3px 3px 0 0", minHeight:2 }}/>
                      <div style={{ height:((d.calls-d.red)/maxC*100)+"%", background:t.brand, borderRadius:"3px 3px 0 0", minHeight:4 }}/>
                    </div>
                    <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, whiteSpace:"nowrap" }}>{d.label}</div>
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
              <div style={{ padding:"18px 24px", borderBottom:"1px solid "+t.border, display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1.5px" }}>PATHWAY PERFORMANCE</div>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand }}>{RANGE_LABELS[range]}</div>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"2fr 80px 80px 80px 80px 80px", padding:"10px 24px", borderBottom:"1px solid "+t.border }}>
                {["PATHWAY","CALLS","COMPLT","AVG RISK","FTP%","TREND"].map(h=>(
                  <div key={h} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>{h}</div>
                ))}
              </div>
              {pathwayData.map((p, i) => {
                const sc   = p.avgScore>55?t.red:p.avgScore>40?t.amber:t.green;
                const sel3 = selIdx === i;
                // Sparkline: for 30D use all 30 points; for 90D / 7D use 7 points
                const sparkPoints = range === "30D"
                  ? p.trend.filter((_,j) => j % 4 === 0)  // downsample to 8 pts
                  : p.trend;
                return (
                  <div key={p.name} onClick={() => setSelIdx(i)} style={{ display:"grid", gridTemplateColumns:"2fr 80px 80px 80px 80px 80px", padding:"14px 24px", cursor:"pointer", background:sel3?t.surfaceHigh:"transparent", borderBottom:i<pathwayData.length-1?"1px solid "+t.border:"none", borderLeft:sel3?"2px solid "+t.brand:"2px solid transparent", transition:"all 0.15s" }}>
                    <div>
                      <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px", color:t.textPrimary }}>{p.name}</div>
                      <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, marginTop:"2px" }}>OPCS {p.code}</div>
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:t.textSecond, alignSelf:"center" }}>
                      {p.calls.toLocaleString()}
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:p.completion>=90?t.green:p.completion>=80?t.amber:t.red, alignSelf:"center" }}>
                      {p.completion}%
                    </div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:sc, alignSelf:"center" }}>{p.avgScore}</div>
                    <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"15px", color:p.ftpRate>15?t.red:p.ftpRate>10?t.amber:t.green, alignSelf:"center" }}>{p.ftpRate}%</div>
                    <div style={{ alignSelf:"center" }}>
                      <Sparkline data={sparkPoints} color={p.improvement>=0?t.red:t.green} w={60} h={24}/>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pathway detail sidebar */}
          <div style={{ display:"flex", flexDirection:"column", gap:"14px" }}>
            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"22px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"14px" }}>SELECTED PATHWAY</div>
              <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"18px", color:t.textPrimary, marginBottom:"4px" }}>{selPath.name}</div>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, marginBottom:"20px" }}>OPCS-4 · {selPath.code}</div>
              <div style={{ textAlign:"center", marginBottom:"20px" }}>
                <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"52px", fontWeight:900, color:selPath.avgScore>55?t.red:selPath.avgScore>40?t.amber:t.green, lineHeight:1, letterSpacing:"-2px" }}>
                  {selPath.avgScore}
                </div>
                <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, marginTop:"4px" }}>AVG RISK SCORE</div>
              </div>
              {[
                ["Calls",       selPath.calls.toLocaleString()],
                ["Completion",  selPath.completion+"%"],
                ["FTP Rate",    selPath.ftpRate+"%"],
                ["RED Rate",    selPath.redRate+"%"],
                ["Score Δ",     (selPath.improvement>0?"▲ ":"▼ ")+Math.abs(selPath.improvement)+"pts"],
              ].map(([k,v])=>(
                <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid "+t.border }}>
                  <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{k.toUpperCase()}</span>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textSecond, fontWeight:600 }}>{v}</span>
                </div>
              ))}
            </div>

            <div style={{ background:t.surface, border:"1px solid "+t.border, borderRadius:"18px", padding:"22px", boxShadow:"0 2px 12px "+t.shadow }}>
              <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"14px" }}>
                RISK TREND · {range}
              </div>
              <Sparkline
                data={range === "30D" ? selPath.trend.filter((_,j)=>j%3===0) : selPath.trend}
                color={selPath.improvement>0?t.red:t.green}
                w={240} h={40}
              />
              <div style={{ display:"flex", justifyContent:"space-between", marginTop:"6px" }}>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>
                  {range === "7D" ? "7 DAYS AGO" : range === "30D" ? "30 DAYS AGO" : "90 DAYS AGO"}
                </span>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted }}>TODAY</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

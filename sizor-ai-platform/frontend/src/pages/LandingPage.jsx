import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../theme/ThemeContext";
import { ragCfg } from "../theme/tokens";
import Nav from "../components/Nav";

const pathwayPills = ["Hip Replacement","Knee Replacement","CABG Recovery","COPD Exacerbation","Post C-Section","Ischaemic Stroke","TIA","Bowel Resection","Heart Failure","Pneumonia","AF Management","Spinal Fusion","Pre-eclampsia","Haemorrhagic Stroke","Hernia Repair","Asthma","DVT","PE Management","Diabetic Foot","Renal Transplant","Liver Resection","Bariatric Surgery","Appendectomy"];

export default function LandingPage() {
  const { t } = useTheme();
  const navigate = useNavigate();
  const [hov, setHov] = useState(null);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, transition:"background 0.3s" }}>
      <Nav/>

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
          <button onClick={() => navigate("/dashboard")}
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
              {[{name:"M. Osei",score:87,rag:"RED"},{name:"D. Achebe",score:54,rag:"AMBER"},{name:"P. Nair",score:31,rag:"GREEN"}].map((p,i) => {
                const c = ragCfg(t, p.rag);
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
        <button onClick={() => navigate("/dashboard")}
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

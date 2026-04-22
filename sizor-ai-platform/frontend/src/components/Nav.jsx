import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTheme } from "../theme/ThemeContext";
import { getMe, logout } from "../api/auth";

const NAV_ITEMS = [
  ["Ward Overview",  "/dashboard"],
  ["Patient Queue",  "/patients"],
  ["Alert Inbox",    "/alerts"],
  ["Scheduler",      "/scheduler"],
  ["Analytics",      "/analytics"],
];

export default function Nav() {
  const { t, isDark, toggle } = useTheme();
  const navigate  = useNavigate();
  const location  = useLocation();
  const [time, setTime]         = useState(new Date());
  const [clinician, setClinician] = useState(null);
  const [showMenu, setShowMenu]   = useState(false);

  useEffect(() => {
    const iv = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    getMe().then(setClinician).catch(() => {});
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const initials = clinician?.full_name
    ? clinician.full_name.split(" ").filter(w => /[A-Z]/i.test(w[0])).slice(0,2).map(w=>w[0].toUpperCase()).join("")
    : "?";

  return (
    <nav style={{ height:60, background:t.nav, borderBottom:"1px solid "+t.navBorder, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 32px", position:"sticky", top:0, zIndex:100, transition:"background 0.3s,border-color 0.3s" }}>
      <div style={{ display:"flex", alignItems:"center", gap:"20px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px", cursor:"pointer" }} onClick={() => navigate("/dashboard")}>
          <div style={{ width:30, height:30, borderRadius:"9px", background:"linear-gradient(135deg,#0AAFA8,#00E5C8)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", boxShadow:"0 0 20px #0AAFA840" }}>◈</div>
          <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:900, fontSize:"18px", color:t.textPrimary, letterSpacing:"-0.5px" }}>Sizor</span>
          <span style={{ fontSize:"10px", padding:"2px 7px", borderRadius:"100px", background:t.brandGlow, border:"1px solid "+t.brand+"40", color:t.brand, fontFamily:"'DM Mono',monospace" }}>BETA</span>
        </div>
        <div style={{ width:1, height:20, background:t.border }}/>
        {NAV_ITEMS.map(([label, path]) => {
          const active = location.pathname === path ||
            (path === "/patients" && location.pathname.startsWith("/patients/"));
          return (
            <button key={path} onClick={() => navigate(path)} style={{ background:"none", border:"none", fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:active?t.brand:t.textMuted, cursor:"pointer", padding:"4px 0", borderBottom:active?"1px solid "+t.brand:"1px solid transparent", transition:"color 0.15s" }}>{label}</button>
          );
        })}
      </div>
      <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"6px" }}>
          <span style={{ width:7, height:7, borderRadius:"50%", background:t.green, display:"inline-block", animation:"pulse 2s infinite", boxShadow:"0 0 8px "+t.green }}/>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.green }}>LIVE</span>
        </div>
        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>
          {time.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}
        </div>
        <button onClick={toggle} title={isDark?"Light mode":"Dark mode"}
          onMouseEnter={e=>{e.currentTarget.style.borderColor=t.brand;e.currentTarget.style.color=t.brand;}}
          onMouseLeave={e=>{e.currentTarget.style.borderColor=t.border;e.currentTarget.style.color=t.textSecond;}}
          style={{ width:36, height:36, borderRadius:"10px", background:t.surfaceHigh, border:"1px solid "+t.border, cursor:"pointer", fontSize:"17px", display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.2s", color:t.textSecond }}>
          {isDark?"☀":"☾"}
        </button>
        {/* Clinician avatar + dropdown */}
        <div style={{ position:"relative" }}>
          <button
            onClick={() => setShowMenu(m => !m)}
            style={{ display:"flex", alignItems:"center", gap:"8px", background:showMenu?t.surfaceHigh:"transparent", border:"1px solid "+(showMenu?t.border:"transparent"), borderRadius:"10px", padding:"4px 8px 4px 4px", cursor:"pointer", transition:"all 0.15s" }}
            onMouseEnter={e=>{ e.currentTarget.style.background=t.surfaceHigh; e.currentTarget.style.borderColor=t.border; }}
            onMouseLeave={e=>{ if(!showMenu){ e.currentTarget.style.background="transparent"; e.currentTarget.style.borderColor="transparent"; }}}
          >
            <div style={{ width:30, height:30, borderRadius:"50%", background:"linear-gradient(135deg,"+t.brand+","+t.brandDark+")", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"11px", color:"#fff", flexShrink:0 }}>
              {initials}
            </div>
            {clinician && (
              <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", fontWeight:600, color:t.textPrimary, maxWidth:100, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {clinician.full_name}
              </span>
            )}
            <svg style={{ width:12, height:12, flexShrink:0, transform:showMenu?"rotate(180deg)":"rotate(0deg)", transition:"transform 0.15s" }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>

          {showMenu && (
            <>
              <div style={{ position:"fixed", inset:0, zIndex:99 }} onClick={() => setShowMenu(false)}/>
              <div style={{ position:"absolute", top:"calc(100% + 8px)", right:0, zIndex:100, minWidth:200, background:t.surface, border:"1px solid "+t.border, borderRadius:"14px", boxShadow:"0 12px 40px "+t.shadow, overflow:"hidden" }}>
                {/* Clinician info */}
                <div style={{ padding:"14px 16px", borderBottom:"1px solid "+t.border }}>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", color:t.textPrimary }}>{clinician?.full_name || "Clinician"}</div>
                  <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, marginTop:"2px" }}>{clinician?.role?.toUpperCase().replace("_"," ") || "STAFF"}</div>
                  <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"11px", color:t.textMuted, marginTop:"3px" }}>{clinician?.email}</div>
                </div>
                {/* Logout */}
                <button
                  onClick={handleLogout}
                  style={{ width:"100%", padding:"12px 16px", background:"transparent", border:"none", display:"flex", alignItems:"center", gap:"10px", cursor:"pointer", transition:"background 0.15s" }}
                  onMouseEnter={e=>{ e.currentTarget.style.background=t.redBg; }}
                  onMouseLeave={e=>{ e.currentTarget.style.background="transparent"; }}
                >
                  <svg style={{ width:15, height:15, flexShrink:0 }} fill="none" viewBox="0 0 24 24" stroke={t.red} strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                  </svg>
                  <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", fontWeight:600, color:t.red }}>Sign out</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

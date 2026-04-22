import { useNavigate, useLocation } from "react-router-dom";
import { logout } from "../api/auth";
import { useTheme } from "../theme/ThemeContext";

const NAV_ITEMS = [
  { label: "Ward Overview", path: "/dashboard" },
  { label: "Patient Queue", path: "/patients" },
  { label: "Alert Inbox",   path: "/alerts" },
  { label: "Scheduler",     path: "/scheduler" },
  { label: "Analytics",     path: "/analytics" },
];

export default function Layout({ children }) {
  const { t, isDark, toggle } = useTheme();
  const navigate  = useNavigate();
  const location  = useLocation();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div style={{ minHeight: "100vh", background: t.bg, transition: "background 0.3s" }}>
      {/* ── Top Nav ── */}
      <nav style={{
        height: 60,
        background: t.nav,
        borderBottom: "1px solid " + t.navBorder,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 28px",
        position: "sticky",
        top: 0,
        zIndex: 100,
        transition: "background 0.3s,border-color 0.3s",
      }}>
        {/* Left: logo + links */}
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {/* Logo */}
          <div
            style={{ display: "flex", alignItems: "center", gap: 9, cursor: "pointer" }}
            onClick={() => navigate("/dashboard")}
          >
            <div style={{
              width: 30, height: 30, borderRadius: 9,
              background: "linear-gradient(135deg,#0AAFA8,#00E5C8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 15, boxShadow: "0 0 20px #0AAFA840",
            }}>◈</div>
            <span style={{
              fontFamily: "'Outfit',sans-serif", fontWeight: 900,
              fontSize: 18, color: t.textPrimary, letterSpacing: "-0.5px",
            }}>Sizor</span>
            <span style={{
              fontSize: 10, padding: "2px 7px", borderRadius: 100,
              background: t.brandGlow, border: "1px solid " + t.brand + "40",
              color: t.brand, fontFamily: "'DM Mono',monospace",
            }}>BETA</span>
          </div>

          {/* Divider */}
          <div style={{ width: 1, height: 20, background: t.border }} />

          {/* Nav links */}
          {NAV_ITEMS.map(({ label, path }) => {
            const active = location.pathname === path ||
              (path === "/patients" && location.pathname.startsWith("/patients/"));
            return (
              <button
                key={path}
                onClick={() => navigate(path)}
                style={{
                  background: "none", border: "none",
                  fontFamily: "'Outfit',sans-serif", fontSize: 13,
                  color: active ? t.brand : t.textMuted,
                  cursor: "pointer", padding: "4px 0",
                  borderBottom: active ? "1px solid " + t.brand : "1px solid transparent",
                  transition: "color 0.15s",
                }}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Right: live badge + theme toggle + avatar/logout */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Live indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: t.green, display: "inline-block",
              boxShadow: "0 0 8px " + t.green,
              animation: "pulse 2s infinite",
            }} />
            <span style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, color: t.green }}>LIVE</span>
          </div>

          {/* Dark/light toggle */}
          <button
            onClick={toggle}
            style={{
              width: 36, height: 36, borderRadius: 10,
              background: t.surfaceHigh, border: "1px solid " + t.border,
              cursor: "pointer", fontSize: 17,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s", color: t.textSecond,
            }}
          >
            {isDark ? "☀" : "☾"}
          </button>

          {/* Avatar / logout */}
          <button
            onClick={handleLogout}
            title="Sign out"
            style={{
              width: 32, height: 32, borderRadius: "50%",
              background: "linear-gradient(135deg,#0AAFA8,#076E69)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: "'Outfit',sans-serif", fontWeight: 700,
              fontSize: 12, color: "#fff", border: "none", cursor: "pointer",
            }}
          >
            DR
          </button>
        </div>
      </nav>

      {/* Page content */}
      {children}
    </div>
  );
}

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getPatientSchedule, deleteSchedule } from "../api/patients";
import { useTheme } from "../theme/ThemeContext";
import client from "../api/client";

function formatDt(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    weekday: "short", day: "numeric", month: "short",
    hour: "2-digit", minute: "2-digit",
  });
}

function relativeTime(iso) {
  if (!iso) return "";
  const diff = (new Date(iso) - Date.now()) / 1000 / 60;
  if (diff < 0) return "overdue";
  if (diff < 60) return `in ${Math.round(diff)}m`;
  if (diff < 1440) return `in ${Math.round(diff / 60)}h`;
  return `in ${Math.round(diff / 1440)}d`;
}

const STATUS_STYLE = {
  pending:   { label: "SCHEDULED", color: "#2196F3", bg: "#E3F2FD" },
  completed: { label: "DONE",      color: "#4CAF50", bg: "#E8F5E9" },
  missed:    { label: "MISSED",    color: "#FF9800", bg: "#FFF3E0" },
  cancelled: { label: "CANCELLED", color: "#9E9E9E", bg: "#F5F5F5" },
};

// Local ISO datetime string for <input type="datetime-local">
function toLocalInput(date = new Date()) {
  const pad = n => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export default function PatientScheduleModal({ patientId, patientName, onClose }) {
  const { t }      = useTheme();
  const navigate   = useNavigate();
  const [schedule, setSchedule]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [deleting, setDeleting]   = useState(null);  // schedule_id being deleted

  // Add-call form state
  const [showAdd, setShowAdd]     = useState(false);
  const [addDt, setAddDt]         = useState(toLocalInput());
  const [addType, setAddType]     = useState("outbound");
  const [addModule, setAddModule] = useState("post_discharge");
  const [adding, setAdding]       = useState(false);
  const [addErr, setAddErr]       = useState("");

  const load = () => {
    setLoading(true);
    getPatientSchedule(patientId)
      .then(data => setSchedule(Array.isArray(data) ? data : []))
      .catch(() => setSchedule([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, [patientId]);

  const upcoming = schedule.filter(s => s.status === "pending").sort((a, b) => new Date(a.scheduled_for) - new Date(b.scheduled_for));
  const past     = schedule.filter(s => s.status !== "pending").sort((a, b) => new Date(b.scheduled_for) - new Date(a.scheduled_for));

  async function handleDelete(scheduleId) {
    setDeleting(scheduleId);
    try {
      await deleteSchedule(patientId, scheduleId);
      setSchedule(prev => prev.filter(s => s.schedule_id !== scheduleId));
    } catch (e) {
      alert("Failed to delete schedule entry.");
    } finally {
      setDeleting(null);
    }
  }

  async function handleAdd(e) {
    e.preventDefault();
    setAdding(true);
    setAddErr("");
    try {
      const iso = new Date(addDt).toISOString();
      await client.post(`/patients/${patientId}/schedule`, {
        scheduled_for: iso,
        call_type: addType,
        module: addModule,
      });
      setShowAdd(false);
      setAddDt(toLocalInput());
      load();
    } catch (err) {
      setAddErr(err?.response?.data?.detail || "Failed to add call.");
    } finally {
      setAdding(false);
    }
  }

  function Row({ s }) {
    const st      = STATUS_STYLE[s.status] || STATUS_STYLE.pending;
    const overdue = s.status === "pending" && new Date(s.scheduled_for) < Date.now();
    const isPending = s.status === "pending";
    return (
      <div style={{ display:"grid", gridTemplateColumns:"1.8fr 1fr 0.6fr 0.8fr 32px", gap:"0", padding:"10px 20px", borderBottom:"1px solid "+t.border, transition:"background 0.15s", alignItems:"center" }}
        onMouseEnter={e => e.currentTarget.style.background = t.surfaceHigh}
        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
      >
        <div>
          <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", fontWeight:600, color: overdue ? t.amber : t.textPrimary }}>
            {formatDt(s.scheduled_for)}
          </div>
          {isPending && (
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color: overdue ? t.amber : t.brand, marginTop:"2px" }}>
              {overdue ? "OVERDUE" : relativeTime(s.scheduled_for).toUpperCase()}
            </div>
          )}
        </div>
        <span style={{ fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.textSecond }}>
          {s.module || s.call_type || "—"}
        </span>
        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"11px", color:t.textMuted }}>
          {s.call_number != null ? "Day " + s.call_number : "—"}
        </span>
        <div>
          <span style={{ padding:"2px 8px", borderRadius:"100px", fontFamily:"'DM Mono',monospace", fontSize:"9px", fontWeight:600, color: overdue ? t.amber : st.color, background: overdue ? t.amberBg : st.bg, border:"1px solid "+(overdue ? t.amberBorder : st.color+"40") }}>
            {overdue ? "OVERDUE" : st.label}
          </span>
        </div>
        {/* Delete button — only show for pending calls */}
        <div style={{ display:"flex", justifyContent:"center" }}>
          {isPending && (
            <button
              onClick={() => handleDelete(s.schedule_id)}
              disabled={deleting === s.schedule_id}
              title="Remove scheduled call"
              style={{ width:24, height:24, borderRadius:"6px", border:"1px solid "+t.border, background:"transparent", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center", opacity: deleting === s.schedule_id ? 0.4 : 1 }}>
              {deleting === s.schedule_id
                ? <span style={{ fontSize:"9px", color:t.textMuted }}>…</span>
                : <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              }
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div style={{ position:"fixed", inset:0, zIndex:200, background:"rgba(0,0,0,0.45)", backdropFilter:"blur(4px)", display:"flex", alignItems:"center", justifyContent:"center" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ width:660, maxHeight:"85vh", background:t.surface, border:"1px solid "+t.border, borderRadius:"20px", boxShadow:"0 32px 80px rgba(0,0,0,0.3)", display:"flex", flexDirection:"column", overflow:"hidden" }}>

        {/* Header */}
        <div style={{ padding:"18px 22px", borderBottom:"1px solid "+t.border, background:"linear-gradient(135deg,"+t.brand+"12,"+t.brandDark+"08)", display:"flex", alignItems:"center", justifyContent:"space-between", flexShrink:0 }}>
          <div>
            <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:t.textPrimary }}>Scheduled Calls</div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, marginTop:"2px" }}>{patientName?.toUpperCase()}</div>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
            <button
              onClick={() => setShowAdd(v => !v)}
              style={{ padding:"6px 14px", borderRadius:"8px", background: showAdd ? t.brand : t.brandGlow, border:"1px solid "+t.brand+"40", fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"12px", color: showAdd ? "#fff" : t.brand, cursor:"pointer", display:"flex", alignItems:"center", gap:"5px" }}>
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.8}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>
              {showAdd ? "Cancel" : "Add Call"}
            </button>
            <button
              onClick={() => { navigate("/patients/" + patientId); onClose(); }}
              style={{ padding:"6px 14px", borderRadius:"8px", background:t.surfaceHigh, border:"1px solid "+t.border, fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"12px", color:t.textSecond, cursor:"pointer" }}>
              View Patient
            </button>
            <button onClick={onClose} style={{ width:30, height:30, borderRadius:"8px", border:"1px solid "+t.border, background:t.surfaceHigh, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <svg style={{ width:14, height:14 }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        {/* Add-call form */}
        {showAdd && (
          <form onSubmit={handleAdd} style={{ padding:"16px 22px", borderBottom:"1px solid "+t.border, background:t.bg, flexShrink:0, display:"flex", flexWrap:"wrap", gap:"12px", alignItems:"flex-end" }}>
            <div style={{ display:"flex", flexDirection:"column", gap:"4px" }}>
              <label style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>DATE & TIME</label>
              <input
                type="datetime-local"
                value={addDt}
                onChange={e => setAddDt(e.target.value)}
                required
                style={{ padding:"7px 10px", borderRadius:"8px", border:"1px solid "+t.border, background:t.surface, color:t.textPrimary, fontFamily:"'Outfit',sans-serif", fontSize:"12px", outline:"none" }}
              />
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"4px" }}>
              <label style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>TYPE</label>
              <select value={addType} onChange={e => setAddType(e.target.value)} style={{ padding:"7px 10px", borderRadius:"8px", border:"1px solid "+t.border, background:t.surface, color:t.textPrimary, fontFamily:"'Outfit',sans-serif", fontSize:"12px", outline:"none", cursor:"pointer" }}>
                <option value="outbound">Outbound</option>
                <option value="inbound">Inbound</option>
              </select>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"4px" }}>
              <label style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>MODULE</label>
              <select value={addModule} onChange={e => setAddModule(e.target.value)} style={{ padding:"7px 10px", borderRadius:"8px", border:"1px solid "+t.border, background:t.surface, color:t.textPrimary, fontFamily:"'Outfit',sans-serif", fontSize:"12px", outline:"none", cursor:"pointer" }}>
                <option value="post_discharge">Post Discharge</option>
                <option value="check_in">Check In</option>
                <option value="follow_up">Follow Up</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"4px" }}>
              {addErr && <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:"#ef4444" }}>{addErr}</span>}
              <button
                type="submit"
                disabled={adding}
                style={{ padding:"7px 18px", borderRadius:"8px", background:t.brand, border:"none", fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"12px", color:"#fff", cursor: adding ? "not-allowed" : "pointer", opacity: adding ? 0.6 : 1 }}>
                {adding ? "Scheduling…" : "Schedule Call"}
              </button>
            </div>
          </form>
        )}

        <div style={{ flex:1, overflowY:"auto" }}>
          {loading ? (
            <div style={{ padding:32, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>Loading schedule…</div>
          ) : schedule.length === 0 ? (
            <div style={{ padding:32, fontFamily:"'Outfit',sans-serif", color:t.textMuted, fontSize:13 }}>No scheduled calls found for this patient.</div>
          ) : (
            <>
              {/* Column headers */}
              <div style={{ display:"grid", gridTemplateColumns:"1.8fr 1fr 0.6fr 0.8fr 32px", gap:"0", padding:"10px 20px", background:t.surfaceHigh, borderBottom:"1px solid "+t.border, position:"sticky", top:0 }}>
                {["Date & Time","Module","Day","Status",""].map(h => (
                  <span key={h} style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px" }}>{h.toUpperCase()}</span>
                ))}
              </div>

              {upcoming.length > 0 && (
                <>
                  <div style={{ padding:"8px 20px 4px", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.brand, letterSpacing:"1px", background:t.bg }}>
                    UPCOMING ({upcoming.length})
                  </div>
                  {upcoming.map(s => <Row key={s.schedule_id} s={s}/>)}
                </>
              )}

              {past.length > 0 && (
                <>
                  <div style={{ padding:"12px 20px 4px", fontFamily:"'DM Mono',monospace", fontSize:"9px", color:t.textMuted, letterSpacing:"1px", background:t.bg, borderTop: upcoming.length > 0 ? "1px solid "+t.border : "none" }}>
                    PAST ({past.length})
                  </div>
                  {past.map(s => <Row key={s.schedule_id} s={s}/>)}
                </>
              )}
            </>
          )}
        </div>

        {/* Footer stats */}
        {!loading && schedule.length > 0 && (
          <div style={{ padding:"12px 22px", borderTop:"1px solid "+t.border, background:t.surfaceHigh, flexShrink:0, display:"flex", gap:"20px" }}>
            {[
              ["Upcoming",  upcoming.length, t.brand],
              ["Completed", past.filter(s=>s.status==="completed").length, t.green],
              ["Missed",    past.filter(s=>s.status==="missed").length, t.amber],
            ].map(([label, count, color]) => (
              <div key={label} style={{ display:"flex", alignItems:"center", gap:"6px" }}>
                <span style={{ width:6, height:6, borderRadius:"50%", background:color, display:"inline-block" }}/>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted }}>{label.toUpperCase()}</span>
                <span style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px", color:t.textPrimary }}>{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { getCliniciansList, actionEscalate } from "../api/patients";
import { useTheme } from "../theme/ThemeContext";

const ROLE_LABELS = {
  doctor:       "Doctor",
  consultant:   "Consultant",
  midwife_lead: "Midwifery Lead",
  anaesthetist: "Anaesthetist",
  ward_nurse:   "Ward Nurse",
};

export default function EscalateModal({ patientId, patientName, onClose, onDone }) {
  const { t } = useTheme();
  const [clinicians, setClinicians] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [note, setNote]             = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]           = useState("");

  useEffect(() => {
    getCliniciansList()
      .then(setClinicians)
      .catch(() => setError("Could not load clinicians."))
      .finally(() => setLoading(false));
  }, []);

  async function submit() {
    if (!selected) return;
    setSubmitting(true);
    setError("");
    try {
      await actionEscalate(patientId, {
        to_clinician_id: selected.clinician_id,
        notes: note.trim() || `Escalation for ${patientName}`,
      });
      onDone?.();
      onClose();
    } catch {
      setError("Failed to send escalation. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div style={{
      position:"fixed", inset:0, zIndex:200,
      background:"rgba(0,0,0,0.55)", backdropFilter:"blur(4px)",
      display:"flex", alignItems:"center", justifyContent:"center",
    }} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        width:480, background:t.surface,
        border:"1px solid "+t.border, borderRadius:"20px",
        boxShadow:"0 32px 80px rgba(0,0,0,0.4)",
        overflow:"hidden",
      }}>
        {/* Header */}
        <div style={{
          background:"linear-gradient(135deg,"+t.brand+"18,"+t.brandDark+"10)",
          borderBottom:"1px solid "+t.border,
          padding:"18px 22px",
          display:"flex", alignItems:"center", justifyContent:"space-between",
        }}>
          <div>
            <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"16px", color:t.textPrimary }}>
              Escalate to Clinician
            </div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.brand, marginTop:"2px" }}>
              {patientName?.toUpperCase()}
            </div>
          </div>
          <button onClick={onClose} style={{ width:30, height:30, borderRadius:"8px", border:"1px solid "+t.border, background:t.surfaceHigh, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <svg style={{ width:14, height:14 }} fill="none" viewBox="0 0 24 24" stroke={t.textMuted} strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div style={{ padding:"20px 22px", display:"flex", flexDirection:"column", gap:"16px" }}>
          {/* Clinician picker */}
          <div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"8px" }}>
              SELECT CLINICIAN
            </div>
            {loading ? (
              <div style={{ fontFamily:"'Outfit',sans-serif", fontSize:"13px", color:t.textMuted }}>Loading clinicians…</div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column", gap:"6px", maxHeight:220, overflowY:"auto" }}>
                {clinicians.map(c => {
                  const isSelected = selected?.clinician_id === c.clinician_id;
                  return (
                    <button
                      key={c.clinician_id}
                      onClick={() => setSelected(c)}
                      style={{
                        display:"flex", alignItems:"center", gap:"12px",
                        padding:"10px 12px", borderRadius:"10px",
                        background: isSelected ? t.brandGlow : t.surfaceHigh,
                        border:"1px solid "+(isSelected ? t.brand+"60" : t.border),
                        cursor:"pointer", textAlign:"left",
                        transition:"all 0.15s",
                      }}
                    >
                      {/* Avatar */}
                      <div style={{
                        width:36, height:36, borderRadius:"10px", flexShrink:0,
                        background: isSelected
                          ? "linear-gradient(135deg,"+t.brand+","+t.brandDark+")"
                          : t.surface,
                        border:"1px solid "+(isSelected ? t.brand+"40" : t.border),
                        display:"flex", alignItems:"center", justifyContent:"center",
                        fontFamily:"'Outfit',sans-serif", fontWeight:800, fontSize:"13px",
                        color: isSelected ? "#fff" : t.textPrimary,
                      }}>
                        {c.full_name.split(" ").filter(w => /[A-Z]/.test(w[0])).slice(0,2).map(w=>w[0]).join("")}
                      </div>
                      <div style={{ flex:1 }}>
                        <div style={{ fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"14px", color: isSelected ? t.brand : t.textPrimary }}>
                          {c.full_name}
                        </div>
                        <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"9px", color: isSelected ? t.brand : t.textMuted, marginTop:"1px" }}>
                          {ROLE_LABELS[c.role] || c.role}
                        </div>
                      </div>
                      {isSelected && (
                        <svg style={{ width:16, height:16, flexShrink:0 }} fill="none" viewBox="0 0 24 24" stroke={t.brand} strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Note */}
          <div>
            <div style={{ fontFamily:"'DM Mono',monospace", fontSize:"10px", color:t.textMuted, letterSpacing:"1px", marginBottom:"8px" }}>
              ADD NOTE <span style={{ opacity:0.5 }}>(OPTIONAL)</span>
            </div>
            <textarea
              rows={3}
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="Describe the reason for escalation, any urgent concerns, or specific actions needed…"
              style={{
                width:"100%", resize:"vertical",
                fontFamily:"'Outfit',sans-serif", fontSize:"13px", lineHeight:1.6,
                color:t.textPrimary, background:t.surfaceHigh,
                border:"1px solid "+t.border, borderRadius:"10px",
                padding:"10px 12px", outline:"none",
                boxSizing:"border-box",
                transition:"border-color 0.15s",
              }}
              onFocus={e => e.target.style.borderColor = t.brand+"80"}
              onBlur={e => e.target.style.borderColor = t.border}
            />
          </div>

          {error && (
            <div style={{ padding:"9px 12px", borderRadius:"8px", background:t.redBg, border:"1px solid "+t.redBorder, fontFamily:"'Outfit',sans-serif", fontSize:"12px", color:t.red }}>
              {error}
            </div>
          )}

          {/* Actions */}
          <div style={{ display:"flex", gap:"10px" }}>
            <button
              onClick={onClose}
              style={{
                flex:1, padding:"12px", borderRadius:"10px",
                background:t.surfaceHigh, border:"1px solid "+t.border,
                fontFamily:"'Outfit',sans-serif", fontWeight:600, fontSize:"13px",
                color:t.textSecond, cursor:"pointer",
              }}>
              Cancel
            </button>
            <button
              onClick={submit}
              disabled={!selected || submitting}
              style={{
                flex:2, padding:"12px", borderRadius:"10px", border:"none",
                background: selected && !submitting
                  ? "linear-gradient(135deg,"+t.brand+","+t.brandDark+")"
                  : t.surfaceHigh,
                fontFamily:"'Outfit',sans-serif", fontWeight:700, fontSize:"13px",
                color: selected && !submitting ? "#fff" : t.textMuted,
                cursor: selected && !submitting ? "pointer" : "not-allowed",
                opacity: selected && !submitting ? 1 : 0.6,
                boxShadow: selected && !submitting ? "0 4px 16px "+t.brand+"40" : "none",
                transition:"all 0.15s",
              }}>
              {submitting ? "Sending…" : "▲ Send Escalation"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

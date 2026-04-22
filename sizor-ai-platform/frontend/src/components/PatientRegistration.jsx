import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import RecoveryDashboard from "./RecoveryDashboard";
import { OPCS_TO_NICE_MAP, AUTO_FLAG_RULES, MANUAL_FLAG_DEFS } from "../data/pathwayMap";

// PATHWAY_CATEGORIES — used to group search results
const PATHWAY_CATEGORIES = {
  Surgical:     ["W37","W38","W40","W43","K40_CABG","H04","H01","J18_CHOLE","Q07","M61","R17","R18"],
  Medical:      ["K60","K40","K57","S01","G45","J44","J18_PNEUMONIA","A41","I26","E11_DKA"],
  "Mental Health": ["Z03_MH","X60","F20"],
};

// ── Validation helpers ────────────────────────────────────────────────────
function validateNHSNumber(val) {
  const digits = val.replace(/\D/g, "");
  if (!digits) return null;
  if (digits.length !== 10) return "NHS number must be exactly 10 digits";
  return null;
}

function validateUKMobile(val) {
  if (!val || !val.trim()) return "Mobile number is required";
  const cleaned = val.replace(/\s/g, "");
  if (!/^(07\d{9}|(\+44|0044)7\d{9})$/.test(cleaned))
    return "Enter a valid UK mobile number (e.g. 07700 900123)";
  return null;
}

const INPUT_CLS =
  "w-full px-3 py-2 text-sm rounded-lg border border-gray-200 bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-nhs-blue focus:border-nhs-blue";
const LABEL_CLS = "block text-xs font-medium text-gray-500 mb-1";

export default function PatientRegistration({ onSuccess, onCancel }) {
  const navigate = useNavigate();

  // ── Form state ───────────────────────────────────────────────────────────
  const [form, setForm] = useState({
    nhs_number: "",
    name: "",
    phone_number: "",
    date_of_birth: "",
    postcode: "",
    discharge_date: "",
    preferred_call_time: "",
    ward: "",
    consultant: "",
    schedule_date: "",
    schedule_time: "",
  });

  // ── Procedure search state ───────────────────────────────────────────────
  const [query, setQuery]       = useState("");
  const [results, setResults]   = useState([]);
  const [selected, setSelected] = useState(null);   // { code, ...pathway }
  const [open, setOpen]         = useState(false);
  const [focusedIdx, setFocusedIdx] = useState(-1);
  const dropdownRef = useRef(null);
  const inputRef    = useRef(null);

  // ── Risk flags state ─────────────────────────────────────────────────────
  const [autoFlags, setAutoFlags]     = useState({});  // tier 1 — locked
  const [manualFlags, setManualFlags] = useState({});  // tier 3 — checkboxes

  // ── Editable pathway customisation ───────────────────────────────────────
  const [customDomains, setCustomDomains]       = useState([]);
  const [customRedFlags, setCustomRedFlags]     = useState([]);
  const [newDomainInput, setNewDomainInput]     = useState("");
  const [newRedFlagInput, setNewRedFlagInput]   = useState("");

  // ── UI state ─────────────────────────────────────────────────────────────
  const [showPreview, setShowPreview] = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [error, setError]             = useState(null);
  const [success, setSuccess]         = useState(null);
  const [nhsError, setNhsError]       = useState(null);
  const [phoneError, setPhoneError]   = useState(null);

  // ── Debug: verify data is loading ───────────────────────────────────────
  useEffect(() => {
    console.log("[Sizor] pathwayMap loaded:", Object.keys(OPCS_TO_NICE_MAP).length, "pathways");
    console.log("[Sizor] sample entry:", OPCS_TO_NICE_MAP["W40"]);
  }, []);

  // ── Live procedure search — filter OPCS_TO_NICE_MAP on every keystroke ───
  useEffect(() => {
    if (!query || query.length < 1) {
      setResults([]);
      setOpen(false);
      setFocusedIdx(-1);
      return;
    }
    const q = query.toLowerCase().trim();

    // Levenshtein edit distance — used for fuzzy per-word matching
    function editDist(a, b) {
      const m = a.length, n = b.length;
      const dp = Array.from({ length: m + 1 }, (_, i) =>
        Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
      );
      for (let i = 1; i <= m; i++)
        for (let j = 1; j <= n; j++)
          dp[i][j] = a[i - 1] === b[j - 1]
            ? dp[i - 1][j - 1]
            : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
      return dp[m][n];
    }

    function pathwayMatches(code, label) {
      const lbl = label.toLowerCase();
      const cod = code.toLowerCase();
      // Fast path: direct substring match
      if (lbl.includes(q) || cod.includes(q)) return true;
      // Word-level fuzzy: every query word must match a label word within edit distance 2
      const qWords = q.split(/\s+/).filter(Boolean);
      const lblWords = lbl.split(/\s+/);
      return qWords.every(qw =>
        lbl.includes(qw) ||
        cod.includes(qw) ||
        (qw.length >= 4 && lblWords.some(lw => lw.length >= 4 && editDist(qw, lw) <= 2))
      );
    }

    const matches = Object.entries(OPCS_TO_NICE_MAP).filter(
      ([code, p]) => pathwayMatches(code, p.label)
    );
    setResults(matches);
    setOpen(matches.length > 0);
    setFocusedIdx(-1);
  }, [query]);

  // ── Close dropdown on outside click ─────────────────────────────────────
  useEffect(() => {
    function onDown(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target))
        setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  // ── Group results by category ────────────────────────────────────────────
  const groupedResults = Object.entries(PATHWAY_CATEGORIES)
    .map(([cat, codes]) => [cat, results.filter(([c]) => codes.includes(c))])
    .filter(([, items]) => items.length > 0);

  // ── Auto-detect risk flags from selected OPCS code ───────────────────────
  function autoDetectRiskFlags(opcsCode) {
    const pathway = OPCS_TO_NICE_MAP[opcsCode];
    if (!pathway) return;
    const detected = {};
    (pathway.auto_risk_flags || []).forEach((flagKey) => {
      if (AUTO_FLAG_RULES[flagKey]) {
        detected[flagKey] = { checked: true, tier: 1, ...AUTO_FLAG_RULES[flagKey] };
      }
    });
    console.log("[Sizor] Auto-detected flags for", opcsCode, ":", detected);
    setAutoFlags(detected);
  }

  // ── Select a pathway from the dropdown ───────────────────────────────────
  function handleSelect(code, pathway) {
    setSelected({ code, ...pathway });
    setQuery(pathway.label);
    setOpen(false);
    setFocusedIdx(-1);
    autoDetectRiskFlags(code);
    setCustomDomains([...(pathway.monitoring_domains || [])]);
    setCustomRedFlags([...(pathway.red_flags || [])]);
  }

  // ── Clear procedure selection ─────────────────────────────────────────────
  function clearSelection() {
    setSelected(null);
    setAutoFlags({});
    setCustomDomains([]);
    setCustomRedFlags([]);
    // intentionally keep query so the user can keep typing
  }

  // ── Domain chip helpers ───────────────────────────────────────────────────
  function removeDomain(d) { setCustomDomains((prev) => prev.filter((x) => x !== d)); }
  function addDomain() {
    const val = newDomainInput.trim().toLowerCase().replace(/\s+/g, "_");
    if (val && !customDomains.includes(val)) setCustomDomains((prev) => [...prev, val]);
    setNewDomainInput("");
  }

  // ── Red flag chip helpers ─────────────────────────────────────────────────
  function removeRedFlag(f) { setCustomRedFlags((prev) => prev.filter((x) => x !== f)); }
  function addRedFlag() {
    const val = newRedFlagInput.trim().toLowerCase().replace(/\s+/g, "_");
    if (val && !customRedFlags.includes(val)) setCustomRedFlags((prev) => [...prev, val]);
    setNewRedFlagInput("");
  }

  // ── Keyboard navigation in dropdown ─────────────────────────────────────
  function handleKeyDown(e) {
    if (!open) return;
    const flat = results; // already flat array of [code, pathway]
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIdx((i) => Math.min(i + 1, flat.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && focusedIdx >= 0) {
      e.preventDefault();
      const [code, pathway] = flat[focusedIdx];
      handleSelect(code, pathway);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  // ── Manual flag toggle (tier 3) ──────────────────────────────────────────
  function toggleManualFlag(key) {
    setManualFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  // ── Field change ─────────────────────────────────────────────────────────
  function handleFieldChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (name === "nhs_number") setNhsError(validateNHSNumber(value));
    if (name === "phone_number") setPhoneError(null);
  }

  // ── Validation ───────────────────────────────────────────────────────────
  function validateForm() {
    const nhsErr = validateNHSNumber(form.nhs_number);
    if (nhsErr) { setNhsError(nhsErr); return false; }
    if (form.nhs_number.replace(/\D/g, "").length !== 10) {
      setNhsError("NHS number must be exactly 10 digits"); return false;
    }
    const phoneErr = validateUKMobile(form.phone_number);
    if (phoneErr) { setPhoneError(phoneErr); return false; }
    if (!selected) { setError("Please select a procedure / pathway."); return false; }
    if (!form.name.trim()) { setError("Full name is required."); return false; }
    if (!form.discharge_date) { setError("Discharge date is required."); return false; }
    const today = new Date(); today.setHours(0, 0, 0, 0);
    if (new Date(form.discharge_date) > today) {
      setError("Discharge date cannot be in the future."); return false;
    }
    return true;
  }

  // ── Submit ───────────────────────────────────────────────────────────────
  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (!validateForm()) return;

    const allFlags = [
      ...Object.keys(autoFlags).filter((k) => autoFlags[k].checked),
      ...Object.keys(manualFlags).filter((k) => manualFlags[k]),
    ];

    setSubmitting(true);
    try {
      const res = await client.post("/patients/pathway-register", {
        nhs_number: form.nhs_number.replace(/\D/g, ""),
        name: form.name,
        phone_number: form.phone_number,
        date_of_birth: form.date_of_birth || null,
        postcode: form.postcode.replace(/\s/g, "").toUpperCase() || null,
        discharge_date: form.discharge_date,
        opcs_code: selected.code,
        domains: customDomains,
        clinical_red_flags: customRedFlags,
        risk_flags: allFlags,
        preferred_call_time: form.preferred_call_time || null,
        ward: form.ward,
        consultant: form.consultant,
      });
      const created = res.data;

      // Schedule the first appointment if date + time are set
      if (form.schedule_date && form.schedule_time) {
        const scheduledFor = new Date(`${form.schedule_date}T${form.schedule_time}:00`).toISOString();
        await client.post(`/patients/${created.patient_id}/schedule`, {
          scheduled_for: scheduledFor,
          call_type: "outbound",
          module: selected.code,
          protocol_name: selected.label,
        });
      }

      if (onSuccess) onSuccess(created);
      navigate(`/patients/${created.patient_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const nhsDigits       = form.nhs_number.replace(/\D/g, "");
  const canSubmit       = !submitting && selected && nhsDigits.length === 10 && form.name.trim() && form.discharge_date;
  const autoDetectedKeys = new Set(Object.keys(autoFlags));

  // ── Registration form ────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900">Register New Patient</h2>
        <p className="text-sm text-gray-500 mt-1">NHS pathway-linked post-discharge monitoring</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6"
        onKeyDown={(e) => { if (e.key === "Enter" && e.target.type !== "submit") e.preventDefault(); }}>

        {/* ── Patient details ─────────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Patient Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={LABEL_CLS}>NHS Number <span className="text-gray-400 font-normal">(10 digits)</span></label>
              <input type="text" name="nhs_number" value={form.nhs_number} onChange={handleFieldChange}
                placeholder="e.g. 943 476 5919" maxLength={12} required
                className={`${INPUT_CLS} ${nhsError ? "!border-red-400 focus:!ring-red-400" : ""}`} />
              {nhsError && <p className="text-xs text-red-600 mt-1">{nhsError}</p>}
            </div>
            <div>
              <label className={LABEL_CLS}>Full Name</label>
              <input type="text" name="name" value={form.name} onChange={handleFieldChange}
                placeholder="Full name" required className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}>Mobile Number</label>
              <input type="tel" name="phone_number" value={form.phone_number} onChange={handleFieldChange}
                placeholder="e.g. 07700 900123" required
                className={`${INPUT_CLS} ${phoneError ? "!border-red-400 focus:!ring-red-400" : ""}`} />
              {phoneError && <p className="text-xs text-red-600 mt-1">{phoneError}</p>}
            </div>
            <div>
              <label className={LABEL_CLS}>Date of Birth</label>
              <input type="date" name="date_of_birth" value={form.date_of_birth} onChange={handleFieldChange} className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}>
                Postcode{" "}
                <span className="text-gray-400 font-normal">(used for identity verification on calls)</span>
              </label>
              <input
                type="text"
                name="postcode"
                value={form.postcode}
                onChange={(e) => setForm((f) => ({ ...f, postcode: e.target.value.toUpperCase() }))}
                placeholder="e.g. SW1A 2AA"
                maxLength={8}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label className={LABEL_CLS}>Discharge Date</label>
              <input type="date" name="discharge_date" value={form.discharge_date} onChange={handleFieldChange}
                max={new Date().toISOString().split("T")[0]} required className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}>
                Preferred call time{" "}
                <span className="text-gray-400 font-normal">(when to call this patient)</span>
              </label>
              <input type="time" name="preferred_call_time" value={form.preferred_call_time}
                onChange={handleFieldChange} className={INPUT_CLS} />
            </div>

            <div>
              <label className={LABEL_CLS}>Ward</label>
              <input type="text" name="ward" value={form.ward} onChange={handleFieldChange}
                placeholder="e.g. Orthopaedic Ward 5" className={INPUT_CLS} />
            </div>
            <div className="sm:col-span-2">
              <label className={LABEL_CLS}>Consultant</label>
              <input type="text" name="consultant" value={form.consultant} onChange={handleFieldChange}
                placeholder="e.g. Mr. Smith" className={INPUT_CLS} />
            </div>
          </div>
        </section>

        {/* ── Procedure / Pathway ─────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Procedure / Pathway</h3>

          <div style={{ position: "relative" }} ref={dropdownRef}>
            <label className={LABEL_CLS}>Search procedure or OPCS code</label>
            <div style={{ position: "relative" }}>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  if (selected) clearSelection();
                }}
                onFocus={() => results.length > 0 && setOpen(true)}
                onKeyDown={(e) => { if (e.key === "Enter") e.preventDefault(); handleKeyDown(e); }}
                placeholder="e.g. hip replacement, W37, heart failure…"
                className={INPUT_CLS}
                autoComplete="off"
              />
              {query && !selected && (
                <button type="button" onClick={() => { clearSelection(); setOpen(false); }}
                  style={{ position:"absolute", right:8, top:"50%", transform:"translateY(-50%)",
                    background:"none", border:"none", cursor:"pointer", color:"#9ca3af", fontSize:16 }}>
                  ×
                </button>
              )}
            </div>

            {/* Live dropdown */}
            {open && (
              <div style={{
                position: "absolute", top: "100%", left: 0, right: 0,
                background: "#ffffff",
                border: "0.5px solid #d1d5db",
                borderRadius: 8, zIndex: 999, maxHeight: 280,
                overflowY: "auto", boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
                marginTop: 2,
              }}>
                {groupedResults.map(([category, items]) => (
                  <div key={category}>
                    <div style={{
                      padding: "6px 12px", fontSize: 11, fontWeight: 600,
                      color: "#6b7280", background: "#f9fafb",
                      textTransform: "uppercase", letterSpacing: "0.04em",
                      borderBottom: "0.5px solid #f3f4f6",
                    }}>
                      {category}
                    </div>
                    {items.map(([code, pathway], idx) => {
                      const flatIdx = results.findIndex(([c]) => c === code);
                      const isFocused = flatIdx === focusedIdx;
                      return (
                        <div
                          key={code}
                          onClick={() => handleSelect(code, pathway)}
                          style={{
                            padding: "10px 12px", cursor: "pointer",
                            borderBottom: "0.5px solid #f3f4f6",
                            display: "flex", justifyContent: "space-between", alignItems: "center",
                            background: isFocused ? "#f0f7ff" : "transparent",
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = "#f0f7ff"; setFocusedIdx(flatIdx); }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = isFocused ? "#f0f7ff" : "transparent"; }}
                        >
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 500, color: "#111827" }}>
                              {pathway.label}
                            </div>
                            <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
                              {pathway.nice_ids.slice(0, 2).join(" · ")}
                            </div>
                          </div>
                          <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 12 }}>
                            <span style={{
                              fontSize: 11, fontWeight: 600, padding: "2px 8px",
                              background: "#E6F1FB", color: "#0C447C",
                              borderRadius: 4, display: "block", marginBottom: 3,
                            }}>
                              {code}
                            </span>
                            <span style={{ fontSize: 11, color: "#6b7280" }}>
                              {pathway.monitoring_window_days}d · {pathway.monitoring_domains.length} domains
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Selected pathway preview card */}
          {selected && (
            <div style={{
              marginTop: 8, padding: "14px 16px",
              background: "#f9fafb",
              border: "0.5px solid #d1d5db",
              borderRadius: 8,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <span style={{ fontSize: 14, fontWeight: 500, color: "#111827" }}>
                    {selected.label}
                  </span>
                  <span style={{
                    marginLeft: 8, fontSize: 11, fontWeight: 600,
                    padding: "2px 8px", background: "#E6F1FB",
                    color: "#0C447C", borderRadius: 4,
                  }}>
                    {selected.code}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={clearSelection}
                  style={{ fontSize: 12, color: "#6b7280", background: "none", border: "none", cursor: "pointer" }}
                >
                  Change
                </button>
              </div>

              {/* NICE IDs */}
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 }}>
                {selected.nice_ids.map((id) => (
                  <span key={id} style={{
                    fontSize: 11, padding: "2px 8px",
                    background: "#EAF3DE", color: "#27500A",
                    borderRadius: 4, fontWeight: 500,
                  }}>
                    {id}
                  </span>
                ))}
              </div>

              {/* Stats row */}
              <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#6b7280", marginBottom: 10 }}>
                <span>{selected.monitoring_window_days} day monitoring</span>
                <span>{selected.call_days?.length || 6} scheduled calls</span>
                <span>{customDomains.length} domains</span>
              </div>

              {/* Editable domain chips */}
              <div style={{ marginBottom: 4 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#6b7280", marginBottom: 6 }}>
                  Domains to monitor <span style={{ fontWeight: 400, color: "#9ca3af" }}>— AI will ask about each on every call</span>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 6 }}>
                  {customDomains.map((d) => (
                    <span key={d} style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      fontSize: 11, padding: "3px 8px",
                      background: "#EFF6FF", border: "0.5px solid #93C5FD",
                      borderRadius: 4, color: "#1D4ED8",
                    }}>
                      {d.replace(/_/g, " ")}
                      <button type="button" onClick={() => removeDomain(d)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#93C5FD", fontSize: 13, lineHeight: 1, padding: 0 }}>
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <input
                    type="text"
                    value={newDomainInput}
                    onChange={(e) => setNewDomainInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addDomain(); } }}
                    placeholder="Add domain…"
                    style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, border: "0.5px solid #d1d5db", outline: "none", width: 160 }}
                  />
                  <button type="button" onClick={addDomain}
                    style={{ fontSize: 11, padding: "3px 10px", borderRadius: 4, background: "#E6F1FB", color: "#005EB8", border: "none", cursor: "pointer", fontWeight: 500 }}>
                    + Add
                  </button>
                </div>
              </div>

              {/* Benchmark preview toggle */}
              <button
                type="button"
                onClick={() => setShowPreview((v) => !v)}
                style={{ marginTop: 12, fontSize: 12, color: "#005EB8", background: "none", border: "none", cursor: "pointer", padding: 0 }}
              >
                {showPreview ? "Hide" : "Preview"} benchmarks
              </button>
            </div>
          )}

          {selected && showPreview && (
            <div className="mt-4">
              <RecoveryDashboard opcsCode={selected.code} title={`${selected.label} — Recovery Benchmarks`} />
            </div>
          )}
        </section>

        {/* ── Risk flags ──────────────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Risk Flags</h3>
          <p className="text-xs text-gray-500 mb-4">
            Configure what the AI monitors and escalates on every call.
          </p>

          {/* Clinical red flags — editable chips */}
          {selected && (
            <div className="mb-5 pb-5 border-b border-gray-100">
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#DC2626", marginBottom: 6 }}>
                Clinical Red Flags <span style={{ fontWeight: 400, color: "#9ca3af" }}>— AI escalates immediately if detected</span>
              </div>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 6 }}>
                {customRedFlags.map((f) => (
                  <span key={f} style={{
                    display: "inline-flex", alignItems: "center", gap: 4,
                    fontSize: 11, padding: "3px 8px",
                    background: "#FEF2F2", border: "0.5px solid #FCA5A5",
                    borderRadius: 4, color: "#DC2626",
                  }}>
                    {f.replace(/_/g, " ")}
                    <button type="button" onClick={() => removeRedFlag(f)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#FCA5A5", fontSize: 13, lineHeight: 1, padding: 0 }}>
                      ×
                    </button>
                  </span>
                ))}
                {customRedFlags.length === 0 && (
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>No red flags set — add below</span>
                )}
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <input
                  type="text"
                  value={newRedFlagInput}
                  onChange={(e) => setNewRedFlagInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addRedFlag(); } }}
                  placeholder="Add red flag…"
                  style={{ fontSize: 11, padding: "3px 8px", borderRadius: 4, border: "0.5px solid #d1d5db", outline: "none", width: 180 }}
                />
                <button type="button" onClick={addRedFlag}
                  style={{ fontSize: 11, padding: "3px 10px", borderRadius: 4, background: "#FEF2F2", color: "#DC2626", border: "0.5px solid #FCA5A5", cursor: "pointer", fontWeight: 500 }}>
                  + Add
                </button>
              </div>
            </div>
          )}

          {/* Tier 1 — auto-detected patient risk factors (locked) */}
          {Object.keys(autoFlags).length > 0 && (
            <div className="mb-4">
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#005EB8", marginBottom: 8 }}>
                Auto-detected patient risk factors
              </div>
              <div className="space-y-2">
                {Object.entries(autoFlags).map(([key, flag]) => (
                  <div key={key} style={{
                    background: "#E6F1FB", border: "0.5px solid #85B7EB",
                    borderRadius: 8, padding: "10px 14px",
                    display: "flex", alignItems: "center", gap: 10,
                  }}>
                    <span style={{ color: "#0C447C", fontSize: 16, flexShrink: 0 }}>🔒</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: "#0C447C" }}>{flag.label}</div>
                      <div style={{ fontSize: 11, color: "#185FA5", marginTop: 2 }}>{flag.reason}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tier 3 — manual patient risk factors */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#9ca3af", marginBottom: 8 }}>
              Additional patient risk factors
            </div>
            <div className="space-y-2">
              {MANUAL_FLAG_DEFS
                .filter((f) => !autoDetectedKeys.has(f.key))
                .map(({ key, label, desc }) => {
                  const checked = !!manualFlags[key];
                  return (
                    <label key={key} className={`flex items-start gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                      checked ? "border-nhs-blue/40 bg-nhs-blue/5" : "border-gray-200 hover:bg-gray-50"
                    }`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleManualFlag(key)}
                        className="mt-0.5 rounded accent-nhs-blue"
                      />
                      <div>
                        <div className="text-sm text-gray-900">{label}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{desc}</div>
                      </div>
                    </label>
                  );
                })}
            </div>
          </div>
        </section>

        {/* ── Schedule First Call ─────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Schedule First Call</h3>
          <p className="text-xs text-gray-500 mb-4">
            Optionally book the first appointment now. Leave blank to schedule later.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={LABEL_CLS}>Date</label>
              <input
                type="date"
                name="schedule_date"
                value={form.schedule_date}
                onChange={handleFieldChange}
                min={new Date().toISOString().split("T")[0]}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label className={LABEL_CLS}>Time</label>
              <input
                type="time"
                name="schedule_time"
                value={form.schedule_time}
                onChange={handleFieldChange}
                disabled={!form.schedule_date}
                className={`${INPUT_CLS} disabled:opacity-50 disabled:cursor-not-allowed`}
              />
            </div>
          </div>
          {form.schedule_date && form.schedule_time && (
            <p className="mt-3 text-xs text-green-700 font-medium">
              First call will be scheduled for {new Date(`${form.schedule_date}T${form.schedule_time}`).toLocaleString("en-GB", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}
            </p>
          )}
        </section>

        {/* ── Pathway summary ─────────────────────────────────────────────── */}
        {selected && form.discharge_date && (
          <section className="rounded-xl border border-green-200 bg-green-50 p-4">
            <h3 className="text-sm font-semibold text-green-900 mb-2">Pathway Summary</h3>
            <div className="text-xs text-green-800 space-y-1">
              <p><span className="font-medium">Pathway:</span> {selected.label} ({selected.code})</p>
              <p><span className="font-medium">NICE guidelines:</span> {selected.nice_ids.join(", ")}</p>
              <p><span className="font-medium">Monitoring window:</span> {selected.monitoring_window_days} days from {form.discharge_date}</p>
              <p><span className="font-medium">Calls scheduled:</span> {selected.call_days?.length || 6} calls across monitoring period</p>
              <p><span className="font-medium">Monitoring domains:</span> {selected.monitoring_domains.map((d) => d.replace(/_/g, " ")).join(", ")}</p>
            </div>
          </section>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          {onCancel && (
            <button type="button" onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-500 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors">
              Cancel
            </button>
          )}
          <button type="submit" disabled={!canSubmit}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-nhs-blue text-white hover:bg-nhs-blue/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            {submitting ? "Registering…" : "Register patient and generate playbook"}
          </button>
        </div>
      </form>
    </div>
  );
}

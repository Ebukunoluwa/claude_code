import { useEffect, useState } from "react";
import client from "../api/client";

// Score constants
const SCORE_COLORS = {
  0: "#22c55e",
  1: "#86efac",
  2: "#fbbf24",
  3: "#f97316",
  4: "#ef4444",
};

const SCORE_BG = {
  0: "bg-green-50 border-green-200 text-green-800",
  1: "bg-green-50 border-green-200 text-green-800",
  2: "bg-amber-50 border-amber-200 text-amber-800",
  3: "bg-orange-50 border-orange-300 text-orange-900",
  4: "bg-red-50 border-red-300 text-red-900",
};

const SCORE_LABELS = {
  0: "Resolved",
  1: "Expected",
  2: "Monitor",
  3: "Expedite — same-day review",
  4: "Escalate — call 999",
};

function ScoreButton({ value, selected, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`w-10 h-10 rounded-lg border-2 font-bold text-sm transition-all ${
        selected
          ? "scale-110 shadow-md border-current"
          : "opacity-60 hover:opacity-90 border-transparent"
      } ${SCORE_BG[value]}`}
      style={selected ? { borderColor: SCORE_COLORS[value] } : {}}
      title={`${value} — ${SCORE_LABELS[value]}`}
    >
      {value}
    </button>
  );
}

function DomainCard({ domain, script, score, onScore }) {
  const [expanded, setExpanded] = useState(true);
  const escalationText =
    score === 4
      ? script?.escalation_script_4
      : score === 3
      ? script?.escalation_script_3
      : null;

  return (
    <div
      className={`rounded-xl border-2 transition-colors ${
        score >= 3 ? "border-red-300 bg-red-50" : score === 2 ? "border-amber-200 bg-amber-50" : "border-[var(--color-border,#e5e7eb)] bg-[var(--color-surface,#fff)]"
      }`}
    >
      {/* Domain header */}
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: SCORE_COLORS[score ?? 1] }}
          />
          <span className="font-semibold text-sm capitalize text-[var(--color-text,#111827)]">
            {domain.replace(/_/g, " ")}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {score !== undefined && score !== null && (
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded border ${SCORE_BG[score]}`}
            >
              {score} — {SCORE_LABELS[score]}
            </span>
          )}
          <span className="text-gray-400 text-xs">{expanded ? "▲" : "▼"}</span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-[var(--color-border,#e5e7eb)]">
          {/* Questions */}
          {script && (
            <div className="mt-3 space-y-2">
              {script.opening_question && (
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text-secondary,#6b7280)] uppercase tracking-wide">
                    Opening
                  </span>
                  <p className="mt-0.5 text-sm text-[var(--color-text,#111827)] italic">
                    "{script.opening_question}"
                  </p>
                </div>
              )}
              {script.clinical_question && (
                <div>
                  <span className="text-xs font-semibold text-[var(--color-text-secondary,#6b7280)] uppercase tracking-wide">
                    Clinical question
                  </span>
                  <p className="mt-0.5 text-sm text-[var(--color-text,#111827)] italic">
                    "{script.clinical_question}"
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Score guide */}
          {script?.score_guide && (
            <div>
              <span className="text-xs font-semibold text-[var(--color-text-secondary,#6b7280)] uppercase tracking-wide">
                Scoring guide
              </span>
              <div className="mt-1.5 space-y-1">
                {Object.entries(script.score_guide).map(([s, desc]) => (
                  <div
                    key={s}
                    className={`flex items-start gap-2 px-2.5 py-1.5 rounded-lg border text-xs ${SCORE_BG[Number(s)]}`}
                  >
                    <span className="font-bold w-4 shrink-0">{s}</span>
                    <span>{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Score selection */}
          <div>
            <span className="text-xs font-semibold text-[var(--color-text-secondary,#6b7280)] uppercase tracking-wide block mb-2">
              Record score
            </span>
            <div className="flex gap-2">
              {[0, 1, 2, 3, 4].map((v) => (
                <ScoreButton
                  key={v}
                  value={v}
                  selected={score === v}
                  onClick={onScore}
                />
              ))}
            </div>
          </div>

          {/* Escalation script */}
          {escalationText && (
            <div
              className={`p-3 rounded-lg border-2 ${
                score === 4 ? "border-red-400 bg-red-100" : "border-orange-400 bg-orange-100"
              }`}
            >
              <p
                className={`text-xs font-bold uppercase tracking-wide mb-1 ${
                  score === 4 ? "text-red-800" : "text-orange-800"
                }`}
              >
                {score === 4 ? "EMERGENCY — Call 999" : "Same-day escalation required"}
              </p>
              <p className={`text-sm italic ${score === 4 ? "text-red-900" : "text-orange-900"}`}>
                "{escalationText}"
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * CallPlaybook
 *
 * Props:
 *   patientId  {string}  Patient UUID
 *   callDay    {number}  Day post-discharge for this call
 *   opcsCode   {string}  OPCS code for the pathway
 *   callId     {string}  Optional existing call ID for submitting scores
 *   onScoresSubmitted  {function}  Callback on successful score submission
 */
export default function CallPlaybook({ patientId, callDay, opcsCode, callId, onScoresSubmitted }) {
  const [playbook, setPlaybook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scores, setScores] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!patientId || !callDay) return;
    setLoading(true);
    setError(null);
    client
      .get(`/patients/${patientId}/playbook/${callDay}`)
      .then((r) => setPlaybook(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load playbook"))
      .finally(() => setLoading(false));
  }, [patientId, callDay]);

  const dayPlaybook = playbook?.[callDay] || playbook || {};
  const domains = Object.keys(dayPlaybook);

  async function submitScores() {
    if (!callId) {
      setSubmitError("No call ID provided — cannot submit scores.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await client.post(`/calls/${callId}/scores`, {
        opcs_code: opcsCode,
        day_post_discharge: callDay,
        domain_scores: scores,
      });
      setSubmitted(true);
      if (onScoresSubmitted) onScoresSubmitted(scores);
    } catch (e) {
      setSubmitError(e.response?.data?.detail || "Failed to submit scores.");
    } finally {
      setSubmitting(false);
    }
  }

  const allScored = domains.length > 0 && domains.every((d) => scores[d] !== undefined);
  const hasEscalation = Object.values(scores).some((s) => s >= 3);

  if (!patientId || !callDay) {
    return (
      <div className="p-4 text-sm text-[var(--color-text-secondary,#6b7280)]">
        Select a patient and call day to load the playbook.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text,#111827)]">
            Call Playbook — Day {callDay}
          </h3>
          {opcsCode && (
            <p className="text-xs text-[var(--color-text-secondary,#6b7280)] mt-0.5">
              Pathway: {opcsCode}
            </p>
          )}
        </div>
        {hasEscalation && (
          <span className="px-2.5 py-1 rounded-lg bg-red-100 border border-red-300 text-red-800 text-xs font-bold animate-pulse">
            Escalation required
          </span>
        )}
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-6">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-500">Loading call playbook…</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {submitted && (
        <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800 font-medium">
          Scores submitted successfully.
          {hasEscalation && " Escalation actions have been triggered."}
        </div>
      )}

      {!loading && !error && !submitted && domains.length === 0 && (
        <p className="text-sm text-gray-500 py-4">No playbook available for this call day.</p>
      )}

      {!loading && !error && !submitted && domains.map((domain) => (
        <DomainCard
          key={domain}
          domain={domain}
          script={dayPlaybook[domain]}
          score={scores[domain]}
          onScore={(v) => setScores((prev) => ({ ...prev, [domain]: v }))}
        />
      ))}

      {!loading && !error && !submitted && domains.length > 0 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-[var(--color-text-secondary,#6b7280)]">
            {Object.keys(scores).length} / {domains.length} domains scored
          </p>
          <button
            type="button"
            onClick={submitScores}
            disabled={!allScored || submitting || !callId}
            className="px-5 py-2 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Submitting…" : "Submit Scores"}
          </button>
        </div>
      )}

      {submitError && (
        <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700">
          {submitError}
        </div>
      )}
    </div>
  );
}

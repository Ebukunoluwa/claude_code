import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboard } from "../api/decisions";
import { getMe } from "../api/auth";
import UrgencyBadge from "../components/UrgencyBadge";
import FTPBadge from "../components/FTPBadge";
import Layout from "../components/Layout";
import AddPatientModal from "../components/AddPatientModal";
import { timeAgo, formatDuration } from "../utils/timezone";

function getInitials(name) {
  if (!name) return "?";
  return name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
}

function avatarColor(severity) {
  if (severity === "red") return "bg-red-500";
  if (severity === "amber") return "bg-amber-500";
  return "bg-nhs-blue";
}

// Each card has a filter function that runs against the worklist
const STAT_CARDS = [
  {
    key: "total_active_patients",
    label: "Active Patients",
    filterId: "all",
    gradient: "bg-gradient-blue",
    filter: () => true,
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
  {
    key: "calls_today",
    label: "Calls Today",
    filterId: "calls_today",
    gradient: "bg-gradient-indigo",
    filter: (p) => {
      if (!p.last_call_at) return false;
      const today = new Date().toDateString();
      return new Date(p.last_call_at).toDateString() === today;
    },
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      </svg>
    ),
  },
  {
    key: "calls_missed",
    label: "Missed Calls",
    filterId: "calls_missed",
    gradient: "bg-gradient-red",
    filter: (p) => !p.last_call_at && !p.reviewed,
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
  },
  {
    key: "awaiting_review",
    label: "Awaiting Review",
    filterId: "awaiting_review",
    gradient: "bg-gradient-amber",
    filter: (p) => !p.reviewed,
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    key: "open_escalations",
    label: "Open Escalations",
    filterId: "open_escalations",
    gradient: "bg-gradient-rose",
    filter: (p) => p.urgency_severity === "red",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
];

export default function DashboardPage() {
  const [data, setData]         = useState(null);
  const [clinician, setClinician] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [activeFilter, setActiveFilter] = useState("all");
  const [search, setSearch]     = useState("");
  const [showAddPatient, setShowAddPatient] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getDashboard(), getMe()])
      .then(([dash, me]) => { setData(dash); setClinician(me); })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredWorklist = useMemo(() => {
    if (!data) return [];
    const card = STAT_CARDS.find((c) => c.filterId === activeFilter);
    let list = card ? data.worklist.filter(card.filter) : data.worklist;

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(
        (p) =>
          p.patient_name?.toLowerCase().includes(q) ||
          p.condition?.toLowerCase().includes(q) ||
          p.nhs_number?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [data, activeFilter, search]);

  function handleCardClick(filterId) {
    setActiveFilter((prev) => (prev === filterId ? "all" : filterId));
    setSearch("");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <aside className="sidebar" />
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-gray-500">
            <svg className="animate-spin w-5 h-5 text-nhs-blue" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            Loading dashboard…
          </div>
        </div>
      </div>
    );
  }

  const { stats, worklist } = data;
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  const activeCard = STAT_CARDS.find((c) => c.filterId === activeFilter);

  return (
    <Layout clinician={clinician}>
      <div className="flex-1 p-6 space-y-6">

        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Clinical Dashboard</h1>
            <p className="text-sm text-gray-500 mt-0.5">{today}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddPatient(true)}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-nhs-blue text-white rounded-xl hover:bg-blue-700 transition shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add Patient
            </button>
            <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-full px-3 py-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs font-medium text-green-700">System live</span>
            </div>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
          {STAT_CARDS.map((card) => {
            const isActive = activeFilter === card.filterId;
            return (
              <button
                key={card.key}
                onClick={() => handleCardClick(card.filterId)}
                className={`${card.gradient} rounded-2xl p-4 text-white relative overflow-hidden shadow-sm text-left transition-all duration-200 ${
                  isActive
                    ? "ring-4 ring-white/50 scale-[1.03] shadow-lg"
                    : "hover:scale-[1.02] hover:shadow-md opacity-90 hover:opacity-100"
                }`}
              >
                {/* active indicator */}
                {isActive && (
                  <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-white animate-pulse" />
                )}
                <div className="absolute top-0 right-0 w-24 h-24 rounded-full bg-white/10 -translate-y-8 translate-x-8" />
                <div className="relative z-10">
                  <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center mb-3">
                    {card.icon}
                  </div>
                  <div className="text-3xl font-extrabold leading-none">{stats[card.key] ?? 0}</div>
                  <div className="text-white/80 text-xs mt-1.5 font-medium">{card.label}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Worklist */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Worklist header with search */}
          <div className="px-6 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-gray-900">Patient Worklist</h2>
                {activeFilter !== "all" && (
                  <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full text-white ${activeCard?.gradient}`}>
                    {activeCard?.label}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                {activeFilter !== "all"
                  ? `Filtered by "${activeCard?.label}" · `
                  : "Sorted by urgency · unreviewed first · "}
                <span className="font-semibold text-gray-600">{filteredWorklist.length}</span> of {worklist.length} patients
                {activeFilter !== "all" && (
                  <button
                    onClick={() => { setActiveFilter("all"); setSearch(""); }}
                    className="ml-2 text-nhs-blue hover:underline"
                  >
                    Clear filter
                  </button>
                )}
              </p>
            </div>

            {/* Search */}
            <div className="relative w-full sm:w-64">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search by name, condition…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-nhs-blue/20 focus:border-nhs-blue transition"
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {filteredWorklist.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <svg className="w-10 h-10 mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm">
                {search ? `No patients matching "${search}"` : `No patients in "${activeCard?.label}"`}
              </p>
              <button
                onClick={() => { setActiveFilter("all"); setSearch(""); }}
                className="mt-2 text-xs text-nhs-blue hover:underline"
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/80 text-gray-500 text-xs font-semibold uppercase tracking-wider">
                    <th className="px-6 py-3 text-left">Patient</th>
                    <th className="px-4 py-3 text-left">Condition</th>
                    <th className="px-4 py-3 text-left">Day</th>
                    <th className="px-4 py-3 text-left">Last Call</th>
                    <th className="px-4 py-3 text-left">Next Call</th>
                    <th className="px-4 py-3 text-left">FTP</th>
                    <th className="px-4 py-3 text-left">Urgency</th>
                    <th className="px-4 py-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredWorklist.map((p) => (
                    <tr
                      key={p.patient_id}
                      onClick={() => navigate(`/patients/${p.patient_id}`)}
                      className="hover:bg-blue-50/50 cursor-pointer transition-colors group"
                    >
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full ${avatarColor(p.urgency_severity)} flex items-center justify-center text-white text-xs font-bold shrink-0 ${p.urgency_severity === "red" ? "pulse-red" : ""}`}>
                            {getInitials(p.patient_name)}
                          </div>
                          <div>
                            <span className="font-semibold text-gray-800 group-hover:text-nhs-blue transition-colors block">
                              {search ? <Highlight text={p.patient_name} query={search} /> : p.patient_name}
                            </span>
                            {p.nhs_number && (
                              <span className="text-[10px] text-gray-400">NHS {p.nhs_number}</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-gray-600">
                        {search ? <Highlight text={p.condition} query={search} /> : p.condition}
                      </td>
                      <td className="px-4 py-3.5">
                        {p.day_in_recovery != null ? (
                          <span className="text-xs font-semibold bg-blue-50 text-nhs-blue px-2 py-0.5 rounded-full">
                            Day {p.day_in_recovery}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="text-xs text-gray-700 font-medium">
                          {p.last_call_duration ? formatDuration(p.last_call_duration) : "—"}
                        </div>
                        {p.last_call_at && (
                          <div className="text-[10px] text-gray-400 mt-0.5">{timeAgo(p.last_call_at)}</div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-gray-500">
                        {p.next_scheduled_call ? (
                          <div>
                            <div className="font-medium text-gray-700">
                              {new Date(p.next_scheduled_call).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
                            </div>
                            <div className="text-gray-400">
                              {new Date(p.next_scheduled_call).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          </div>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3.5"><FTPBadge status={p.ftp_status} /></td>
                      <td className="px-4 py-3.5"><UrgencyBadge severity={p.urgency_severity} /></td>
                      <td className="px-4 py-3.5">
                        {p.reviewed ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                            Reviewed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            Pending
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {showAddPatient && clinician && (
        <AddPatientModal
          clinician={clinician}
          onClose={() => setShowAddPatient(false)}
          onAdded={() => {
            // Refresh dashboard after adding
            Promise.all([getDashboard(), getMe()])
              .then(([dash, me]) => { setData(dash); setClinician(me); });
          }}
        />
      )}
    </Layout>
  );
}

/* Highlights matching text in search results */
function Highlight({ text, query }) {
  if (!query || !text) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-100 text-yellow-900 rounded px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

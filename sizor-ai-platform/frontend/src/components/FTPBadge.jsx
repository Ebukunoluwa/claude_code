const CONFIG = {
  on_track: { label: "On Track", cls: "bg-green-50 text-green-700 border-green-200" },
  failing: { label: "Failing", cls: "bg-red-50 text-red-700 border-red-200" },
  improving: { label: "Improving", cls: "bg-blue-50 text-blue-700 border-blue-200" },
  unknown: { label: "Unknown", cls: "bg-gray-100 text-gray-500 border-gray-200" },
};

export default function FTPBadge({ status }) {
  const key = status || "unknown";
  const c = CONFIG[key] || CONFIG.unknown;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${c.cls}`}>
      {c.label}
    </span>
  );
}

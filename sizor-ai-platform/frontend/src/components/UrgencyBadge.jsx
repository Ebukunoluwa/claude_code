const CONFIG = {
  red: { label: "Red", cls: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-500" },
  amber: { label: "Amber", cls: "bg-amber-50 text-amber-700 border-amber-200", dot: "bg-amber-500" },
  green: { label: "Green", cls: "bg-green-50 text-green-700 border-green-200", dot: "bg-green-500" },
};

export default function UrgencyBadge({ severity = "green" }) {
  const c = CONFIG[severity] || CONFIG.green;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${c.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${c.dot}`} />
      {c.label}
    </span>
  );
}

/** Tiny SVG sparkline — matches the design exactly */
export default function Spark({ data, color, w = 72, h = 28 }) {
  if (!data || data.length < 2) return null;
  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const norm = (v) => h - ((v - mn) / (mx - mn || 1)) * (h - 4) - 2;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${norm(v)}`).join(" ");
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={w} cy={norm(data[data.length - 1])} r="2.5" fill={color} />
    </svg>
  );
}

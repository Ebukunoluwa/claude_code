export default function Sparkline({ data, color, w=64, h=28 }) {
  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const norm = v => h - ((v - mn) / (mx - mn || 1)) * (h - 4) - 2;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${norm(v)}`).join(" ");
  const gradId = "sg" + color.replace("#", "");
  return (
    <svg width={w} height={h} style={{ overflow:"visible" }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={color} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" opacity="0.9"/>
      <circle cx={w} cy={norm(data[data.length - 1])} r="2.5" fill={color}/>
    </svg>
  );
}

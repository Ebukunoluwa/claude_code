import { SEVERITY_COLORS } from "../utils/colors";

export default function PriorityDot({ severity = "green", size = 3 }) {
  const color = SEVERITY_COLORS[severity]?.dot || "#16A34A";
  return (
    <span
      className={`inline-block rounded-full w-${size} h-${size}`}
      style={{ backgroundColor: color, width: `${size * 4}px`, height: `${size * 4}px`, flexShrink: 0 }}
    />
  );
}

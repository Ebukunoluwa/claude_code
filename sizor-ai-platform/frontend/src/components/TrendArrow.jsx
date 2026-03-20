export default function TrendArrow({ trend }) {
  if (trend === "improving" || trend === "improving_fast") {
    return <span className="text-green-600 font-bold">↑</span>;
  }
  if (trend === "worsening" || trend === "declining" || trend === "acute_deterioration") {
    return <span className="text-red-600 font-bold">↓</span>;
  }
  return <span className="text-gray-400">→</span>;
}

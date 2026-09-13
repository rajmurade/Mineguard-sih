import { SEVERITY_STYLES } from "../constants.js";

// Compact semicircular arc gauge, color-coded by the compliance severity that
// the caller computed for the current value.
export default function Gauge({ value, max, severity, unit }) {
  const safeMax = max > 0 ? max : 1;
  const pct = Math.max(0, Math.min(value / safeMax, 1));
  const color = (SEVERITY_STYLES[severity] || {}).hex || "#475569";
  const arcLength = Math.PI * 50; // radius 50 semicircle

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 72" className="w-full max-w-[120px]">
        <path
          d="M 10 70 A 50 50 0 0 1 110 70"
          fill="none"
          stroke="#1e2a44"
          strokeWidth="9"
          strokeLinecap="round"
        />
        <path
          d="M 10 70 A 50 50 0 0 1 110 70"
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${pct * arcLength} ${arcLength}`}
          style={{ filter: `drop-shadow(0 0 4px ${color}66)` }}
        />
        <text
          x="60"
          y="58"
          textAnchor="middle"
          className="fill-slate-100 font-mono"
          style={{ fontSize: "17px", fontWeight: 700 }}
        >
          {Number.isFinite(value) ? value.toFixed(0) : "—"}
        </text>
      </svg>
      <span className="mt-1 text-[9px] uppercase tracking-widest text-slate-500">
        {unit}
      </span>
    </div>
  );
}
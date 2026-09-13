import { useEffect, useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Sector, Tooltip } from "recharts";
import { getIncidents } from "../api.js";
import { INCIDENT_TYPE_LABELS } from "../constants.js";
import Panel from "./Panel.jsx";

const TYPE_COLORS = {
  ppe_violation: "#f87171",
  proximity_risk: "#fb923c",
  fire_smoke: "#fbbf24",
  environmental: "#22d3ee",
  unauthorized_zone: "#a78bfa",
  fall: "#34d399",
};

const TOOLTIP_STYLE = {
  backgroundColor: "#0f161b",
  border: "1px solid #23303a",
  borderRadius: "6px",
  fontSize: "12px",
  color: "#cbd5e1",
};

function Donut({ data }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const total = data.reduce((sum, d) => sum + d.value, 0);

  const renderActiveShape = (props) => {
    const {
      cx,
      cy,
      innerRadius,
      outerRadius,
      startAngle,
      endAngle,
      fill,
      payload,
    } = props;
    return (
      <g>
        <text x={cx} y={cy - 6} textAnchor="middle" fill="#7dd3fc" fontSize="22" fontWeight="bold" fontFamily="ui-monospace, monospace">
          {payload.value}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill="#64748b" fontSize="10">
          {payload.name}
        </text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius + 5}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
      </g>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={62}
          outerRadius={86}
          paddingAngle={2}
          cornerRadius={4}
          activeIndex={activeIndex ?? undefined}
          activeShape={renderActiveShape}
          onMouseEnter={(_, index) => setActiveIndex(index)}
          onMouseLeave={() => setActiveIndex(null)}
        >
          {data.map((d) => (
            <Cell key={d.type} fill={TYPE_COLORS[d.type] || "#64748b"} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export default function IncidentsByTypePie() {
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    getIncidents()
      .then((list) => {
        if (!alive) return;
        setIncidents(Array.isArray(list) ? list : []);
        setError(false);
      })
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, []);

  const data = useMemo(() => {
    const counts = new Map();
    for (const inc of incidents) {
      counts.set(inc.type, (counts.get(inc.type) || 0) + 1);
    }
    return [...counts.entries()].map(([type, value]) => ({
      type,
      name: INCIDENT_TYPE_LABELS[type] || type,
      value,
    }));
  }, [incidents]);

  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <Panel
      title="Incidents by Type"
      right={<span className="text-[10px] text-slate-500">{total} total</span>}
    >
      {error ? (
        <div className="px-1 text-xs text-slate-500">Unable to load incidents.</div>
      ) : total === 0 ? (
        <div className="px-1 text-xs text-slate-500">No incidents recorded.</div>
      ) : (
        <div className="flex flex-col items-center gap-1">
          <Donut data={data} />
          <ul className="grid w-full max-w-sm grid-cols-2 gap-x-4 gap-y-1 px-1">
            {data.map((d) => (
              <li key={d.type} className="flex items-center gap-2 text-[11px] text-slate-400">
                <span
                  className="h-2 w-2 shrink-0 rounded-sm"
                  style={{ backgroundColor: TYPE_COLORS[d.type] || "#64748b" }}
                />
                <span className="truncate">{d.name}</span>
                <span className="ml-auto font-mono text-slate-300">{d.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
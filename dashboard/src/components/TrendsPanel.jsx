import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getIncidents } from "../api.js";
import { SEVERITY_STYLES } from "../constants.js";
import { dayKey } from "../format.js";
import Panel from "./Panel.jsx";

const DAYS = 14;

const TOOLTIP_STYLE = {
  backgroundColor: "#0f1a2e",
  border: "1px solid #1e2a44",
  borderRadius: 8,
  fontSize: 12,
};

function lastNDays(n) {
  const out = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    out.push({
      key: dayKey(d.toISOString()),
      label: d.toLocaleDateString([], { month: "short", day: "numeric" }),
    });
  }
  return out;
}

function incidentsPerDay(incidents) {
  const days = lastNDays(DAYS);
  const byDay = days.reduce((acc, d) => {
    acc[d.key] = { ...d, critical: 0, high: 0, warning: 0, compliant: 0 };
    return acc;
  }, {});
  for (const inc of incidents) {
    const key = inc.timestamp ? dayKey(inc.timestamp) : null;
    if (key && byDay[key]) {
      const sev = inc.severity;
      if (sev in byDay[key]) byDay[key][sev] += 1;
    }
  }
  return Object.values(byDay);
}

export default function TrendsPanel() {
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    getIncidents()
      .then((list) => alive && setIncidents(Array.isArray(list) ? list : []))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, []);

  const data = useMemo(() => incidentsPerDay(incidents), [incidents]);

  return (
    <Panel
      title="Incident Trends — last 14 days"
      right={error ? <span className="text-[10px] text-red-400">offline</span> : null}
    >
      <div className="p-3">
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid stroke="#1e2a44" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "#1e2a44" }} />
              <YAxis allowDecimals={false} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#1e2a4422" }} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <Bar dataKey="critical" stackId="s" fill={SEVERITY_STYLES.critical.hex} name="Critical" />
              <Bar dataKey="high" stackId="s" fill={SEVERITY_STYLES.high.hex} name="High" />
              <Bar dataKey="warning" stackId="s" fill={SEVERITY_STYLES.warning.hex} name="Warning" />
              <Bar dataKey="compliant" stackId="s" fill={SEVERITY_STYLES.compliant.hex} name="Compliant" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Panel>
  );
}
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getLatestReadings, getReadings } from "../api.js";
import {
  METRIC_BANDS,
  METRIC_MAX,
  METRIC_UNITS,
  SEVERITY_STYLES,
  classifyValue,
} from "../constants.js";
import { fmtTime } from "../format.js";
import Gauge from "./Gauge.jsx";
import Panel from "./Panel.jsx";

const METRICS = ["aqi", "gas_level", "temperature", "noise_db", "dust_pm"];
const METRIC_LABELS = { aqi: "AQI", gas_level: "CO", temperature: "Temp", noise_db: "Noise", dust_pm: "Dust" };

const TOOLTIP_STYLE = {
  backgroundColor: "#0f1a2e",
  border: "1px solid #1e2a44",
  borderRadius: 8,
  fontSize: 12,
};

function MetricCell({ reading, metric }) {
  const value = reading?.[metric];
  const severity = classifyValue(METRIC_BANDS[metric], value);
  const style = SEVERITY_STYLES[severity] || {};
  return (
    <div className="flex items-center gap-2.5 rounded-md border border-ops-border bg-ops-rail px-2 py-2">
      <Gauge value={value ?? 0} max={METRIC_MAX[metric]} severity={severity} unit={METRIC_UNITS[metric]} />
      <div className="min-w-0">
        <div className="text-[9px] uppercase tracking-wider text-slate-500">
          {METRIC_LABELS[metric]}
        </div>
        <div className="font-mono text-sm font-semibold text-slate-100">
          {value ?? "—"}
        </div>
        <div className="flex items-center gap-1 text-[9px] text-slate-400">
          <span className={`h-1 w-1 rounded-full ${style.dot || "bg-slate-500"}`} />
          {severity === "na" ? "no data" : severity}
        </div>
      </div>
    </div>
  );
}

function ZoneCard({ reading }) {
  return (
    <div className="rounded-lg border border-ops-border bg-ops-panel/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-200">{reading.zone}</h3>
        <span className="font-mono text-[10px] text-slate-500">{fmtTime(reading.timestamp)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {METRICS.map((m) => (
          <MetricCell key={m} reading={reading} metric={m} />
        ))}
      </div>
    </div>
  );
}

function AqiTrend({ zone }) {
  const [points, setPoints] = useState([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!zone) return;
    let alive = true;
    setError(false);
    getReadings(zone, 300)
      .then((list) => {
        if (!alive) return;
        const now = Date.now();
        const withinHour = (Array.isArray(list) ? list : [])
          .filter((r) => r.timestamp && now - new Date(r.timestamp).getTime() <= 60 * 60 * 1000)
          .map((r) => ({ t: fmtTime(r.timestamp), aqi: r.aqi, gas: r.gas_level }))
          .reverse();
        setPoints(withinHour);
      })
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, [zone]);

  if (points.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-xs text-slate-500">
        {error ? "Could not load AQI history for " + zone : "No readings in the last 60 min for " + zone}
      </div>
    );
  }

  const withIdx = points.map((p, i) => ({ ...p, seq: i }));

  return (
    <div className="h-44">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={withIdx} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#1e2a44" strokeDasharray="3 3" />
          <XAxis dataKey="seq" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(v) => withIdx[v]?.t ?? ""} interval="preserveStartEnd" />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(v, name) => [v, name === "aqi" ? "AQI" : "CO ppm"]}
            labelFormatter={(v) => withIdx[v]?.t ?? ""}
          />
          <Line type="monotone" dataKey="aqi" stroke="#22d3ee" strokeWidth={2} dot={false} name="aqi" />
          <Line type="monotone" dataKey="gas" stroke="#a78bfa" strokeWidth={1.5} dot={false} name="gas" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function EnvironmentalPanel() {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [error, setError] = useState(false);

  const load = () =>
    getLatestReadings()
      .then((list) => {
        setError(false);
        setZones(Array.isArray(list) ? list : []);
      })
      .catch(() => setError(true));

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 15000);
    return () => window.clearInterval(timer);
  }, []);

  const activeZone = useMemo(
    () => selectedZone || zones[0]?.zone || null,
    [selectedZone, zones]
  );

  return (
    <Panel
      title="Environmental Conditions"
      right={
        <span className="text-[10px] text-slate-500">
          {error ? "offline" : `${zones.length} zone(s) · 15s refresh`}
        </span>
      }
    >
      <div className="space-y-3 p-3">
        {zones.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-xs text-slate-500">
            {error ? "Backend unreachable" : "No readings yet"}
          </div>
        ) : (
          zones.map((r) => <ZoneCard key={r.zone} reading={r} />)
        )}

        <div className="rounded-lg border border-ops-border bg-ops-panel/60 p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-200">
              AQI / CO — last 60 min
            </h3>
            <select
              className="input"
              value={activeZone ?? ""}
              onChange={(e) => setSelectedZone(e.target.value || null)}
            >
              {zones.map((r) => (
                <option key={r.zone} value={r.zone}>
                  {r.zone}
                </option>
              ))}
            </select>
          </div>
          <AqiTrend zone={activeZone} />
        </div>
      </div>
    </Panel>
  );
}
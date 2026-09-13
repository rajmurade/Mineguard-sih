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
import { METRIC_MAX, METRIC_UNITS } from "../constants.js";
import { fmtTime } from "../format.js";
import Panel from "./Panel.jsx";

const METRICS = ["aqi", "gas_level", "temperature", "noise_db", "dust_pm"];
const METRIC_LABELS = {
  aqi: "AQI",
  gas_level: "CO",
  temperature: "Temp",
  noise_db: "Noise",
  dust_pm: "Dust",
};
const ZONE_COLORS = ["#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#f87171", "#60a5fa"];

const TOOLTIP_STYLE = {
  backgroundColor: "#0f1a2e",
  border: "1px solid #1e2a44",
  borderRadius: 8,
  fontSize: 12,
};

export default function MetricTrendsPanel() {
  const [zones, setZones] = useState([]);
  const [metric, setMetric] = useState("aqi");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    setError(false);

    getLatestReadings()
      .then(async (latest) => {
        if (!alive) return;
        const zoneList = (Array.isArray(latest) ? latest : []).map((r) => r.zone);
        if (zoneList.length === 0) {
          if (alive) setZones([]);
          return;
        }
        const perZone = await Promise.all(
          zoneList.map((zone) =>
            getReadings(zone, 120)
              .then((list) => ({
                zone,
                points: (Array.isArray(list) ? list : []).map((r) => ({
                  ts: new Date(r.timestamp).getTime(),
                  value: r[metric],
                })),
              }))
              .catch(() => ({ zone, points: [] }))
          )
        );
        if (!alive) return;

        setZones(zoneList.filter((z) => perZone.find((p) => p.zone === z)?.points.length));
        // Align every zone to the shared set of timestamps (last reading at or before t).
        const tsSet = new Set();
        perZone.forEach((p) => p.points.forEach((pt) => pt.value != null && tsSet.add(pt.ts)));
        const tsList = [...tsSet].sort((a, b) => a - b);
        const aligned = tsList.map((ts) => {
          const row = { t: fmtTime(new Date(ts)) };
          perZone.forEach(({ zone, points }) => {
            let value = null;
            for (let i = points.length - 1; i >= 0; i -= 1) {
              if (points[i].ts <= ts) {
                value = points[i].value;
                break;
              }
            }
            row[zone] = value;
          });
          return row;
        });
        if (alive) setRows(aligned);
      })
      .catch(() => alive && setError(true));

    return () => {
      alive = false;
    };
  }, [metric]);

  const visibleZones = useMemo(
    () => zones.filter((z) => rows.some((r) => r[z] != null)),
    [zones, rows]
  );

  return (
    <Panel
      title="Environmental Trends · across zones"
      right={
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500">metric</span>
          <select className="input" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {METRICS.map((m) => (
              <option key={m} value={m}>
                {METRIC_LABELS[m]}
              </option>
            ))}
          </select>
        </div>
      }
    >
      <div className="space-y-2 p-3">
        {error ? (
          <div className="flex h-40 items-center justify-center text-xs text-slate-500">
            Backend unreachable
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-xs text-slate-500">
            No readings yet
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-1.5">
              {visibleZones.map((z, i) => (
                <span
                  key={z}
                  className="flex items-center gap-1.5 text-[11px] text-slate-400"
                >
                  <span
                    className="h-2 w-2 rounded-sm"
                    style={{ backgroundColor: ZONE_COLORS[i % ZONE_COLORS.length] }}
                  />
                  {z}
                </span>
              ))}
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rows} margin={{ top: 8, right: 8, left: -14, bottom: 0 }}>
                  <CartesianGrid stroke="#1e2a44" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="t"
                    tick={{ fill: "#64748b", fontSize: 10 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{ fill: "#64748b", fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    domain={[0, METRIC_MAX[metric]]}
                    tickFormatter={(v) => `${v}${METRIC_UNITS[metric]}`}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: "#94a3b8" }} />
                  {visibleZones.map((z, i) => (
                    <Line
                      key={z}
                      type="monotone"
                      dataKey={z}
                      stroke={ZONE_COLORS[i % ZONE_COLORS.length]}
                      strokeWidth={1.75}
                      dot={false}
                      name={z}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}
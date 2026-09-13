import { useCallback, useEffect, useState } from "react";
import { getActiveWorkers, getIncidents, getLatestReadings } from "../api.js";
import { METRIC_BANDS, classifyValue } from "../constants.js";

const COMPLIANCE_METRICS = ["aqi", "gas_level", "temperature", "noise_db", "dust_pm"];

function complianceRate(readings) {
  let compliant = 0;
  let total = 0;
  for (const r of readings || []) {
    for (const metric of COMPLIANCE_METRICS) {
      const value = r?.[metric];
      if (value === null || value === undefined || Number.isNaN(Number(value))) continue;
      total += 1;
      if (classifyValue(METRIC_BANDS[metric], Number(value)) === "compliant") compliant += 1;
    }
  }
  return total > 0 ? Math.round((compliant / total) * 100) : null;
}

function KpiCard({ label, value, suffix, tone, hint }) {
  const toneColors = {
    cyan: "text-cyan-300",
    amber: "text-amber-300",
    red: "text-red-400",
    emerald: "text-emerald-300",
  };
  return (
    <div className="flex items-center justify-between rounded-lg border border-ops-border bg-ops-panel px-4 py-3">
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
        <div className="mt-1 font-mono text-2xl leading-none">
          <span className={toneColors[tone] || toneColors.cyan}>
            {value ?? "—"}
          </span>
          {suffix && value !== null && (
            <span className="text-sm text-slate-400">{suffix}</span>
          )}
        </div>
      </div>
      <span className="shrink-0 text-[10px] text-slate-600">{hint}</span>
    </div>
  );
}

export default function KpiBar() {
  const [workers, setWorkers] = useState(null);
  const [openAlerts, setOpenAlerts] = useState(null);
  const [critical, setCritical] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    try {
      const [workerList, incidents, latest] = await Promise.all([
        getActiveWorkers(),
        getIncidents(),
        getLatestReadings(),
      ]);
      setWorkers(Array.isArray(workerList) ? workerList.length : null);
      const open = (Array.isArray(incidents) ? incidents : []).filter(
        (i) => i.resolution_status === "open"
      );
      setOpenAlerts(open.length);
      setCritical(open.filter((i) => i.severity === "critical").length);
      setCompliance(complianceRate(Array.isArray(latest) ? latest : []));
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, [load]);

  return (
    <section className="border-b border-ops-border bg-ops-rail/40">
      <div className="mx-auto w-full max-w-screen-2xl px-4 py-3">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label="Workers Inside"
            value={workers}
            tone="cyan"
            hint={offline ? "offline" : "on-site"}
          />
          <KpiCard
            label="Active Alerts"
            value={openAlerts}
            tone="amber"
            hint="open incidents"
          />
          <KpiCard
            label="Critical Incidents"
            value={critical}
            tone="red"
            hint="severity critical"
          />
          <KpiCard
            label="Compliance Rate"
            value={compliance}
            suffix="%"
            tone="emerald"
            hint="env readings"
          />
        </div>
      </div>
    </section>
  );
}
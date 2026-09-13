import { useEffect, useState } from "react";
import {
  getLatestReadings,
  sendEnvironmentalReading,
  startEmergencyDrill,
} from "../api.js";
import Panel from "./Panel.jsx";

const FALLBACK_ZONES = ["Zone A - Tunnel 1", "Zone B - Open Pit"];

const GAS_LEVELS = [
  { label: "Normal", value: 25 },
  { label: "Elevated", value: 100 },
  { label: "High", value: 200 },
  { label: "Critical", value: 400 },
];

const SLIDERS = [
  { key: "aqi", label: "AQI", min: 0, max: 1000, unit: "" },
  { key: "temperature", label: "Temp", min: 0, max: 60, unit: "°C" },
  { key: "noise_db", label: "Noise", min: 0, max: 140, unit: "dB" },
  { key: "dust_pm", label: "Dust / PM", min: 0, max: 1000, unit: "mg/m³" },
];

export default function SimulateEventPanel() {
  // Zones come from the backend (same source as EnvironmentalPanel); fall back
  // to the standard two zones when the API has no readings yet.
  const [zones, setZones] = useState([]);
  const [zone, setZone] = useState(FALLBACK_ZONES[0]);
  const [gasIdx, setGasIdx] = useState(0);
  const [values, setValues] = useState({ aqi: 50, temperature: 25, noise_db: 60, dust_pm: 1 });
  const [sending, setSending] = useState(false);
  const [drilling, setDrilling] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let alive = true;
    getLatestReadings()
      .then((list) => {
        if (!alive) return;
        const fetched = (Array.isArray(list) ? list : [])
          .map((r) => r.zone)
          .filter(Boolean);
        if (fetched.length > 0) {
          const unique = Array.from(new Set(fetched));
          setZones(unique);
          setZone((current) => (unique.includes(current) ? current : unique[0]));
        }
      })
      .catch(() => {
        /* keep the fallback zones so the demo tool still works offline */
      });
    return () => {
      alive = false;
    };
  }, []);

  const activeZones = zones.length > 0 ? zones : FALLBACK_ZONES;

  const sendReading = async () => {
    setSending(true);
    setResult(null);
    try {
      const body = await sendEnvironmentalReading({
        zone,
        gas_level: GAS_LEVELS[gasIdx].value,
        aqi: values.aqi,
        temperature: values.temperature,
        noise_db: values.noise_db,
        dust_pm: values.dust_pm,
        source: "simulated",
      });
      const incidents = (body.evaluations || []).filter((e) => e.should_create_incident);
      setResult({
        kind: "ok",
        text: incidents.length
          ? `incident #${incidents.map((e) => e.incident_id).join(", #")} triggered`
          : "reading sent (no incident)",
      });
    } catch (err) {
      setResult({ kind: "err", text: String(err) });
    } finally {
      setSending(false);
    }
  };

  const triggerDrill = async () => {
    setDrilling(true);
    setResult(null);
    try {
      const body = await startEmergencyDrill(zone);
      setResult({
        kind: "ok",
        text: `drill — ${body.unaccounted_count} unaccounted in ${body.zone}`,
      });
    } catch (err) {
      setResult({ kind: "err", text: String(err) });
    } finally {
      setDrilling(false);
    }
  };

  return (
    <Panel
      title="Demo Controls"
      right={
        <span className="chip border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
          simulated
        </span>
      }
    >
      <div className="space-y-3 p-3">
        <label className="block">
          <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
            Zone
          </span>
          <select
            className="input w-full"
            value={zone}
            onChange={(e) => setZone(e.target.value)}
          >
            {activeZones.map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
            Gas level
          </span>
          <select
            className="input w-full"
            value={gasIdx}
            onChange={(e) => setGasIdx(Number(e.target.value))}
          >
            {GAS_LEVELS.map((g, i) => (
              <option key={g.label} value={i}>
                {g.label} ({g.value} ppm)
              </option>
            ))}
          </select>
        </label>

        {SLIDERS.map((s) => (
          <label key={s.key} className="block">
            <span className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-500">
              <span>{s.label}</span>
              <span className="rounded bg-ops-rail px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">
                {values[s.key]}
                {s.unit}
              </span>
            </span>
            <input
              type="range"
              className="range"
              min={s.min}
              max={s.max}
              value={values[s.key]}
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [s.key]: Number(e.target.value) }))
              }
            />
          </label>
        ))}

        <button
          className="btn-primary w-full"
          onClick={sendReading}
          disabled={sending || drilling}
        >
          {sending ? "Sending…" : "Send Reading"}
        </button>
        <button
          className="btn-ghost !border-red-500/40 !text-red-300 hover:!bg-red-500/10"
          onClick={triggerDrill}
          disabled={drilling || sending}
        >
          {drilling ? "Triggering…" : "Trigger Emergency Drill"}
        </button>

        {result && (
          <div
            className={`text-[11px] leading-snug ${
              result.kind === "err" ? "text-red-400" : "text-emerald-300"
            }`}
          >
            {result.kind === "err" ? `Failed: ${result.text}` : result.text}
          </div>
        )}
      </div>
    </Panel>
  );
}
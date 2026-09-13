import { useState } from "react";
import { reportUrl } from "../api.js";
import Panel from "./Panel.jsx";

const RANGES = [
  { value: "daily", label: "Daily (last 24 hours)" },
  { value: "weekly", label: "Weekly (last 7 days)" },
];

const FORMATS = [
  {
    value: "pdf",
    label: "PDF",
    desc: "ReportLab summary with severity/type breakdowns and the incident log",
  },
  {
    value: "xlsx",
    label: "XLSX",
    desc: "OpenPyXL workbook: Summary, Incidents and Environmental sheets",
  },
];

async function download(format, range) {
  const res = await fetch(reportUrl(format, range), {
    headers: { Accept: "application/octet-stream" },
  });
  if (!res.ok) {
    throw new Error(`Export failed (HTTP ${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^";]+)"?/.exec(disposition);
  a.download = match ? match[1] : `mineguard_${range}.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ReportsTab() {
  const [range, setRange] = useState("daily");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);

  const trigger = async (format) => {
    setBusy(format);
    setError(null);
    try {
      await download(format, range);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Panel title="Reports — export">
      <div className="max-w-3xl p-4">
        <p className="mb-4 text-xs text-slate-400">
          Summarizes incidents and environmental readings for the selected range.
          The PDF is generated with ReportLab, the spreadsheet with OpenPyXL.
        </p>

        <div className="mb-4">
          <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">
            Time range
          </span>
          <div className="flex flex-wrap gap-2">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={
                  r.value === range
                    ? "btn-primary"
                    : "btn-ghost"
                }
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {FORMATS.map((f) => (
            <button
              key={f.value}
              disabled={busy !== null}
              onClick={() => trigger(f.value)}
              className="group flex items-start justify-between gap-3 rounded-lg border border-ops-border bg-ops-rail p-4 text-left transition-colors hover:border-cyan-500/50"
            >
              <div>
                <div className="font-mono text-lg font-bold text-cyan-300">
                  {f.label}
                </div>
                <p className="mt-1 text-[11px] text-slate-500">{f.desc}</p>
                <span className="mt-2 inline-block text-[10px] text-cyan-400">
                  GET /reports/export?format={f.value}&amp;range={range}
                </span>
              </div>
              <span className="text-2xl text-slate-600 group-hover:text-cyan-400">
                {busy === f.value ? "…" : "↓"}
              </span>
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            {error}
          </div>
        )}
      </div>
    </Panel>
  );
}
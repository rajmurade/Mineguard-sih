import { useEffect, useState } from "react";
import { SEVERITY_STYLES } from "../constants.js";

const WS_LABEL = {
  connecting: { dot: "bg-amber-400 animate-pulse", text: "LINKING…" },
  connected: { dot: "bg-emerald-400", text: "LIVE" },
  reconnecting: { dot: "bg-red-500 animate-pulse", text: "RECONNECTING…" },
};

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="text-right font-mono">
      <div className="text-lg leading-tight text-slate-100">
        {now.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">
        {now.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}
      </div>
    </div>
  );
}

function SeverityChips({ openIncidents }) {
  if (!openIncidents || openIncidents.length === 0) return null;
  return (
    <div className="hidden items-center gap-1.5 md:flex">
      {openIncidents.map(({ severity, count }) => {
        const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.warning;
        return (
          <span key={severity} className={style.badge}>
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            {severity} {count}
          </span>
        );
      })}
    </div>
  );
}

export default function TopBar({ wsStatus, summary, backendOk }) {
  const ws = WS_LABEL[wsStatus] || WS_LABEL.connecting;
  const systemStatus = !backendOk
    ? { dot: "bg-red-500 animate-pulse", text: "DEGRADED" }
    : { dot: "bg-emerald-400", text: "OPERATIONAL" };

  return (
    <header className="sticky top-0 z-40 border-b border-ops-border bg-ops-rail/95 backdrop-blur">
      <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-4 py-2.5">
        <div className="flex items-center gap-4">
          <div className="leading-tight">
            <div className="font-mono text-base font-bold tracking-widest text-cyan-300">
              MINEGUARD
            </div>
            <div className="text-[9px] uppercase tracking-[0.3em] text-slate-500">
              Operations Center
            </div>
          </div>
          <div className="hidden h-8 w-px bg-ops-border sm:block" />
          <div className="hidden items-center gap-3 sm:flex">
            <span className={`chip border-slate-600/40 bg-slate-800/40 text-slate-300`}>
              <span className={`h-1.5 w-1.5 rounded-full ${systemStatus.dot}`} />
              SYS {systemStatus.text}
            </span>
            <span className="chip border-slate-600/40 bg-slate-800/40 text-slate-300">
              <span className={`h-1.5 w-1.5 rounded-full ${ws.dot}`} />
              WS {ws.text}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <SeverityChips openIncidents={summary?.open_incidents} />
          <div className="hidden items-center gap-2 rounded-lg border border-ops-border bg-ops-panel px-3 py-1.5 sm:flex">
            <span className="font-mono text-2xl font-bold leading-none text-cyan-300">
              {summary?.active_worker_count ?? "—"}
            </span>
            <span className="text-[10px] uppercase leading-tight tracking-wider text-slate-400">
              Active
              <br />
              workers
            </span>
          </div>
          <Clock />
        </div>
      </div>
    </header>
  );
}
import { useCallback, useEffect, useState } from "react";
import { fmtTime } from "../format.js";
import Panel from "./Panel.jsx";

const POLL_MS = 3000;

export default function WorkerStatusPanel() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(false);

  // Same /cv-stream/status polling LiveFeedPanel uses — one signal for both
  // the live frame and the worker count on it.
  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch("/cv-stream/status");
      if (!res.ok) return;
      setStatus(await res.json());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    pollStatus();
    const timer = window.setInterval(pollStatus, POLL_MS);
    return () => window.clearInterval(timer);
  }, [pollStatus]);

  const active =
    !!status?.active && (status.frame_count ?? 0) > 0;
  const count = active ? Math.max(0, status.current_worker_count ?? 0) : 0;

  return (
    <Panel
      title="Workers Detected"
      className="h-full"
      right={
        active ? (
          <span className="chip border-red-500/50 bg-red-500/10 text-red-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-500" />
            LIVE
          </span>
        ) : (
          <span className="chip border-slate-600/40 bg-slate-800/40 text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-500" />
            STANDBY
          </span>
        )
      }
    >
      {!active ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 p-5 text-center">
          <div className="text-sm font-semibold text-slate-300">
            {error ? "Camera feed unreachable" : "No active camera feed"}
          </div>
          <p className="max-w-md text-[11px] leading-relaxed text-slate-500">
            Worker presence comes from the CV pipeline. Start it pointed at this
            backend, e.g.{" "}
            <code className="rounded bg-ops-rail px-1 py-0.5 font-mono text-[10px] text-cyan-300">
              python -m cv_pipeline.run_live --stream-url http://localhost:8000
            </code>
            .
          </p>
        </div>
      ) : (
        <div className="p-3">
          <div className="rounded-md border border-ops-border bg-ops-rail px-3 py-2">
            <div className="font-mono text-3xl font-bold leading-none text-cyan-300">
              {count}
            </div>
            <div className="mt-1 text-[10px] uppercase tracking-wider text-slate-500">
              Workers Detected · in current frame
            </div>
          </div>

          {count > 0 ? (
            <ul className="mt-2 grid grid-cols-2 gap-1.5">
              {Array.from({ length: count }, (_, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 rounded-md border border-ops-border px-2 py-1.5 text-xs"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  <span className="font-mono text-slate-300">Worker {i + 1}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-2 text-xs text-slate-500">No workers in view.</div>
          )}

          {status?.last_updated && (
            <div className="mt-2 text-right font-mono text-[9px] text-slate-600">
              frame {status.frame_count} · {fmtTime(status.last_updated)}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
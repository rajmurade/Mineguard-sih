import { useCallback, useEffect, useRef, useState } from "react";
import Panel from "./Panel.jsx";

// Live CCTV feed.
//
// The panel renders a plain <img src="/cv-stream"> — an MJPEG
// (multipart/x-mixed-replace) stream served by FastAPI, no video library needed.
//
// IMPORTANT: for anything to show, the CV pipeline must be ACTIVELY RUNNING
// (python -m cv_pipeline.run_live ... or python -m cv_pipeline.run_recorded ...)
// AND pointed at the stream endpoint on this backend, e.g.:
//
//     python -m cv_pipeline.run_live --source 0 \
//         --api-url http://localhost:8000 --stream-url http://localhost:8000
//     python -m cv_pipeline.run_recorded --file clip.mp4 --stream-url http://localhost:8000
//
// The pipeline's FramePublisher POSTs JPEG-encoded, detection-box-annotated
// frames to POST /cv-stream; the frontend polls GET /cv-stream/status and only
// points <img> at GET /cv-stream while the feed is fresh. Otherwise it renders
// a "no active feed" placeholder instead of a broken image icon.
//
// No pipeline running -> status.active is false -> placeholder panel.

const STALE_AFTER_SECONDS = 5;
const POLL_MS = 3000;

function NoFeedNotice({ status }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <svg
        className="h-10 w-10 text-slate-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"
        />
      </svg>
      <div className="text-sm font-semibold text-slate-300">No active feed</div>
      <p className="max-w-lg text-[11px] leading-relaxed text-slate-500">
        The live CCTV feed requires the CV pipeline to be running and pointed at
        this stream endpoint. Start it with e.g.{" "}
        <code className="rounded bg-ops-rail px-1 py-0.5 font-mono text-[10px] text-cyan-300">
          python -m cv_pipeline.run_live --source 0 --stream-url http://localhost:8000
        </code>{" "}
        (or <code className="rounded bg-ops-rail px-1 py-0.5 font-mono text-[10px] text-cyan-300">run_recorded --file clip.mp4 --stream-url http://localhost:8000</code>).
        Annotated frames with detection boxes will start streaming here
        automatically.
      </p>
      {status?.last_updated && (
        <span className="font-mono text-[10px] text-slate-600">
          last frame {new Date(status.last_updated).toLocaleTimeString()} · no frames since
        </span>
      )}
    </div>
  );
}

export default function LiveFeedPanel() {
  const [status, setStatus] = useState(null);
  const [imgFailed, setImgFailed] = useState(false);
  const imgRef = useRef(null);

  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch("/cv-stream/status");
      if (!res.ok) return;
      setStatus(await res.json());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    pollStatus();
    const timer = window.setInterval(pollStatus, POLL_MS);
    return () => window.clearInterval(timer);
  }, [pollStatus]);

  const active =
    !!status?.active && !imgFailed && status.frame_count > 0;

  return (
    <Panel
      title="Live CCTV Feed — annotated stream"
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
      <div className="relative aspect-video bg-black">
        {active && (
          <img
            ref={imgRef}
            src="/cv-stream"
            alt="Live CCTV feed with detection boxes"
            className="absolute inset-0 h-full w-full object-contain"
            onError={() => setImgFailed(true)}
          />
        )}
        {active && status && (
          <>
            <div className="absolute bottom-2 left-2 flex items-center gap-2 rounded bg-black/70 px-2 py-1 font-mono text-[10px] text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              {status.source}
            </div>
            <div className="absolute bottom-2 right-2 rounded bg-black/70 px-2 py-1 font-mono text-[10px] text-slate-400">
              frame {status.frame_count} · {new Date(status.last_updated).toLocaleTimeString()}
            </div>
          </>
        )}
        {!active && <NoFeedNotice status={status} />}
      </div>
    </Panel>
  );
}
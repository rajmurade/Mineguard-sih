import { useEffect, useMemo, useState } from "react";
import { getIncidents } from "../api.js";
import { INCIDENT_TYPE_LABELS, SEVERITY_STYLES } from "../constants.js";
import { CV_EVENT_LABELS, incidentTypeLabel, parseIncidentDescription } from "../formatters.js";
import { fmtTime } from "../format.js";
import Panel from "./Panel.jsx";

const CV_TYPES = new Set([
  "ppe_violation",
  "proximity_risk",
  "fire_smoke",
  "fall",
  "unauthorized_zone",
]);

export default function AIDetectionsPanel() {
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

  const cvList = useMemo(
    () =>
      (Array.isArray(incidents) ? incidents : [])
        .filter((i) => CV_TYPES.has(i.type))
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)),
    [incidents]
  );

  const groups = useMemo(() => {
    const map = new Map();
    for (const inc of cvList) {
      const parsed = parseIncidentDescription(inc.description);
      const eventType = parsed?.event_type || inc.type;
      let g = map.get(eventType);
      if (!g) {
        g = {
          eventType,
          count: 0,
          severity: inc.severity,
          latest: inc.timestamp,
          label:
            CV_EVENT_LABELS[eventType] ||
            INCIDENT_TYPE_LABELS[inc.type] ||
            eventType,
        };
        map.set(eventType, g);
      }
      g.count += 1;
      if (new Date(inc.timestamp) > new Date(g.latest)) {
        g.latest = inc.timestamp;
        g.severity = inc.severity;
      }
    }
    return [...map.values()].sort((a, b) => b.count - a.count);
  }, [cvList]);

  const recent = cvList.slice(0, 6);

  return (
    <Panel title="AI Detections · recent CV activity">
      {error ? (
        <div className="px-1 text-xs text-slate-500">Unable to load detections.</div>
      ) : cvList.length === 0 ? (
        <div className="px-1 text-xs text-slate-500">
          No CV detections yet — start camera/cv or send events to /cv-events.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1.5">
            {groups.map((g) => (
              <span
                key={g.eventType}
                className={`chip ${SEVERITY_STYLES[g.severity]?.badge || "chip"}`}
              >
                {g.label} · {g.count}
              </span>
            ))}
          </div>
          <ul className="divide-y divide-ops-border/60">
            {recent.map((inc) => {
              const style = SEVERITY_STYLES[inc.severity] || SEVERITY_STYLES.compliant;
              return (
                <li
                  key={inc.id}
                  className="flex items-center justify-between gap-2 px-0.5 py-1.5"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />
                    <span className="truncate text-xs text-slate-300">
                      {incidentTypeLabel(inc)}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-slate-500">
                    {fmtTime(inc.timestamp)}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Panel>
  );
}
import { useEffect, useRef, useState } from "react";
import { getIncidents } from "../api.js";
import { RESOLVED_STYLE, SEVERITY_STYLES } from "../constants.js";
import { formatIncidentDescription, incidentTypeLabel } from "../formatters.js";
import { fmtTime } from "../format.js";
import Panel from "./Panel.jsx";

const MAX_ITEMS = 50;

function severityStyle(item) {
  if (item.eventType === "incident" && item.resolution_status === "resolved") {
    return RESOLVED_STYLE;
  }
  return SEVERITY_STYLES[item.severity] || SEVERITY_STYLES.warning;
}

// Converts a raw WS payload ({ event: "incident"|"emergency_drill", ... }) into
// a feed item shape.
function toFeedItem(raw) {
  const isDrill = raw.event === "emergency_drill";
  return {
    key: `${raw.event}-${isDrill ? raw.started_at : raw.incident_id}-${Date.now()}`,
    eventType: isDrill ? "drill" : "incident",
    type: raw.type,
    zone: raw.zone,
    severity: raw.severity,
    resolution_status: raw.resolution_status,
    timestamp: isDrill ? raw.started_at : raw.timestamp,
    started_at: raw.started_at,
    description: raw.description,
    unaccounted_count: raw.unaccounted_count,
  };
}

function FeedItem({ item }) {
  const style = severityStyle(item);
  const label =
    item.eventType === "drill" ? "Emergency drill" : incidentTypeLabel(item);
  const description = formatIncidentDescription(item);

  return (
    <li className="animate-[fadeIn_.25s_ease-out] border-b border-ops-border/60 px-3 py-2">
      <div className="flex items-start gap-2.5">
        <div className="relative mt-1">
          <span className={`block h-2.5 w-2.5 rounded-full ${style.dot}`} />
          {item.severity === "critical" && (
            <span
              className={`absolute -inset-1 animate-ping rounded-full opacity-30 ${style.dot}`}
            />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate text-xs font-semibold text-slate-100">{label}</span>
            <span className="shrink-0 font-mono text-[10px] text-slate-500">
              {fmtTime(item.timestamp)}
            </span>
          </div>
          <div className="mt-0.5 flex items-center justify-between gap-2">
            <span className="truncate text-[11px] text-slate-400">{item.zone}</span>
            <span className={style.badge}>
              <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
              {item.severity}
              {item.resolution_status === "resolved" ? " · resolved" : ""}
            </span>
          </div>
          {item.unaccounted_count ? (
            <p className="mt-1 truncate text-[11px] text-slate-500">
              {item.unaccounted_count} worker(s) unaccounted in {item.zone}
            </p>
          ) : (
            description && (
              <p className="mt-1 truncate text-[11px] text-slate-500">{description}</p>
            )
          )}
        </div>
      </div>
    </li>
  );
}

export default function IncidentFeed({ alert, maxItems = MAX_ITEMS, compact = false }) {
  const [items, setItems] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    getIncidents()
      .then((list) => {
        const recent = (Array.isArray(list) ? list : [])
          .slice(0, maxItems)
          .map((inc) => ({
            key: `seed-${inc.id}`,
            eventType: "incident",
            ...inc,
          }));
        setItems((prev) => [...recent, ...prev]);
      })
      .catch(() => {
        /* backend not reachable yet; WS will catch up */
      });
  }, [maxItems]);

  useEffect(() => {
    if (!alert) return;
    const item = toFeedItem(alert);
    setItems((prev) => [item, ...prev.filter((p) => p.key !== item.key)].slice(0, maxItems));
  }, [alert, maxItems]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [items.length]);

  return (
    <Panel
      title="Live Incident Feed"
      className="h-full"
      right={
        <span className="text-[10px] text-slate-500">
          {items.length} event(s)
        </span>
      }
    >
      <div
        ref={scrollRef}
        className={compact ? "max-h-56 overflow-y-auto" : "h-full overflow-y-auto"}
      >
        {items.length === 0 ? (
          <div className="flex h-full items-center justify-center px-4 text-center text-xs text-slate-500">
            No alerts yet — watching /ws/alerts…
          </div>
        ) : (
          <ul>
            {items.map((item) => (
              <FeedItem key={item.key} item={item} />
            ))}
          </ul>
        )}
      </div>
    </Panel>
  );
}
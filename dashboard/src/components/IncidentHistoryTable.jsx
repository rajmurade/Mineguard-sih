import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { evidenceUrl, getIncident, getIncidents, markIncidentResolved } from "../api.js";
import {
  INCIDENT_TYPE_LABELS,
  RESOLVED_STYLE,
  SEVERITIES,
  SEVERITY_STYLES,
} from "../constants.js";
import { formatIncidentDescription, incidentTypeLabel } from "../formatters.js";
import { fmtDateTime, fmtTime } from "../format.js";
import Panel from "./Panel.jsx";

function EvidenceImage({ url, alt, className }) {
  const [broken, setBroken] = useState(false);
  if (!url || broken) return null;
  return (
    <img
      src={url}
      alt={alt}
      className={className}
      onError={() => setBroken(true)}
      loading="lazy"
    />
  );
}

function SeverityBadge({ severity, status }) {
  const style =
    status === "resolved" ? RESOLVED_STYLE : SEVERITY_STYLES[severity] || SEVERITY_STYLES.warning;
  return (
    <span className={style.badge}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {severity}
      {status === "resolved" ? " · resolved" : ""}
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    open: "chip border-slate-500/40 bg-slate-700/30 text-slate-300",
    acknowledged: "chip border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
    resolved: "chip border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  };
  return <span className={map[status] || map.open}>{status}</span>;
}

export default function IncidentHistoryTable() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState({ severity: "", type: "", from: "", to: "" });
  const [selectedId, setSelectedId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const list = await getIncidents();
      setIncidents(Array.isArray(list) ? list : []);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const fromTs = filter.from ? new Date(`${filter.from}T00:00:00`).getTime() : null;
    const toTs = filter.to ? new Date(`${filter.to}T23:59:59.999`).getTime() : null;
    return incidents.filter((inc) => {
      if (filter.severity && inc.severity !== filter.severity) return false;
      if (filter.type && inc.type !== filter.type) return false;
      const ts = inc.timestamp ? new Date(inc.timestamp).getTime() : null;
      if (fromTs && (!ts || ts < fromTs)) return false;
      if (toTs && (!ts || ts > toTs)) return false;
      return true;
    });
  }, [incidents, filter]);

  const clearFilters = () => setFilter({ severity: "", type: "", from: "", to: "" });

  const openIncident = (id) => setSelectedId(id);

  return (
    <>
      <Panel
        title="Incident History"
        right={
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-slate-500">
              {loading ? "loading…" : `${filtered.length} / ${incidents.length}`}
            </span>
            <button onClick={load} className="btn-ghost !px-2 !py-1 text-[10px]" title="Refresh">
              ⟳
            </button>
          </div>
        }
      >
        <div className="border-b border-ops-border p-3">
          <div className="grid grid-cols-2 items-end gap-2 md:grid-cols-5">
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Severity</span>
              <select
                className="input w-full"
                value={filter.severity}
                onChange={(e) => setFilter({ ...filter, severity: e.target.value })}
              >
                <option value="">All</option>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">Type</span>
              <select
                className="input w-full"
                value={filter.type}
                onChange={(e) => setFilter({ ...filter, type: e.target.value })}
              >
                <option value="">All</option>
                {Object.entries(INCIDENT_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">From</span>
              <input
                type="date"
                className="input w-full"
                value={filter.from}
                onChange={(e) => setFilter({ ...filter, from: e.target.value })}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-[10px] uppercase tracking-wider text-slate-500">To</span>
              <input
                type="date"
                className="input w-full"
                value={filter.to}
                onChange={(e) => setFilter({ ...filter, to: e.target.value })}
              />
            </label>
            <div className="flex gap-2">
              <button onClick={clearFilters} className="btn-ghost flex-1">
                Clear
              </button>
            </div>
          </div>
        </div>

        <div className="max-h-[560px] overflow-auto">
          <table className="w-full text-left">
            <thead className="sticky top-0 z-10 bg-ops-rail">
              <tr>
                <th className="th-sort">ID</th>
                <th className="th-sort">Time</th>
                <th className="th-sort">Type</th>
                <th className="th-sort">Severity</th>
                <th className="th-sort">Zone</th>
                <th className="th-sort">Worker</th>
                <th className="th-sort">Evidence</th>
                <th className="th-sort">Status</th>
                <th className="th-sort" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ops-border/50">
              {error && (
                <tr>
                  <td colSpan={9} className="td text-center text-red-400">
                    Backend unreachable — could not load incidents.
                  </td>
                </tr>
              )}
              {!error && filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="td text-center text-slate-500">
                    No incidents match the current filters.
                  </td>
                </tr>
              )}
              {filtered.map((inc) => (
                <tr
                  key={inc.id}
                  onClick={() => openIncident(inc.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      openIncident(inc.id);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`View incident ${inc.id}`}
                  aria-haspopup="dialog"
                  className="cursor-pointer hover:bg-slate-800/40 focus-visible:bg-slate-800/40 focus-visible:outline-none"
                >
                  <td className="td font-mono text-slate-400">#{inc.id}</td>
                  <td className="td font-mono text-[11px]">{fmtDateTime(inc.timestamp)}</td>
                  <td className="td text-slate-200">
                    {incidentTypeLabel(inc)}
                  </td>
                  <td className="td">
                    <SeverityBadge severity={inc.severity} status={inc.resolution_status} />
                  </td>
                  <td className="td">{inc.zone}</td>
                  <td className="td font-mono text-[11px]">{inc.worker_id ?? "—"}</td>
                  <td className="td">
                    {inc.evidence_frame_path ? (
                      <EvidenceImage
                        url={evidenceUrl(inc.id)}
                        alt="evidence"
                        className="h-9 w-12 rounded object-cover ring-1 ring-ops-border"
                      />
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="td">
                    <StatusBadge status={inc.resolution_status} />
                  </td>
                  <td className="td">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        openIncident(inc.id);
                      }}
                      className="btn-ghost !px-2 !py-1 text-[10px] text-cyan-300"
                      aria-label={`View incident ${inc.id} details`}
                    >
                      View →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {selectedId !== null &&
        createPortal(
          <IncidentDetail
            incidentId={selectedId}
            onClose={() => setSelectedId(null)}
            onResolved={(updated) => {
              setIncidents((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
            }}
          />,
          document.body
        )}
    </>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-0.5 text-xs text-slate-200">{children}</div>
    </div>
  );
}

function IncidentDetail({ incidentId, onClose, onResolved }) {
  const [incident, setIncident] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);

  useEffect(() => {
    let alive = true;
    getIncident(incidentId)
      .then((data) => alive && setIncident(data))
      .catch(() => alive && setLoadError(true));
    return () => {
      alive = false;
    };
  }, [incidentId]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, incidentId]);

  const markResolved = async () => {
    setSaving(true);
    setSaveError(false);
    try {
      const updated = await markIncidentResolved(incidentId);
      setIncident(updated);
      onResolved(updated);
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
    }
  };

  const resolved = incident?.resolution_status === "resolved";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      style={{ position: "fixed", inset: 0, zIndex: 50 }}
      role="dialog"
      aria-modal="true"
      aria-label={`Incident ${incidentId} details`}
      onClick={onClose}
    >
      <div
        className="panel w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {loadError ? (
          <div className="p-6 text-sm text-red-400">
            Could not load incident #{incidentId}.
          </div>
        ) : !incident ? (
          <div className="p-6 text-sm text-slate-400">Loading…</div>
        ) : (
          <>
            <div className="flex items-start justify-between border-b border-ops-border p-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">
                  {incidentTypeLabel(incident)}{" "}
                  <span className="font-mono text-slate-500">#{incident.id}</span>
                </h3>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={incident.severity} status={incident.resolution_status} />
                  <StatusBadge status={incident.resolution_status} />
                  <span className="chip border-slate-600/40 bg-slate-800/40 text-slate-300">
                    {incident.zone}
                  </span>
                </div>
              </div>
              <button onClick={onClose} className="btn-ghost !px-2 !py-1" title="Close (Esc)">
                ✕
              </button>
            </div>

            <div className="grid gap-4 p-4 md:grid-cols-2">
              <div className="space-y-3">
                <Field label="Timestamp">{fmtDateTime(incident.timestamp)}</Field>
                <Field label="Type">{incident.type}</Field>
                <Field label="Severity">{incident.severity}</Field>
                <Field label="Zone">{incident.zone}</Field>
                <Field label="Worker ID">{incident.worker_id ?? "—"}</Field>
                <Field label="Requires attention">
                  <span className={resolved ? "text-emerald-400" : "text-amber-400"}>
                    {resolved ? "Resolved" : "Open"}
                  </span>
                </Field>
              </div>

              <div className="space-y-3">
                <Field label="Description">
                  <p className="text-slate-300">
                    {formatIncidentDescription(incident) || incident.description || "—"}
                  </p>
                </Field>
                <Field label="Evidence (CV capture)">
                  {incident.evidence_frame_path ? (
                    <EvidenceImage
                      url={evidenceUrl(incident.id)}
                      alt="Evidence frame"
                      className="mt-1 w-full max-h-64 rounded-lg object-contain bg-black ring-1 ring-ops-border"
                    />
                  ) : (
                    <span className="text-slate-500">No saved frame for this incident.</span>
                  )}
                </Field>
                {!incident.evidence_frame_path && (
                  <Field label="Evidence path on disk">
                    <span className="font-mono text-[10px] break-all text-slate-500">
                      {incident.evidence_frame_path ?? "—"}
                    </span>
                  </Field>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-ops-border p-4">
              {saveError ? (
                <span className="text-xs text-red-400">Could not update — try again.</span>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                {!resolved && (
                  <button
                    onClick={markResolved}
                    disabled={saving}
                    className="btn-primary"
                  >
                    {saving ? "Resolving…" : "✓ Mark resolved"}
                  </button>
                )}
                <button onClick={onClose} className="btn-ghost">
                  Close
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
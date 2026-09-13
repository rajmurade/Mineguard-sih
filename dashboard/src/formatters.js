// Display-only helpers for incident labels + descriptions. The backend stores a
// single `description` string such as
//   "aqi_high (value=1000.0): aqi_high: 1000.0 triggered critical threshold"
// or
//   "no_helmet (confidence=0.8): no_helmet confirmed: 3/3 detections within 5.0s window"
// We parse that string to render concrete metric values / confidence inline
// (e.g. "AQI 1000", "No helmet detected (confidence 80%)") without ever
// changing the stored value or the Compliance Engine.

import { INCIDENT_TYPE_LABELS, METRIC_BANDS } from "./constants.js";

// compliance event_type -> human-readable environmental metric.
const ENV_METRICS = {
  aqi_high: { metric: "AQI", unit: "", band: "aqi" },
  gas_high: { metric: "CO", unit: " ppm", band: "gas_level" },
  temp_high: { metric: "Temp", unit: "°C", band: "temperature" },
  noise_high: { metric: "Noise", unit: " dB", band: "noise_db" },
  dust_high: { metric: "Dust", unit: " mg/m³", band: "dust_pm" },
};

// compliance event_type -> operator-facing CV label.
export const CV_EVENT_LABELS = {
  no_helmet: "No helmet detected",
  no_vest: "No vest detected",
  restricted_zone_entry: "Restricted zone entry",
  proximity_risk: "Proximity risk",
  fire: "Fire detected",
  smoke: "Smoke detected",
  fall: "Worker fall detected",
};

// description -> { event_type, kind: "value"|"confidence", number, reason } or null.
export function parseIncidentDescription(description) {
  if (!description) return null;
  const m = String(description).match(
    /^([a-z_]+)\s+\((value|confidence)=(\d+(?:\.\d+)?)\):\s*(.*)$/
  );
  if (!m) return null;
  return {
    event_type: m[1],
    kind: m[2],
    number: Number(m[3]),
    reason: m[4],
  };
}

function formatNumber(n) {
  if (Number.isInteger(n)) return String(n);
  return String(Math.round(n * 100) / 100);
}

function confidencePct(n) {
  return Math.round(n * 100);
}

// "critical >500", "high ≥301" style threshold snippet for an environmental
// incident, derived from its severity band in METRIC_BANDS (mirrors rules.json).
function thresholdText(event_type, severity) {
  const info = ENV_METRICS[event_type];
  if (!info) return null;
  const bands = METRIC_BANDS[info.band] || [];
  const band = bands.find((b) => b.severity === severity);
  if (!band) return null;
  if (band === bands[bands.length - 1]) {
    const step = Number.isInteger(band.min) ? 1 : 0.1;
    return `${severity} >${formatNumber(band.min - step)}`;
  }
  return `${severity} ≥${formatNumber(band.min)}`;
}

// Label shown in list/feed rows: concrete metric+value for environmental
// incidents ("AQI 1000"), CV detection + confidence for PPE detections
// ("No helmet detected (confidence 80%)"), otherwise the plain type label.
export function incidentTypeLabel(incident) {
  const parsed = incident?.description ? parseIncidentDescription(incident.description) : null;

  if (incident?.type === "environmental") {
    if (parsed && ENV_METRICS[parsed.event_type]) {
      const info = ENV_METRICS[parsed.event_type];
      return `${info.metric} ${formatNumber(parsed.number)}${info.unit}`;
    }
    return INCIDENT_TYPE_LABELS.environmental || "Environmental";
  }

  if (parsed && parsed.kind === "confidence" && CV_EVENT_LABELS[parsed.event_type]) {
    return `${CV_EVENT_LABELS[parsed.event_type]} (confidence ${confidencePct(parsed.number)}%)`;
  }

  return INCIDENT_TYPE_LABELS[incident?.type] || incident?.type || "Incident";
}

// Friendly version of the stored description for the detail modal and feed:
//   "AQI reached 1000 (threshold: critical >500)"
//   "No helmet detected (confidence 80%)"
// Falls back to the raw description when it can't be parsed.
export function formatIncidentDescription(incident) {
  const parsed = incident?.description ? parseIncidentDescription(incident.description) : null;
  if (!parsed) return incident?.description || null;

  if (ENV_METRICS[parsed.event_type]) {
    const info = ENV_METRICS[parsed.event_type];
    const threshold = thresholdText(parsed.event_type, incident?.severity);
    const suffix = threshold ? ` (threshold: ${threshold})` : "";
    return `${info.metric} reached ${formatNumber(parsed.number)}${info.unit}${suffix}`;
  }

  if (parsed.kind === "confidence" && CV_EVENT_LABELS[parsed.event_type]) {
    return `${CV_EVENT_LABELS[parsed.event_type]} (confidence ${confidencePct(parsed.number)}%)`;
  }

  return incident?.description || null;
}
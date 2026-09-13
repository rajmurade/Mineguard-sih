// Severity taxonomy shared across the dashboard (matches app/enums.py + the
// compliance rules). Classes are literal strings so Tailwind keeps them.

export const SEVERITIES = ["compliant", "warning", "high", "critical"];

export const SEVERITY_STYLES = {
  compliant: {
    dot: "bg-emerald-400",
    bar: "bg-emerald-500",
    hex: "#34d399",
    badge: "chip border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  },
  warning: {
    dot: "bg-amber-400",
    bar: "bg-amber-500",
    hex: "#fbbf24",
    badge: "chip border-amber-500/40 bg-amber-500/10 text-amber-300",
  },
  high: {
    dot: "bg-orange-400",
    bar: "bg-orange-500",
    hex: "#fb923c",
    badge: "chip border-orange-500/40 bg-orange-500/10 text-orange-300",
  },
  critical: {
    dot: "bg-red-500",
    bar: "bg-red-600",
    hex: "#f87171",
    badge: "chip border-red-500/40 bg-red-500/10 text-red-300",
  },
};

export const RESOLVED_STYLE = {
  dot: "bg-emerald-400",
  bar: "bg-emerald-500",
  hex: "#34d399",
  badge: "chip border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
};

export const INCIDENT_TYPE_LABELS = {
  ppe_violation: "PPE Violation",
  proximity_risk: "Proximity Risk",
  fire_smoke: "Fire / Smoke",
  environmental: "Environmental",
  unauthorized_zone: "Unauthorized Zone",
  fall: "Fall",
};

export const WORKER_SEVERITY_MAP = {
  compliant: "compliant",
  warning: "warning",
  high: "high",
  critical: "critical",
};

// Bands are ascending inclusive ranges keyed at their minimum; the last band
// is the catch-all. Mirrors compliance/rules.json.
export const METRIC_BANDS = {
  aqi: [
    { min: 0, severity: "compliant" },
    { min: 150, severity: "warning" },
    { min: 301, severity: "high" },
    { min: 501, severity: "critical" },
  ],
  gas_level: [
    { min: 0, severity: "compliant" },
    { min: 50, severity: "warning" },
    { min: 151, severity: "high" },
    { min: 301, severity: "critical" },
  ],
  temperature: [
    { min: 0, severity: "compliant" },
    { min: 40, severity: "warning" },
    { min: 46, severity: "high" },
    { min: 51, severity: "critical" },
  ],
  noise_db: [
    { min: 0, severity: "compliant" },
    { min: 85, severity: "warning" },
    { min: 93, severity: "high" },
    { min: 101, severity: "critical" },
  ],
  dust_pm: [
    { min: 0, severity: "compliant" },
    { min: 2.0, severity: "warning" },
    { min: 3.6, severity: "high" },
    { min: 5.1, severity: "critical" },
  ],
};

// Display scale cap per metric (drives the gauge arc), not a safety threshold.
export const METRIC_MAX = {
  aqi: 500,
  gas_level: 400,
  temperature: 60,
  noise_db: 120,
  dust_pm: 8,
};

export const METRIC_UNITS = {
  aqi: "AQI",
  gas_level: "CO ppm",
  temperature: "°C",
  noise_db: "dB",
  dust_pm: "mg/m³",
};

// Approximate clockwise order used when stacking severity bars.
export const SEVERITY_ORDER_BARS = ["critical", "high", "warning"];

export function classifyValue(bands, value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "na";
  let severity = bands[0].severity;
  for (const band of bands) {
    if (value >= band.min) severity = band.severity;
    else break;
  }
  return severity;
}
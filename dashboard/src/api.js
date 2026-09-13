// Thin fetch helpers for the MineGuard REST API. All paths are relative so the
// same code works served from /dashboard (prod) and through the Vite proxy (dev).

async function getJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

export const getActiveWorkers = () => getJson("/workers/active");
export const getDashboardSummary = () => getJson("/dashboard/summary");
export const getIncidents = () => getJson("/incidents");
export const getIncident = (id) => getJson(`/incidents/${id}`);
export const getLatestReadings = () => getJson("/environmental-readings/latest");
export const getReadings = (zone, limit = 200) =>
  getJson(
    `/environmental-readings?zone=${encodeURIComponent(zone)}&limit=${limit}`
  );

export const evidenceUrl = (id) => `/incidents/${id}/evidence`;
export const reportUrl = (format, range) =>
  `/reports/export?format=${format}&range=${range}`;

export async function markIncidentResolved(id) {
  const res = await fetch(`/incidents/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolution_status: "resolved" }),
  });
  if (!res.ok) throw new Error(`PUT /incidents/${id} -> ${res.status}`);
  return res.json();
}

export async function sendEnvironmentalReading(payload) {
  const res = await fetch("/environmental-readings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`POST /environmental-readings -> ${res.status}`);
  return res.json();
}

export async function startEmergencyDrill(zone) {
  const res = await fetch("/emergency-drill/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zone }),
  });
  if (!res.ok) throw new Error(`POST /emergency-drill/start -> ${res.status}`);
  return res.json();
}
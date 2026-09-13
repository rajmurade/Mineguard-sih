# MineGuard

AI-powered mine safety, environmental, and compliance monitoring system — built for Smart India Hackathon 2026.

MineGuard watches mine operations through CCTV/webcam feeds and environmental sensor data, automatically detects safety violations and hazardous conditions, evaluates their severity, and alerts the right people in real time — so operators aren't stuck manually watching dozens of camera feeds.

**Stack:** Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · WebSockets · OpenCV · Ultralytics YOLOv8 · React · Tailwind · Recharts

---

## What it does

| Category | Detects |
|---|---|
| **PPE / Worker safety** | Helmet / no helmet, vest / no vest |
| **Unsafe behavior** | Worker–vehicle proximity risk |
| **Environmental hazards** | High AQI, gas levels, temperature, noise, dust/PM |
| **Accountability** | Unaccounted workers during an emergency drill |

Every detection — whether from a camera or a sensor — flows through the same **Compliance Engine**, which decides severity (compliant / warning / high / critical) and routes an alert to the right people, in real time, over WebSockets.

---

## Architecture

```
CCTV / Webcam  ──┐
                 ├──► CV Pipeline (YOLOv8 + OpenCV) ──┐
Environmental    │                                     ├──► Compliance Engine ──► Incident + Alert (WS)
Sensors / Sim ───┘                                     │                              │
                                                        │                              ▼
                                                        └──────────────────────► Operator Dashboard
```

- **Compliance Engine** (`compliance/`) — standalone, pure-Python decision module. No FastAPI or DB dependency, fully unit-tested, rules live in an editable JSON config.
- **CV Pipeline** (`cv_pipeline/`) — turns live webcam or recorded video into compliance events using two pretrained YOLOv8 models (no training required).
- **Backend** (`app/`) — FastAPI + PostgreSQL, REST + WebSocket API, evidence storage, PDF/XLSX reporting.
- **Operator Dashboard** (`dashboard/`) — the main safety operations center: live CCTV feed, real-time alerts, environmental gauges, incident history, reports, and an embedded demo-control panel.
- **Admin Simulator** (`admin/`) — a separate, minimal demo tool for triggering simulated environmental readings and emergency drills without real sensors.

---

## Quick start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000 — interactive docs at `/docs`
- Operator Dashboard: http://localhost:8000/dashboard
- Admin Simulator: http://localhost:8000/admin-simulator
- DB: `postgresql+psycopg://mineguard:mineguard@localhost:5432/mineguard`

The dashboard and admin simulator are pre-built React apps — if you change their source, rebuild before restarting:

```bash
cd dashboard && npm install && npm run build      # base path: /dashboard/
cd admin && npm install && npm run build -- --base=/admin-simulator/
```

### Seed data

```bash
docker compose exec api python -m app.seed
```

Seeds 2 zones and sample environmental readings. **Fake worker names are intentionally not seeded** — worker presence on the dashboard reflects live camera detection instead (see below), not a placeholder registry.

### Manual run (without Docker)

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
pip install -r requirements-cv.txt                  # optional: CV pipeline
docker compose up -d db                             # Postgres only
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Running the computer-vision pipeline

Install the extra dependencies once:

```bash
pip install -r requirements-cv.txt   # opencv-python, ultralytics, huggingface-hub, requests
```

The first run downloads two pretrained models (no training needed):

1. **PPE detection** — `killuminati1/construction-ppe-yolov8` (Hugging Face) — Hard_hat, No-Helmet, Vest, No-Vest, Worker
2. **Proximity/vehicle detection** — stock `yolov8n.pt` (COCO) — person, car, truck

```bash
# Live webcam, streamed to the dashboard's live feed panel
python -m cv_pipeline.run_live --source 0 --api-url http://localhost:8000 \
  --zone "Zone A - Tunnel 1" --stream-url http://localhost:8000

# Recorded video file
python -m cv_pipeline.run_recorded --file clip.mp4 --api-url http://localhost:8000 \
  --zone "Zone A - Tunnel 1" --stream-url http://localhost:8000 --loop --output out.mp4
```

**Event flow:** detections → `cv_pipeline/events.py` maps them to compliance events (`no_helmet`, `no_vest`, `proximity_risk`) → an evidence JPEG is saved under `evidence/<event>/…` → the event is POSTed to `/cv-events` → the Compliance Engine debounces it (3 detections within 5s) → an `Incident` is created with the evidence path attached → broadcast over `/ws/alerts` if severity ≥ high.

> **Note:** proximity risk currently uses pixel-distance between bounding boxes as a demo proxy. Real-world distance would require a ground-plane camera calibration — noted directly in `cv_pipeline/proximity.py`.

---

## Operator Dashboard (`/dashboard`)

The main safety operations center. Sidebar navigation across four sections:

- **Overview** — live CCTV feed (annotated MJPEG stream) with a real-time worker count from active camera detections, environmental gauges, live incident feed, incidents-by-type breakdown, and an embedded **Demo Controls** panel so environmental scenarios and emergency drills can be triggered without leaving the dashboard.
- **Incidents** — full incident history, filterable by severity/type/date; clicking a row opens full detail including the CV evidence image and a "mark resolved" action; incident trend chart.
- **Environment** — per-zone environmental gauges and multi-zone metric trend charts.
- **Reports** — download daily/weekly PDF or Excel summaries.

Live data only — no seeded placeholder names. Worker presence reflects what the active camera currently sees, not a static registry.

---

## Admin Simulation Panel (`/admin-simulator`)

A separate, minimal tool for demoing the alert pipeline without real sensors — send a simulated environmental reading or trigger an emergency drill and watch the full pipeline (Compliance Engine → Incident → real-time WebSocket alert) fire, live. Kept intentionally isolated from the operator dashboard so it can be built/iterated on independently.

---

## Key endpoints

| Endpoint | Notes |
|---|---|
| `POST /incidents` | Create an incident (severity supplied by caller). Broadcasts over WS when severity ≥ high. |
| `GET /incidents?status=open&severity=critical` | Filterable by status, severity, type, zone. |
| `GET /incidents/{id}/evidence` | Serves the saved CV evidence JPEG (404 if none). |
| `GET /workers/active` | Workers currently inside the mine (registry-based; requires real entry/exit events). |
| `POST /environmental-readings` | Sensor/simulated payload → evaluated via Compliance Engine → incidents + WS broadcast. |
| `POST /cv-events` | CV detection event → debounce-confirmed → incident + evidence + WS broadcast. |
| `POST /cv-stream` | Raw JPEG push from an active CV pipeline run (`--stream-url`). |
| `GET /cv-stream` | MJPEG stream of annotated frames — rendered by the dashboard's live feed panel. |
| `GET /cv-stream/status` | `{active, source, frame_count, current_worker_count, last_updated, stale}` |
| `POST /emergency-drill/start` | Returns workers still inside a zone as `unaccounted_workers`; broadcasts CRITICAL over WS. |
| `GET /reports/export?format=pdf\|xlsx&range=daily\|weekly` | Downloads a summary report. |
| `GET /dashboard/summary` | Active worker count, open incidents by severity, latest readings per zone. |
| `WS /ws/alerts` | Real-time incident broadcasts (severity ≥ high). |

---

## Project layout

```
app/                    FastAPI backend
  main.py               entrypoint
  models/                Worker, WorkerEntryExit, Incident, AlertLog, EnvironmentalReading
  routers/                workers, incidents, environmental, dashboard, ws, cv_events, cv_stream, reports, emergency_drill
  services/               compliance wiring, presence, alerts (WS), reports (PDF/XLSX), frame streaming
compliance/             standalone rules/severity/debounce/routing engine
cv_pipeline/            webcam/video capture → detection → compliance events
admin/                  React admin simulator      (→ admin/dist)
dashboard/              React operator dashboard    (→ dashboard/dist)
alembic/                DB migrations
tests/                  110+ tests across compliance, CV pipeline, backend, reports
docker-compose.yml      postgres + api
```

---

## Testing

```bash
pytest
```

110+ tests covering: Compliance Engine severity tiers and debounce logic, CV pipeline components (video source, detector, proximity, event mapping, ingestion), backend endpoints (incidents, environmental, `/cv-events`, `/cv-stream`, reports), and frontend/backend mount integration.

---

## Known limitations (by design, for this MVP)

- **Proximity risk** uses pixel-distance as a proxy for real-world distance — production use would need ground-plane camera calibration.
- **PPE detection** uses a pretrained public model rather than one fine-tuned on mine-specific footage — accuracy may vary with lighting/camera angle.
- **Worker count** from live detection may double-count a single person if both detection models flag them in the same frame — a known, documented trade-off for this MVP.
- **Fire/smoke and fall detection** were scoped in the original design but deprioritized for this build in favor of a solid, reliable PPE + environmental + proximity pipeline.

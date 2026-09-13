# MineGuard

AI-based mine safety monitoring system — backend foundation.

Stack: Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, WebSockets.

## Compliance Engine

Standalone, pure-Python decision module (`compliance/`) — no FastAPI/DB
dependency. Entry point:

```python
from compliance import evaluate_event

decision = evaluate_event({
    "source": "environmental",          # "cv" | "environmental"
    "event_type": "aqi_high",           # see compliance/models.py
    "zone": "Zone A - Tunnel 1",
    "worker_id": None,
    "value": 320,                        # sensor reading (env events)
    "confidence": None,                  # YOLO score (cv events)
    "timestamp": "2026-01-01T08:00:00",
})
# decision.should_create_incident, .severity, .alert_recipients, .escalate_external, .reason
```

- **Rules are an editable JSON config** (`compliance/rules.json`) — threshold
  bands, CV severities, confidence minimums, debounce window, and combo rules.
  Tune without touching logic. `compliance/rules.load_rules_from_path()` lets
  you point the engine at your own config file.
- **CV debounce**: N detections (default 3) within a 5s window per
  (event_type, zone, worker_id) before an incident is raised. Fires once per
  streak (rising edge) — keep-alive detections don't flood incidents; it
  re-arms only after the window slides empty.
- **Routing**: warning → worker + local supervisor; high → safety officer +
  site manager; critical → same as high + `escalate_external=True`.

Tests: `pytest` — 76 tests: compliance unit tests (severity tiers, debounce,
routing), CV pipeline (VideoSource, Detector, ProximityAnalyzer, events,
ingester, end-to-end with real OpenCV codecs), and `/cv-events` backend smoke
tests on SQLite.

## Computer-Vision pipeline

Live/recorded camera ingestion that turns detections into compliance events and
pushes them to the backend through the same Compliance Engine used by sensors.

```
cv_pipeline/
  video_source.py    VideoSource: webcam (int), rtsp/http(s) stream, or file
  detector.py        Detector: PPE model (HF construction-ppe-yolov8) + stock
                     yolov8n COCO; mode both|alternate; lazy weight loading
  proximity.py       ProximityAnalyzer: person/Worker near car/truck (pixel
                     distance; real meters need a ground-plane calibration)
  events.py          detections -> compliance event dicts (no_helmet, no_vest,
                     proximity_risk with worker+heavy_vehicle combo)
  ingest.py          EventIngester / HttpEventIngester -> POST /cv-events
  pipeline.py        CVPipeline: main frame loop, evidence JPEGs, bbox drawing,
                     FPS logging, optional imshow / annotated output video
  runners.py         shared argparse for both entry points
  run_live.py        live capture       python -m cv_pipeline.run_live --source 0
  run_recorded.py    file processing    python -m cv_pipeline.run_recorded --file clip.mp4
```

Install the extra deps once:

```bash
pip install -r requirements-cv.txt     # opencv-python, ultralytics, huggingface-hub, requests
```

First run downloads the PPE weights from Hugging Face and `yolov8n.pt` (cached COCO model from Ultralytics). Then:

```bash
# webcam (page / RTSP works the same way)
python -m cv_pipeline.run_live --source 0 --api-url http://localhost:8000 --zone "Zone A - Tunnel 1"

# recorded file, looping, annotated output video
python -m cv_pipeline.run_recorded --file demo.mp4 --loop --output out.mp4 --show
```

Event flow: model detections → `cv_pipeline/events.py` (No-Helmet → `no_helmet`,
No-Vest → `no_vest`, person/Worker near car/truck → `proximity_risk`) → the
pipeline saves a JPEG evidence frame under `evidence/<event>/…` and POSTs the
event to `POST /cv-events`. The backend runs it through `evaluate_event()`, its
debouncer confirms it (3 detections in 5s), creates an `Incident` (with the
evidence frame path), and broadcasts over `/ws/alerts` when severity ≥ high.
Combos with `["worker","heavy_vehicle"]` escalate `proximity_risk` to CRITICAL.

## Operator Dashboard (`/dashboard`)

The main operator-facing safety operations center, built in React + Tailwind +
Recharts. It is served from `/dashboard` (kept separate from the demo's
`/admin-simulator` mount) and shows:

- **Top bar** — system status + WebSocket link indicator, live clock, active
  worker count, open-incident severity chips.
- **Live CCTV Feed** — renders the annotated MJPEG stream via a plain
  `<img src="/cv-stream">`. It needs the CV pipeline actively pushing frames:
  launch a runner with `--stream-url http://localhost:8000`
  (e.g. `python -m cv_pipeline.run_live --source 0 --stream-url http://localhost:8000`
  or `python -m cv_pipeline.run_recorded --file clip.mp4 --stream-url http://localhost:8000`).
  Without a running publisher the panel shows a "No active feed" placeholder
  (it polls `GET /cv-stream/status`).
- **Live Incident Feed** — subscribes to `/ws/alerts` (with automatic
  reconnect showing a connection-status indicator), auto-scrolling, color coded
  green (compliant/resolved) / yellow (warning) / orange (high) / red (critical).
- **Environmental Conditions** — per-zone gauge cards for AQI, CO, temp, noise,
  dust, color-coded on the same severity bands as the Compliance Engine, plus an
  AQI/CO trend for the last 60 min (Recharts).
- **Incident Trends** — incidents per day over 14 days, stacked by severity.
- **Workers On Site** — `GET /workers/active` list with role breakdown.
- **Incident History** — the real incident table, filterable by severity, type
  and date range; clicking a row opens a detail view that renders the CV
  evidence JPEG (served by `GET /incidents/{id}/evidence`) and a "Mark resolved"
  button (`PUT /incidents/{id}`).
- **Reports tab** — downloads daily/weekly PDF (ReportLab) or XLSX (OpenPyXL)
  from `GET /reports/export?format=pdf|xlsx&range=daily|weekly`.

Build it once, then the backend serves it:

```bash
cd dashboard
npm install
npm run build           # base is /dashboard/ (see vite.config.js)
```

Dev iteration: `cd dashboard && npm run dev` (Vite on :5138 proxies API and
`/ws` to the backend). Module-per-panel: `TopBar.jsx`, `IncidentFeed.jsx`,
`EnvironmentalPanel.jsx` (+ `Gauge.jsx`), `TrendsPanel.jsx`,
`WorkerStatusPanel.jsx`, `IncidentHistoryTable.jsx`, `ReportsTab.jsx`.

## Admin Simulation Panel (demo-only)

A React page (`/admin-simulator`) to demo the loop: send environmental readings
or trigger emergency drills, watch incidents get created in real time.

**Build it once:**

```bash
cd admin
npm install
npm run build -- --base=/admin-simulator/
```

The backend serves the built app at `http://localhost:8000/admin-simulator`
(if `admin/dist` is missing, the route returns a "not built" message instead of
crashing). For live dev iteration, use `cd admin && npm run dev` — Vite proxies
API + WebSocket to `localhost:8000`.

What it does:

- **Send Reading** → `POST /environmental-readings`. The backend now evaluates
  the reading through the Compliance Engine (`app/services/compliance.py`): each
  metric is turned into a compliance event; when `should_create_incident` is
  true an `Incident` is created and broadcast over `/ws/alerts`
  (severity ≥ high). The response includes the per-metric evaluations.
- **Trigger Emergency Drill** → `POST /emergency-drill/start`
  (`app/routers/emergency_drill.py`). Cross-references `WorkerEntryExit` and
  returns workers still inside the selected zone (last event is an `entry` with
  no later `exit`) as `unaccounted_workers`, and broadcasts a CRITICAL system
  event over the WebSocket. Returns immediately (demo mode).
- **Live feed** keeps the last 10 events: each reading's evaluations plus
  incident/drill broadcasts received over the WebSocket.

## Project layout

```
app/
  main.py               FastAPI entrypoint
  config.py             pydantic-settings
  database.py           engine, session, Base, get_db
  enums.py              shared Enum values
  models/               SQLAlchemy models (Worker, WorkerEntryExit, Incident,
                        AlertLog, EnvironmentalReading)
  schemas/              Pydantic request/response models
  routers/              workers, incidents, environmental, dashboard, ws, cv_events, reports
  services/presence.py  active-worker helpers
  services/compliance.py  process_reading + materialize_incident + INCIDENT_TYPE_MAP
  services/alerts.py    WS broadcast helpers (threshold >= high)
  services/reports.py   PDF (ReportLab) + XLSX (OpenPyXL) report generation
  websocket_manager.py  WS connection manager + broadcast
  seed.py               seed 10 workers + 2 zones
compliance/             pure-Python decision engine (rules, debounce, routing)
cv_pipeline/            camera capture -> detections -> events (see CV section)
admin/                  React admin simulator (built -> admin/dist)
dashboard/              React operator dashboard (built -> dashboard/dist)
alembic/                Alembic migration environment
docker-compose.yml      postgres + api
```

## Quick start (Docker)

```bash
docker compose up --build
```

API: http://localhost:8000 — OpenAPI docs at http://localhost:8000/docs
DB: `postgresql+psycopg://mineguard:mineguard@localhost:5432/mineguard`

Seed data (10 workers, 2 zones, entry/exit + environmental readings) is applied
automatically on API container startup.

### Manual run

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -r requirements-cv.txt  # optional: computer-vision pipeline
docker compose up -d db            # PostgreSQL only
alembic upgrade head               # apply migrations (or: python -m app.seed)
uvicorn app.main:app --reload
```

## Alembic

Generate an initial migration from models:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

## Key endpoints

| Endpoint | Notes |
|---|---|
| `POST /incidents` | Creates an incident; `severity` is passed in by the caller (Compliance Engine integration later). Broadcasts over WS when severity `>= high`. |
| `GET /incidents?status=open&severity=critical` | Filterable by status, severity, type, zone. |
| `GET /incidents/{id}/evidence` | Serves the saved CV evidence JPEG (404 if none / file gone). |
| `GET /workers/active` | Workers currently inside the mine (derived from latest entry/exit). |
| `POST /environmental-readings` | Accepts simulated or real sensor payloads. Evaluated via the Compliance Engine → creates incidents + WS broadcasts. |
| `POST /cv-events` | CV detection event (no_helmet/no_vest/proximity_risk/fire/…). Runs `evaluate_event()` → incident (after debounce confirm) + evidence frame path + WS broadcast when severity `>= high`. |
| `POST /cv-stream` | Raw-JPEG push from a running CV pipeline (`FramePublisher`, opt-in via `--stream-url`). Feeds the dashboard's live feed buffer. |
| `GET /cv-stream` | MJPEG (`multipart/x-mixed-replace`) stream of the latest *annotated* frames — the dashboard renders it via a plain `<img src="/cv-stream">`. Empty until a pipeline is actively pushing. |
| `GET /cv-stream/status` | `{active, source, frame_count, last_updated, stale}` for the Live Feed panel to switch between the live image and the "no active feed" placeholder. |
| `POST /emergency-drill/start` | Demo drill: returns workers still inside `zone` as `unaccounted_workers`, broadcasts a CRITICAL WS event. |
| `GET /reports/export?format=pdf\|xlsx&range=daily\|weekly` | Downloads a summary report (ReportLab PDF / OpenPyXL XLSX) for the last 24h or 7d. |
| `GET /dashboard/summary` | Active worker count, open incidents by severity, latest readings per zone. |
| `/dashboard` · `/admin-simulator` | Static mounts for the operator dashboard and the demo simulator (built React apps). |
| `WS /ws/alerts` | Real-time broadcast of new incidents with severity `>= high`. |

## WebSocket usage

```js
const ws = new WebSocket("ws://localhost:8000/ws/alerts");
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

The server pushes an `{ event: "incident", ... }` payload whenever an incident
with severity `high` or `critical` is created.
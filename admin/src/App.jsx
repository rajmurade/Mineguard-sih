import { useEffect, useRef, useState } from "react";

const ZONES = ["Zone A - Tunnel 1", "Zone B - Open Pit"];

const GAS_LEVELS = [
  { label: "Normal", value: 25 },
  { label: "Elevated", value: 100 },
  { label: "High", value: 200 },
  { label: "Critical", value: 400 },
];

const MAX_FEED = 10;

const SEVERITY_COLORS = {
  compliant: "#2e7d32",
  warning: "#f9a825",
  high: "#d32f2f",
  critical: "#6a1b9a",
};

function feedId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function api(path, options) {
  return fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
}

export default function App() {
  // --- environmental reading form state ---
  const [zone, setZone] = useState(ZONES[0]);
  const [gasIdx, setGasIdx] = useState(0);
  const [aqi, setAqi] = useState(50);
  const [temp, setTemp] = useState(25);
  const [noise, setNoise] = useState(60);
  const [dust, setDust] = useState(1);

  // --- emergency drill state ---
  const [drillZone, setDrillZone] = useState(ZONES[0]);
  const [drillBusy, setDrillBusy] = useState(false);

  // --- live feed ---
  const [feed, setFeed] = useState([]);
  const [sending, setSending] = useState(false);
  const [wsStatus, setWsStatus] = useState("connecting");

  const feedRef = useRef([]);
  const wsRef = useRef(null);

  const pushFeed = (entry) => {
    const next = [...feedRef.current, { id: feedId(), ...entry }];
    feedRef.current = next.slice(-MAX_FEED);
    setFeed(feedRef.current);
  };

  // --- WebSocket -----------------------------------------------------
  useEffect(() => {
    let closed = false;
    let retry = null;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/alerts`);
      wsRef.current = ws;
      setWsStatus("connecting");

      ws.onopen = () => setWsStatus("connected");
      ws.onclose = () => {
        if (closed) return;
        setWsStatus("disconnected");
        retry = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (evt) => {
        let msg;
        try {
          msg = JSON.parse(evt.data);
        } catch {
          return;
        }
        if (msg.event === "incident") {
          pushFeed({
            kind: "incident",
            title: `INCIDENT #${msg.incident_id} · ${msg.type}`,
            detail: `${msg.zone}${msg.description ? ` — ${msg.description}` : ""}`,
            severity: msg.severity,
          });
        } else if (msg.event === "emergency_drill") {
          const names = (msg.unaccounted_workers || []).map((w) => w.name).join(", ");
          pushFeed({
            kind: "drill",
            title: `EMERGENCY DRILL · ${msg.zone}`,
            detail: `unaccounted: ${msg.unaccounted_count}${names ? ` — ${names}` : ""}`,
            severity: "critical",
          });
        }
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      if (wsRef.current) wsRef.current.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- actions ------------------------------------------------------
  const sendReading = async () => {
    setSending(true);
    try {
      const gas = GAS_LEVELS[gasIdx].value;
      const res = await api("/environmental-readings", {
        method: "POST",
        body: JSON.stringify({
          zone,
          gas_level: gas,
          aqi,
          temperature: temp,
          noise_db: noise,
          dust_pm: dust,
          source: "simulated",
        }),
      });
      const body = await res.json();
      if (!res.ok) {
        pushFeed({ kind: "error", title: "SEND FAILED", detail: JSON.stringify(body) });
        return;
      }
      (body.evaluations || []).forEach((ev) => {
        pushFeed({
          kind: "reading",
          title: `${ev.event_type} = ${ev.value}`,
          detail: ev.should_create_incident
            ? `→ ${ev.severity}  ·  incident #${ev.incident_id}`
            : `→ ${ev.severity}  (no incident)`,
          severity: ev.severity,
        });
      });
    } catch (err) {
      pushFeed({ kind: "error", title: "SEND ERROR", detail: String(err) });
    } finally {
      setSending(false);
    }
  };

  const triggerDrill = async () => {
    setDrillBusy(true);
    try {
      const res = await api("/emergency-drill/start", {
        method: "POST",
        body: JSON.stringify({ zone: drillZone }),
      });
      const body = await res.json();
      if (!res.ok) {
        pushFeed({ kind: "error", title: "DRILL FAILED", detail: JSON.stringify(body) });
        return;
      }
      const names = (body.unaccounted_workers || []).map((w) => w.name).join(", ");
      pushFeed({
        kind: "drill",
        title: `EMERGENCY DRILL RESPONSE · ${body.zone}`,
        detail: `unaccounted: ${body.unaccounted_count}${names ? ` — ${names}` : ""}`,
        severity: "critical",
      });
    } catch (err) {
      pushFeed({ kind: "error", title: "DRILL ERROR", detail: String(err) });
    } finally {
      setDrillBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="header">
        <h1>MineGuard · Admin Simulator</h1>
        <span className={`ws-badge ${wsStatus}`}>WS: {wsStatus}</span>
      </header>

      <main className="layout">
        {/* ------- left: controls ------- */}
        <section className="col">
          <div className="card">
            <h2>Send environmental reading</h2>

            <label>
              Zone
              <select value={zone} onChange={(e) => setZone(e.target.value)}>
                {ZONES.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Gas level
              <select value={gasIdx} onChange={(e) => setGasIdx(Number(e.target.value))}>
                {GAS_LEVELS.map((g, i) => (
                  <option key={g.label} value={i}>
                    {g.label} ({g.value} ppm)
                  </option>
                ))}
              </select>
            </label>

            <label>
              AQI: <strong>{aqi}</strong>
              <input
                type="range"
                min="0"
                max="1000"
                value={aqi}
                onChange={(e) => setAqi(Number(e.target.value))}
              />
            </label>

            <label>
              Temperature (°C): <strong>{temp}</strong>
              <input
                type="range"
                min="0"
                max="60"
                value={temp}
                onChange={(e) => setTemp(Number(e.target.value))}
              />
            </label>

            <label>
              Noise (dB): <strong>{noise}</strong>
              <input
                type="range"
                min="0"
                max="140"
                value={noise}
                onChange={(e) => setNoise(Number(e.target.value))}
              />
            </label>

            <label>
              Dust / PM: <strong>{dust}</strong>
              <input
                type="range"
                min="0"
                max="1000"
                value={dust}
                onChange={(e) => setDust(Number(e.target.value))}
              />
            </label>

            <button onClick={sendReading} disabled={sending}>
              {sending ? "Sending…" : "Send Reading"}
            </button>
          </div>

          <div className="card">
            <h2>Emergency drill</h2>
            <label>
              Zone
              <select value={drillZone} onChange={(e) => setDrillZone(e.target.value)}>
                {ZONES.map((z) => (
                  <option key={z} value={z}>
                    {z}
                  </option>
                ))}
              </select>
            </label>
            <p className="hint">
              Cross-checks entry/exit events and reports workers still inside the zone.
            </p>
            <button className="danger" onClick={triggerDrill} disabled={drillBusy}>
              {drillBusy ? "Triggering…" : "Trigger Emergency Drill"}
            </button>
          </div>
        </section>

        {/* ------- right: live feed ------- */}
        <section className="col">
          <div className="card">
            <h2>Live feed · last {MAX_FEED} events</h2>
            {feed.length === 0 ? (
              <p className="empty">No events yet — send a reading or trigger a drill.</p>
            ) : (
              <ul className="feed">
                {feed.map((e) => (
                  <li key={e.id} className={`feed-item ${e.kind}`}>
                    <div className="feed-line">
                      <span className="severity-dot" style={{ background: SEVERITY_COLORS[e.severity] || "#999" }} />
                      <strong>{e.title}</strong>
                    </div>
                    <div className="feed-detail">{e.detail}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
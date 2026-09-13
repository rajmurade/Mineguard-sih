import { useEffect, useRef, useState } from "react";

// Subscribe to /ws/alerts with automatic reconnection.
// Returns one of: "connecting" | "connected" | "reconnecting".
// A 30s heartbeat keeps the socket alive so the backend's ping echo flows.

const RETRY_DELAY_MS = 2500;
const HEARTBEAT_MS = 30000;

export function useAlerts(onMessage) {
  const [status, setStatus] = useState("connecting");
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    let socket = null;
    let closedByUs = false;
    let retryTimer = null;
    let heartbeatTimer = null;

    const connect = () => {
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${proto}://${window.location.host}/ws/alerts`);
      setStatus("connecting");

      socket.onopen = () => {
        setStatus("connected");
        heartbeatTimer = window.setInterval(() => {
          if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send("ping");
          }
        }, HEARTBEAT_MS);
      };

      socket.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        if (data.event === "ping") return; // liveness echo, not a real alert
        handlerRef.current?.(data);
      };

      socket.onclose = () => {
        window.clearInterval(heartbeatTimer);
        setStatus("reconnecting");
        if (!closedByUs) {
          retryTimer = window.setTimeout(connect, RETRY_DELAY_MS);
        }
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      closedByUs = true;
      window.clearTimeout(retryTimer);
      window.clearInterval(heartbeatTimer);
      socket?.close();
    };
  }, []);

  return status;
}
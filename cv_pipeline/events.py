"""Convert unified detections into the Compliance Engine's normalized event schema."""

from __future__ import annotations

from datetime import datetime, timezone

from cv_pipeline.proximity import ProximityAnalyzer

# PPE model violation classes -> compliance event_type
PPE_VIOLATION_MAP: dict[str, str] = {
    "No-Helmet": "no_helmet",
    "No-Vest": "no_vest",
}

# event_type -> incident type shown in the evidence filename
EVENT_DIR_NAMES = {
    "no_helmet": "no-helmet",
    "no_vest": "no-vest",
    "proximity_risk": "proximity",
}


def base_event(
    event_type: str, confidence: float, zone: str, timestamp: datetime, worker_id: int | None
) -> dict:
    return {
        "source": "cv",
        "event_type": event_type,
        "zone": zone,
        "worker_id": worker_id,
        "confidence": confidence,
        "value": None,
        "timestamp": timestamp.isoformat(),
    }


def detections_to_events(
    detections: list[dict],
    zone: str,
    analyzer: ProximityAnalyzer,
    worker_id: int | None = None,
    timestamp: datetime | None = None,
) -> list[dict]:
    """Build compliance events from one frame's detections.

    Maps:
      No-Helmet -> "no_helmet",   No-Vest -> "no_vest",
      person/Worker near car/truck -> "proximity_risk" (+ ``objects`` for combo).
    """
    ts = timestamp or datetime.now(timezone.utc)
    events: list[dict] = []

    for detection in detections:
        event_type = PPE_VIOLATION_MAP.get(detection.get("class_name"))
        if event_type:
            events.append(base_event(event_type, detection["confidence"], zone, ts, worker_id))

    for pair in analyzer.analyze(detections):
        confidence = min(pair["person"]["confidence"], pair["vehicle"]["confidence"])
        event = base_event("proximity_risk", confidence, zone, ts, worker_id)
        event["objects"] = pair["objects"]
        event["distance_px"] = round(pair["distance"], 1)
        events.append(event)

    return events
"""Helpers for pushing incident/system events over the WebSocket."""

from app.enums import Severity
from app.models import Incident
from app.schemas.ws import IncidentAlertPayload
from app.websocket_manager import manager

BROADCAST_THRESHOLD = "high"


async def broadcast_incident(incident: Incident) -> None:
    """Broadcast an incident over WS when its severity is >= BROADCAST_THRESHOLD."""
    if not Severity.meets_threshold(incident.severity, BROADCAST_THRESHOLD):
        return
    payload = IncidentAlertPayload(
        incident_id=incident.id,
        type=incident.type,
        zone=incident.zone,
        timestamp=incident.timestamp,
        severity=incident.severity,
        worker_id=incident.worker_id,
        resolution_status=incident.resolution_status,
        description=incident.description,
    )
    await manager.broadcast(payload.model_dump(mode="json"))
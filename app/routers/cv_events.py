from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Incident
from app.schemas.cv_events import CvEventPayload, CvEventResponse
from app.services.alerts import broadcast_incident
from app.services.compliance import (
    INCIDENT_TYPE_MAP,
    decimal_severity,
    materialize_incident,
)
from compliance import evaluate_event

router = APIRouter(prefix="/cv-events", tags=["cv"])


@router.post("", response_model=CvEventResponse, status_code=202)
async def ingest_cv_event(payload: CvEventPayload, db: Session = Depends(get_db)):
    """Evaluate one CV detection event through the Compliance Engine.

    Runs the same pipeline as environmental readings: compliance decision ->
    incident row (on confirmation) -> WebSocket broadcast for severe events.
    The Compliance Engine's debouncer decides when repeated detections actually
    confirm an incident.
    """
    event = payload.model_dump()
    timestamp = event.pop("timestamp") or datetime.now(timezone.utc)
    event["timestamp"] = timestamp

    decision = evaluate_event(event)

    incident: Incident | None = None
    if decision.should_create_incident:
        if event["event_type"] not in INCIDENT_TYPE_MAP:
            raise HTTPException(
                status_code=422,
                detail=f"no incident type mapping for compliance event '{event['event_type']}'",
            )
        incident = materialize_incident(
            db,
            event_type=event["event_type"],
            severity=decision.severity,
            zone=event["zone"],
            timestamp=timestamp,
            worker_id=event.get("worker_id"),
            description=(
                f"{event['event_type']} (confidence={event.get('confidence')}): "
                f"{decision.reason}"
            ),
            evidence_frame_path=event.get("evidence_frame_path"),
        )
        db.commit()
        await broadcast_incident(incident)

    return CvEventResponse(
        should_create_incident=decision.should_create_incident,
        severity=decimal_severity(decision.severity),
        incident_id=incident.id if incident else None,
        reason=decision.reason,
        recipients=decision.alert_recipients,
        escalate_external=bool(decision.escalate_external),
    )
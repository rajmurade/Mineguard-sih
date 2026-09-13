from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import IncidentType, ResolutionStatus, Severity
from app.models import AlertLog, Incident
from app.schemas.incident import (
    AlertLogCreate,
    AlertLogRead,
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
)
from app.services.alerts import broadcast_incident

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=201)
async def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    timestamp = data.pop("timestamp", None)
    incident = Incident(timestamp=timestamp, **data)
    db.add(incident)
    db.commit()
    db.refresh(incident)

    await broadcast_incident(incident)

    return incident


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    status: ResolutionStatus | None = None,
    severity: Severity | None = None,
    type: IncidentType | None = None,
    zone: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(Incident)
    if status is not None:
        query = query.where(Incident.resolution_status == status)
    if severity is not None:
        query = query.where(Incident.severity == severity)
    if type is not None:
        query = query.where(Incident.type == type)
    if zone is not None:
        query = query.where(Incident.zone == zone)
    return db.scalars(query.order_by(Incident.timestamp.desc())).all()


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/{incident_id}/evidence")
def incident_evidence(incident_id: int, db: Session = Depends(get_db)):
    """Serve the saved CV evidence frame (JPEG) stored on this incident.

    The stored path must be consistent with the container mount: the CV
    pipeline persists cwd-relative paths like ``evidence/no-vest/x.jpg``, which
    resolve to ``/app/evidence/no-vest/x.jpg`` inside the API container (where
    ``./evidence`` is mounted) and to ``<cwd>/evidence/no-vest/x.jpg`` on the
    host. Absolute paths are served as-is for legacy rows.
    """
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not incident.evidence_frame_path:
        raise HTTPException(status_code=404, detail="Incident has no evidence frame")
    evidence_path = Path(incident.evidence_frame_path)
    if not evidence_path.is_absolute():
        evidence_path = Path.cwd() / evidence_path
    if not evidence_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Evidence file not found on disk: {evidence_path}",
        )
    return FileResponse(evidence_path, media_type="image/jpeg")


@router.put("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)
):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, key, value)
    db.commit()
    db.refresh(incident)
    return incident


@router.delete("/{incident_id}", status_code=204)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    db.delete(incident)
    db.commit()


@router.post("/{incident_id}/alert-logs", response_model=AlertLogRead, status_code=201)
def create_alert_log(
    incident_id: int, payload: AlertLogCreate, db: Session = Depends(get_db)
):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    data = payload.model_dump()
    sent_at = data.pop("sent_at", None)
    data.pop("incident_id", None)
    log = AlertLog(incident_id=incident_id, sent_at=sent_at, **data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/{incident_id}/alert-logs", response_model=list[AlertLogRead])
def list_alert_logs(incident_id: int, db: Session = Depends(get_db)):
    if db.get(Incident, incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    logs = db.scalars(
        select(AlertLog).where(AlertLog.incident_id == incident_id)
    ).all()
    return logs


@router.post("/{incident_id}/alert-logs/{log_id}/acknowledge", response_model=AlertLogRead)
def acknowledge_alert_log(
    incident_id: int, log_id: int, db: Session = Depends(get_db)
):
    log = db.get(AlertLog, log_id)
    if log is None or log.incident_id != incident_id:
        raise HTTPException(status_code=404, detail="Alert log not found")
    log.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log)
    return log
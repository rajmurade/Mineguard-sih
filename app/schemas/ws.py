from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import IncidentType, ResolutionStatus, Severity
from app.schemas.worker import WorkerRead


class IncidentAlertPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str = "incident"
    incident_id: int
    type: IncidentType
    zone: str
    timestamp: datetime
    severity: Severity
    worker_id: int | None = None
    resolution_status: ResolutionStatus
    description: str | None = None


class EmergencyDrillPayload(BaseModel):
    event: str = "emergency_drill"
    severity: Severity = Severity.critical
    zone: str
    started_at: datetime
    unaccounted_workers: list[WorkerRead] = []
    unaccounted_count: int = 0
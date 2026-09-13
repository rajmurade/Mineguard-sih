from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import IncidentType, ResolutionStatus, Severity


class IncidentBase(BaseModel):
    type: IncidentType
    zone: str = Field(min_length=1, max_length=120)
    severity: Severity
    worker_id: int | None = None
    evidence_frame_path: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=1000)


class IncidentCreate(IncidentBase):
    timestamp: datetime | None = None


class IncidentUpdate(BaseModel):
    type: IncidentType | None = None
    zone: str | None = Field(default=None, min_length=1, max_length=120)
    severity: Severity | None = None
    worker_id: int | None = None
    evidence_frame_path: str | None = Field(default=None, max_length=500)
    resolution_status: ResolutionStatus | None = None
    description: str | None = Field(default=None, max_length=1000)


class IncidentRead(IncidentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    resolution_status: ResolutionStatus


class AlertLogBase(BaseModel):
    incident_id: int
    recipient_role: str = Field(min_length=1, max_length=80)


class AlertLogCreate(AlertLogBase):
    sent_at: datetime | None = None


class AlertLogUpdate(BaseModel):
    acknowledged_at: datetime | None = None


class AlertLogRead(AlertLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sent_at: datetime
    acknowledged_at: datetime | None = None
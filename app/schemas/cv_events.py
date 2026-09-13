from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.enums import Severity

# Compliance CV event types (keep in sync with compliance/rules.json "cv").
CV_EVENT_TYPES = Literal[
    "no_helmet",
    "no_vest",
    "restricted_zone_entry",
    "proximity_risk",
    "fire",
    "smoke",
    "fall",
]


class CvEventPayload(BaseModel):
    source: Literal["cv"] = "cv"
    event_type: CV_EVENT_TYPES
    zone: str = Field(min_length=1, max_length=120)
    worker_id: int | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    value: float | None = None
    objects: list[str] = []
    evidence_frame_path: str | None = Field(default=None, max_length=500)
    timestamp: datetime | None = None


class CvEventResponse(BaseModel):
    should_create_incident: bool
    severity: Severity
    incident_id: int | None = None
    reason: str
    recipients: list[str] = []
    escalate_external: bool = False
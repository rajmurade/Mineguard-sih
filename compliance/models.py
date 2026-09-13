"""Normalized domain types for the Compliance Engine: no FastAPI, no DB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class Source(str, Enum):
    CV = "cv"
    ENVIRONMENTAL = "environmental"


class EventType(str, Enum):
    NO_HELMET = "no_helmet"
    NO_VEST = "no_vest"
    RESTRICTED_ZONE_ENTRY = "restricted_zone_entry"
    PROXIMITY_RISK = "proximity_risk"
    FIRE = "fire"
    SMOKE = "smoke"
    FALL = "fall"
    GAS_HIGH = "gas_high"
    AQI_HIGH = "aqi_high"
    TEMP_HIGH = "temp_high"
    NOISE_HIGH = "noise_high"
    DUST_HIGH = "dust_high"

    @property
    def is_cv(self) -> bool:
        return self in {
            EventType.NO_HELMET,
            EventType.NO_VEST,
            EventType.RESTRICTED_ZONE_ENTRY,
            EventType.PROXIMITY_RISK,
            EventType.FIRE,
            EventType.SMOKE,
            EventType.FALL,
        }


@dataclass(frozen=True)
class SafetyEvent:
    """Normalized event accepted by the engine.

    ``objects`` is an optional list of detected object labels (e.g.
    ``["worker", "heavy_vehicle"]``) used by combo rules such as
    ``proximity_risk``.
    """

    source: Source
    event_type: EventType
    zone: str
    worker_id: int | None
    value: float | None
    confidence: float | None
    timestamp: datetime
    objects: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "SafetyEvent":
        required = ("source", "event_type", "zone", "timestamp")
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"event missing required fields: {missing}")

        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        objects = data.get("objects") or data.get("object_types") or ()
        if isinstance(objects, str):
            objects = [objects]

        event = cls(
            source=Source(data["source"]),
            event_type=EventType(data["event_type"]),
            zone=str(data["zone"]),
            worker_id=data.get("worker_id"),
            value=float(data["value"]) if data.get("value") is not None else None,
            confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
            timestamp=timestamp,
            objects=tuple(objects),
        )

        if event.source is Source.ENVIRONMENTAL and event.value is None:
            raise ValueError(f"event_type '{event.event_type.value}' requires 'value'")
        return event


@dataclass(frozen=True)
class ComplianceDecision:
    """Structured result returned by :func:`evaluate_event`."""

    should_create_incident: bool
    severity: Severity
    alert_recipients: list[str]
    reason: str
    escalate_external: bool = False

    def as_dict(self) -> dict:
        return {
            "should_create_incident": self.should_create_incident,
            "severity": self.severity.value,
            "alert_recipients": list(self.alert_recipients),
            "escalate_external": self.escalate_external,
            "reason": self.reason,
        }
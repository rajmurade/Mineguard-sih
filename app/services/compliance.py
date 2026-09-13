"""Bridge between EnvironmentalReading rows and the Compliance Engine.

Each sensor reading is converted into compliance ``safety_event`` payloads
(one per supported metric) and evaluated. Any event that reaches
``should_create_incident`` becomes an Incident row and is broadcast over WS.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from compliance import evaluate_event
from app.enums import IncidentType, ResolutionStatus, Severity
from app.models import EnvironmentalReading, Incident
from app.services.alerts import broadcast_incident

# (EnvironmentalReading field, compliance event_type) pairs evaluated per reading.
METRIC_EVENT_PAIRS: list[tuple[str, str]] = [
    ("gas_level", "gas_high"),
    ("aqi", "aqi_high"),
    ("temperature", "temp_high"),
    ("noise_db", "noise_high"),
    ("dust_pm", "dust_high"),
]

# compliance event_type -> backend Incident.type
INCIDENT_TYPE_MAP: dict[str, IncidentType] = {
    "no_helmet": IncidentType.ppe_violation,
    "no_vest": IncidentType.ppe_violation,
    "restricted_zone_entry": IncidentType.unauthorized_zone,
    "proximity_risk": IncidentType.proximity_risk,
    "fire": IncidentType.fire_smoke,
    "smoke": IncidentType.fire_smoke,
    "fall": IncidentType.fall,
    "gas_high": IncidentType.environmental,
    "aqi_high": IncidentType.environmental,
    "temp_high": IncidentType.environmental,
    "noise_high": IncidentType.environmental,
    "dust_high": IncidentType.environmental,
}


@dataclass
class ReadingEvaluation:
    event_type: str
    value: float
    should_create_incident: bool
    severity: Severity
    reason: str
    incident_id: int | None = None

    def as_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "value": self.value,
            "should_create_incident": self.should_create_incident,
            "severity": self.severity.value,
            "incident_id": self.incident_id,
            "reason": self.reason,
        }


def materialize_incident(
    db: Session,
    *,
    event_type: str,
    severity,
    zone: str,
    timestamp,
    worker_id: int | None = None,
    description: str | None = None,
    evidence_frame_path: str | None = None,
) -> Incident:
    """Create a flushed (but uncommitted) Incident row from a compliance event.

    Caller owns the commit (so it can broadcast before/after). Raises
    ValueError when the compliance event_type has no IncidentType mapping.
    """
    incident_type = INCIDENT_TYPE_MAP.get(event_type)
    if incident_type is None:
        raise ValueError(f"no IncidentType mapping for compliance event '{event_type}'")
    incident = Incident(
        type=incident_type,
        zone=zone,
        timestamp=timestamp,
        severity=Severity(severity.value),
        worker_id=worker_id,
        evidence_frame_path=evidence_frame_path,
        resolution_status=ResolutionStatus.open,
        description=description,
    )
    db.add(incident)
    db.flush()
    return incident


async def process_reading(db: Session, reading: EnvironmentalReading) -> list[ReadingEvaluation]:
    """Evaluate a saved reading, persist incidents, and broadcast alerts.

    Returns one ReadingEvaluation per monitored metric.
    """
    evaluations: list[ReadingEvaluation] = []
    created: list[Incident] = []

    for field, event_type in METRIC_EVENT_PAIRS:
        value = float(getattr(reading, field))
        event = {
            "source": "environmental",
            "event_type": event_type,
            "zone": reading.zone,
            "worker_id": None,
            "value": value,
            "confidence": None,
            "timestamp": reading.timestamp,
        }
        decision = evaluate_event(event)

        incident_id: int | None = None
        if decision.should_create_incident:
            incident = materialize_incident(
                db,
                event_type=event_type,
                severity=decision.severity,
                zone=reading.zone,
                timestamp=reading.timestamp,
                description=f"{event_type} (value={value}): {decision.reason}",
            )
            incident_id = incident.id
            created.append(incident)

        evaluations.append(
            ReadingEvaluation(
                event_type=event_type,
                value=value,
                should_create_incident=decision.should_create_incident,
                severity=decimal_severity(decision.severity),
                reason=decision.reason,
                incident_id=incident_id,
            )
        )

    if created:
        db.commit()
        for incident in created:
            await broadcast_incident(incident)

    return evaluations


def decimal_severity(severity) -> Severity:
    """Map a compliance Severity back to the backend severity enum."""
    return Severity(severity.value)
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import ResolutionStatus, Severity
from app.models import EnvironmentalReading, Incident, Worker
from app.schemas.dashboard import DashboardSummary, LatestReading, SeverityCount
from app.services.presence import active_worker_ids

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    worker_ids = active_worker_ids(db)
    active_count = 0
    if worker_ids:
        active_count = len(
            db.scalars(
                select(Worker.id).where(Worker.id.in_(worker_ids)).where(Worker.active_status.is_(True))
            ).all()
        )

    severity_rows = db.execute(
        select(Incident.severity, func.count(Incident.id))
        .where(Incident.resolution_status == ResolutionStatus.open)
        .group_by(Incident.severity)
    ).all()
    open_by_severity = [
        SeverityCount(severity=sev, count=count)
        for sev, count in severity_rows
    ]

    zone_rows = db.execute(
        select(EnvironmentalReading.zone, func.max(EnvironmentalReading.id))
        .group_by(EnvironmentalReading.zone)
    ).all()
    readings: list[LatestReading] = []
    for zone, _ in zone_rows:
        reading = db.scalar(
            select(EnvironmentalReading)
            .where(EnvironmentalReading.zone == zone)
            .order_by(EnvironmentalReading.timestamp.desc())
            .limit(1)
        )
        if reading is not None:
            readings.append(
                LatestReading(
                    zone=reading.zone,
                    gas_level=reading.gas_level,
                    aqi=reading.aqi,
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    noise_db=reading.noise_db,
                    dust_pm=reading.dust_pm,
                )
            )

    return DashboardSummary(
        active_worker_count=active_count,
        open_incidents=open_by_severity,
        latest_readings=readings,
    )
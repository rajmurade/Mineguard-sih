from pydantic import BaseModel

from app.enums import Severity


class SeverityCount(BaseModel):
    severity: Severity
    count: int


class LatestReading(BaseModel):
    zone: str
    gas_level: float | None = None
    aqi: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    noise_db: float | None = None
    dust_pm: float | None = None


class DashboardSummary(BaseModel):
    active_worker_count: int
    open_incidents: list[SeverityCount]
    latest_readings: list[LatestReading]
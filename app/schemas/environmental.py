from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import DataSource, Severity


class EnvironmentalReadingBase(BaseModel):
    zone: str = Field(min_length=1, max_length=120)
    gas_level: float = Field(ge=0, default=0)
    aqi: float = Field(ge=0, default=0)
    temperature: float = Field(default=0.0)
    humidity: float = Field(ge=0, le=100, default=0)
    noise_db: float = Field(ge=0, default=0)
    dust_pm: float = Field(ge=0, default=0)
    source: DataSource = DataSource.simulated


class EnvironmentalReadingCreate(EnvironmentalReadingBase):
    timestamp: datetime | None = None


class EnvironmentalReadingUpdate(BaseModel):
    gas_level: float | None = Field(default=None, ge=0)
    aqi: float | None = Field(default=None, ge=0)
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    noise_db: float | None = Field(default=None, ge=0)
    dust_pm: float | None = Field(default=None, ge=0)


class EnvironmentalReadingRead(EnvironmentalReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime


class EventEvaluation(BaseModel):
    event_type: str
    value: float
    should_create_incident: bool
    severity: Severity
    incident_id: int | None = None
    reason: str


class ReadingWithEvaluation(EnvironmentalReadingRead):
    evaluations: list[EventEvaluation] = []
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import DataSource


class EnvironmentalReading(Base):
    __tablename__ = "environmental_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone: Mapped[str] = mapped_column(String(120), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    gas_level: Mapped[float] = mapped_column(Float, default=0.0)
    aqi: Mapped[float] = mapped_column(Float, default=0.0)
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    humidity: Mapped[float] = mapped_column(Float, default=0.0)
    noise_db: Mapped[float] = mapped_column(Float, default=0.0)
    dust_pm: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, name="data_source"), default=DataSource.simulated
    )
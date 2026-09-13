from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import IncidentType, ResolutionStatus, Severity
from app.models.worker import Worker


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[IncidentType] = mapped_column(
        Enum(IncidentType, name="incident_type"), index=True
    )
    zone: Mapped[str] = mapped_column(String(120), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    severity: Mapped[Severity] = mapped_column(Enum(Severity, name="severity"), index=True)
    worker_id: Mapped[int | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), nullable=True
    )
    evidence_frame_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus, name="resolution_status"),
        default=ResolutionStatus.open,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    worker: Mapped["Worker | None"] = relationship()  # noqa: F821
    alert_logs: Mapped[list["AlertLog"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    recipient_role: Mapped[str] = mapped_column(String(80))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="alert_logs")
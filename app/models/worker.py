from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import EntryExitDirection


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80))
    tag_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active_status: Mapped[bool] = mapped_column(default=True)

    entries_exits: Mapped[list["WorkerEntryExit"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )


class WorkerEntryExit(Base):
    __tablename__ = "worker_entry_exits"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("workers.id", ondelete="CASCADE"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    direction: Mapped[EntryExitDirection] = mapped_column(
        Enum(EntryExitDirection, name="entry_exit_direction"), index=True
    )
    zone: Mapped[str] = mapped_column(String(120))

    worker: Mapped[Worker] = relationship(back_populates="entries_exits")
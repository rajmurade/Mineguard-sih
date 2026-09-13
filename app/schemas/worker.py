from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import EntryExitDirection


class WorkerBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    tag_id: str = Field(min_length=1, max_length=64)
    active_status: bool = True


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, min_length=1, max_length=80)
    tag_id: str | None = Field(default=None, min_length=1, max_length=64)
    active_status: bool | None = None


class WorkerRead(WorkerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class WorkerEntryExitBase(BaseModel):
    worker_id: int | None = None
    direction: EntryExitDirection
    zone: str = Field(min_length=1, max_length=120)


class WorkerEntryExitCreate(WorkerEntryExitBase):
    timestamp: datetime | None = None


class WorkerEntryExitRead(WorkerEntryExitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: int
    timestamp: datetime


class WorkerDetail(WorkerRead):
    entries_exits: list[WorkerEntryExitRead] = []
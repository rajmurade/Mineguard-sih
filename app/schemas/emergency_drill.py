from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.worker import WorkerRead


class EmergencyDrillStartRequest(BaseModel):
    zone: str = Field(min_length=1, max_length=120)
    drill_end_elapsed_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Seconds since the drill end time; if it exceeds the threshold the "
        "roll call is treated as finished and unaccounted workers are reported. For "
        "demo purposes results are returned immediately when omitted.",
    )


class EmergencyDrillStartResponse(BaseModel):
    zone: str
    started_at: datetime
    drill_mode: str = "immediate"
    unaccounted_workers: list[WorkerRead]
    unaccounted_count: int
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.emergency_drill import (
    EmergencyDrillStartRequest,
    EmergencyDrillStartResponse,
)
from app.schemas.ws import EmergencyDrillPayload
from app.services.presence import active_workers_in_zone
from app.websocket_manager import manager

router = APIRouter(prefix="/emergency-drill", tags=["emergency"])

# Demo-only threshold for the "drill end time reached" path. If the drill end is
# more than this many seconds in the past, workers still inside are reported as
# unaccounted; otherwise the roll call is still open. For demo purposes results
# are returned immediately regardless.
ROLL_CALL_END_THRESHOLD_SECONDS = 15.0


@router.post("/start", response_model=EmergencyDrillStartResponse)
async def start_emergency_drill(
    payload: EmergencyDrillStartRequest, db: Session = Depends(get_db)
):
    """Start (simulate) an emergency drill for a zone.

    Cross-references WorkerEntryExit to find workers still inside the zone
    (last event is an ``entry`` with no later ``exit``) and broadcasts them as
    a CRITICAL-severity system event over the WebSocket.
    """
    started_at = datetime.now(timezone.utc)

    elapsed = payload.drill_end_elapsed_seconds
    if elapsed is not None and elapsed > ROLL_CALL_END_THRESHOLD_SECONDS:
        drill_mode = "roll_call_closed"
    else:
        drill_mode = "immediate"

    workers = active_workers_in_zone(db, payload.zone)

    unaccounted = [worker for worker in workers if worker.active_status]

    broadcast = EmergencyDrillPayload(
        zone=payload.zone,
        started_at=started_at,
        unaccounted_workers=unaccounted,
        unaccounted_count=len(unaccounted),
    )
    await manager.broadcast(broadcast.model_dump(mode="json"))

    return EmergencyDrillStartResponse(
        zone=payload.zone,
        started_at=started_at,
        drill_mode=drill_mode,
        unaccounted_workers=unaccounted,
        unaccounted_count=len(unaccounted),
    )
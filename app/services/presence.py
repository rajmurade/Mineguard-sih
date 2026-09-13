from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import EntryExitDirection
from app.models import Worker, WorkerEntryExit


def latest_event_map(db: Session) -> dict[int, WorkerEntryExit]:
    """Latest entry/exit event per worker. Returns ``{worker_id: event}``."""
    events = db.scalars(
        select(WorkerEntryExit).order_by(WorkerEntryExit.timestamp.desc())
    ).all()

    latest: dict[int, WorkerEntryExit] = {}
    for event in events:
        latest.setdefault(event.worker_id, event)
    return latest


def latest_entry_exit_map(db: Session) -> dict[int, bool]:
    """Latest event per worker. Returns {worker_id: is_inside}."""
    return {
        worker_id: event.direction == EntryExitDirection.entry
        for worker_id, event in latest_event_map(db).items()
    }


def active_worker_ids(db: Session) -> list[int]:
    return [
        worker_id
        for worker_id, inside in latest_entry_exit_map(db).items()
        if inside
    ]


def active_worker_ids_in_zone(db: Session, zone: str) -> list[int]:
    """Workers still inside a specific zone.

    A worker counts as being in ``zone`` only when their single most recent
    entry/exit event is an ``entry`` recorded in that zone (i.e. they were the
    last to enter this zone and have no later exit anywhere).
    """
    return [
        worker_id
        for worker_id, event in latest_event_map(db).items()
        if event.direction is EntryExitDirection.entry and event.zone == zone
    ]


def active_workers_in_zone(db: Session, zone: str) -> list[Worker]:
    ids = active_worker_ids_in_zone(db, zone)
    if not ids:
        return []
    return list(
        db.scalars(select(Worker).where(Worker.id.in_(ids)).where(Worker.active_status.is_(True))).all()
    )
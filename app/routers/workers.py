from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Worker, WorkerEntryExit
from app.schemas.worker import (
    WorkerCreate,
    WorkerDetail,
    WorkerEntryExitCreate,
    WorkerEntryExitRead,
    WorkerRead,
    WorkerUpdate,
)

router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("", response_model=WorkerRead, status_code=201)
def create_worker(payload: WorkerCreate, db: Session = Depends(get_db)):
    worker = Worker(**payload.model_dump())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.get("", response_model=list[WorkerRead])
def list_workers(
    active: bool | None = None, db: Session = Depends(get_db)
):
    query = select(Worker)
    if active is not None:
        query = query.where(Worker.active_status == active)
    return db.scalars(query.order_by(Worker.id)).all()


@router.get("/active", response_model=list[WorkerRead])
def list_active_workers(db: Session = Depends(get_db)):
    query = (
        select(WorkerEntryExit)
        .order_by(WorkerEntryExit.timestamp.desc())
    )
    latest_events = db.scalars(query).all()

    mine_map: dict[int, bool] = {}
    for event in latest_events:
        if event.worker_id not in mine_map:
            mine_map[event.worker_id] = event.direction.value == "entry"

    active_ids = [wid for wid, inside in mine_map.items() if inside]
    if not active_ids:
        return []
    workers = db.scalars(
        select(Worker)
        .where(Worker.id.in_(active_ids))
        .where(Worker.active_status.is_(True))
    ).all()
    return workers


@router.get("/{worker_id}", response_model=WorkerDetail)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.scalar(
        select(Worker)
        .options(joinedload(Worker.entries_exits))
        .where(Worker.id == worker_id)
    )
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.put("/{worker_id}", response_model=WorkerRead)
def update_worker(
    worker_id: int, payload: WorkerUpdate, db: Session = Depends(get_db)
):
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(worker, key, value)
    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    db.delete(worker)
    db.commit()


@router.post("/{worker_id}/entry-exits", response_model=WorkerEntryExitRead, status_code=201)
def create_entry_exit(
    worker_id: int, payload: WorkerEntryExitCreate, db: Session = Depends(get_db)
):
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    data = payload.model_dump()
    timestamp = data.pop("timestamp", None)
    data.pop("worker_id", None)
    event = WorkerEntryExit(worker_id=worker_id, timestamp=timestamp, **data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
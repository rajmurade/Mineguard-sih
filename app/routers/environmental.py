from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EnvironmentalReading
from app.schemas.environmental import (
    EnvironmentalReadingCreate,
    EnvironmentalReadingRead,
    EnvironmentalReadingUpdate,
    ReadingWithEvaluation,
)
from app.services.compliance import process_reading

router = APIRouter(prefix="/environmental-readings", tags=["environmental"])


@router.post("", response_model=ReadingWithEvaluation, status_code=201)
async def create_reading(
    payload: EnvironmentalReadingCreate, db: Session = Depends(get_db)
):
    data = payload.model_dump()
    timestamp = data.pop("timestamp", None)
    reading = EnvironmentalReading(timestamp=timestamp, **data)
    db.add(reading)
    db.commit()
    db.refresh(reading)

    evaluations = await process_reading(db, reading)

    return ReadingWithEvaluation(
        id=reading.id,
        zone=reading.zone,
        timestamp=reading.timestamp,
        gas_level=reading.gas_level,
        aqi=reading.aqi,
        temperature=reading.temperature,
        humidity=reading.humidity,
        noise_db=reading.noise_db,
        dust_pm=reading.dust_pm,
        source=reading.source,
        evaluations=[
            item.as_dict() for item in evaluations
        ],
    )


@router.get("", response_model=list[EnvironmentalReadingRead])
def list_readings(
    zone: str | None = None,
    source: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = select(EnvironmentalReading)
    if zone is not None:
        query = query.where(EnvironmentalReading.zone == zone)
    if source is not None:
        query = query.where(EnvironmentalReading.source == source)
    return db.scalars(
        query.order_by(EnvironmentalReading.timestamp.desc()).limit(limit)
    ).all()


@router.get("/latest", response_model=list[EnvironmentalReadingRead])
def latest_readings(db: Session = Depends(get_db)):
    zones = db.scalars(
        select(EnvironmentalReading.zone).distinct()
    ).all()
    result = []
    for zone in zones:
        reading = db.scalar(
            select(EnvironmentalReading)
            .where(EnvironmentalReading.zone == zone)
            .order_by(EnvironmentalReading.timestamp.desc())
            .limit(1)
        )
        if reading is not None:
            result.append(reading)
    return result


@router.get("/{reading_id}", response_model=EnvironmentalReadingRead)
def get_reading(reading_id: int, db: Session = Depends(get_db)):
    reading = db.get(EnvironmentalReading, reading_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    return reading


@router.put("/{reading_id}", response_model=EnvironmentalReadingRead)
def update_reading(
    reading_id: int, payload: EnvironmentalReadingUpdate, db: Session = Depends(get_db)
):
    reading = db.get(EnvironmentalReading, reading_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(reading, key, value)
    db.commit()
    db.refresh(reading)
    return reading


@router.delete("/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)):
    reading = db.get(EnvironmentalReading, reading_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="Reading not found")
    db.delete(reading)
    db.commit()
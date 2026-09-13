from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.enums import DataSource
from app.models import EnvironmentalReading

ZONES = ["Zone A - Tunnel 1", "Zone B - Open Pit"]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(EnvironmentalReading.id).limit(1))
        if existing is not None:
            print("Database already seeded. Skipping.")
            return

        now = datetime.now(timezone.utc)
        for zone in ZONES:
            base = [
                (1.5, 42, 24.0, 60.0, 78.0, 0.35),
                (2.1, 55, 25.5, 62.0, 81.0, 0.50),
                (1.8, 48, 24.8, 61.0, 79.0, 0.42),
            ]
            for offset, (gas, aqi, temp, humidity, noise, dust) in enumerate(base):
                db.add(
                    EnvironmentalReading(
                        zone=zone,
                        timestamp=now - timedelta(minutes=10 - offset * 5),
                        gas_level=gas + ZONES.index(zone) * 0.4,
                        aqi=aqi + ZONES.index(zone) * 10,
                        temperature=temp,
                        humidity=humidity,
                        noise_db=noise,
                        dust_pm=dust,
                        source=DataSource.simulated,
                    )
                )

        db.commit()
        print(f"Seeded {len(ZONES)} zones with environmental data (no fake worker registry).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
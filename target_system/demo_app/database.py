"""
Target Demo Application: Database Connection Manager
Configures SQLAlchemy QueuePool with dynamic disposal and reconnection.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

import target_system.demo_app.config as config
from target_system.demo_app.models import Base, Room

engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            pass
    engine = create_engine(
        config.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=config.POOL_SIZE,
        max_overflow=config.MAX_OVERFLOW,
        pool_timeout=config.POOL_TIMEOUT,
        connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_initial_rooms()
    return engine, SessionLocal


def get_db():
    global SessionLocal
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_initial_rooms():
    global SessionLocal
    db = SessionLocal()
    try:
        if db.query(Room).count() == 0:
            for i in range(1, 21):
                room = Room(
                    room_number=f"ROOM-{100+i}",
                    room_type="Single Bed Deluxe" if i % 2 == 0 else "Double Bed Sharing",
                    monthly_rent=9500.0 if i % 2 == 0 else 6500.0,
                    is_available=True
                )
                db.add(room)
            db.commit()
    finally:
        db.close()


# Initialize on import
init_db()

"""
Target Demo Application: Server
FastAPI microservice modeling room bookings and rent transactions under realistic concurrency.
"""

import time
import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import target_system.demo_app.config as config
from target_system.demo_app.database import get_db, init_db, engine
from target_system.demo_app.models import Room, Booking, RentPayment

app = FastAPI(
    title="Karamstay Demo Booking & Payment Service",
    description="Target microservice used by Project UMBRELLA to demonstrate autonomous fault diagnosis and self-healing.",
    version="1.0.0"
)


class BookingRequest(BaseModel):
    tenant_name: str = Field(..., example="Aarav Sharma")
    room_number: str = Field(default="ROOM-101")


class PaymentRequest(BaseModel):
    booking_id: int = Field(default=1)
    tenant_name: str = Field(..., example="Aarav Sharma")
    amount: float = Field(default=8500.0)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "demo_booking_service",
        "pool_size": config.POOL_SIZE,
        "max_overflow": config.MAX_OVERFLOW,
        "pool_timeout": config.POOL_TIMEOUT
    }


@app.get("/metrics")
def metrics():
    checkedout = engine.pool.checkedout() if engine and hasattr(engine, "pool") else 0
    size = engine.pool.size() if engine and hasattr(engine, "pool") else config.POOL_SIZE
    return {
        "pool_size": size,
        "checked_out_connections": checkedout,
        "overflow": engine.pool.overflow() if engine and hasattr(engine, "pool") else 0,
        "utilization_pct": round((checkedout / max(size, 1)) * 100.0, 1)
    }


@app.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    rooms = db.query(Room).limit(10).all()
    return [{"id": r.id, "room_number": r.room_number, "rent": r.monthly_rent, "available": r.is_available} for r in rooms]


@app.post("/book-room", status_code=status.HTTP_201_CREATED)
def book_room(req: BookingRequest, db: Session = Depends(get_db)):
    # Simulates real DB transaction latency (holds connection for 0.25s)
    time.sleep(0.25)
    room = db.query(Room).filter(Room.room_number == req.room_number).first()
    if not room:
        room = db.query(Room).first()

    booking = Booking(
        tenant_name=req.tenant_name,
        room_id=room.id if room else 1,
        status="confirmed"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "tenant_name": booking.tenant_name,
        "room_id": booking.room_id,
        "status": booking.status,
        "timestamp": booking.created_at.isoformat()
    }


@app.post("/pay-rent", status_code=status.HTTP_201_CREATED)
def pay_rent(req: PaymentRequest, db: Session = Depends(get_db)):
    time.sleep(0.25)
    payment = RentPayment(
        booking_id=req.booking_id,
        tenant_name=req.tenant_name,
        amount=req.amount,
        status="completed",
        transaction_ref=f"TXN-{uuid.uuid4().hex[:8].upper()}"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "tenant_name": payment.tenant_name,
        "amount": payment.amount,
        "transaction_ref": payment.transaction_ref,
        "status": payment.status
    }


@app.post("/reset")
def reset_db():
    init_db()
    return {"message": "Database and connection pool reset successfully."}

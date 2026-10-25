"""
Target Demo Application: Data Models
SQLAlchemy ORM models representing rooms, bookings, and rent payments.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(50), unique=True, index=True, nullable=False)
    room_type = Column(String(50), default="Single Bed Standard")
    monthly_rent = Column(Float, default=8500.0)
    is_available = Column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(100), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    status = Column(String(50), default="confirmed")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RentPayment(Base):
    __tablename__ = "rent_payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    tenant_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="completed")
    transaction_ref = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

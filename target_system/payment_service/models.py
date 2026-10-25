"""
Payment Service Database Models
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from target_system.payment_service.database import Base

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(30), default="COMPLETED")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

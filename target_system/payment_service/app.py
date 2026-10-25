"""
Payment Processing Microservice
FastAPI service configured with a strict connection pool limit (pool_size=2).
"""

import time
import logging
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import TimeoutError as DBTimeoutError

from target_system.payment_service.database import engine, Base, get_db
from target_system.payment_service.models import PaymentTransaction
from target_system.payment_service import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("payment_service")

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Processing Service", version="1.0.0")

class ChargeRequest(BaseModel):
    customer_name: str
    amount: float

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "payment-service",
        "pool_size": config.POOL_SIZE,
        "max_overflow": config.MAX_OVERFLOW
    }

@app.post("/api/v1/payments/charge", status_code=status.HTTP_201_CREATED)
def process_payment(charge: ChargeRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    logger.info(f"Received charge request for customer '{charge.customer_name}' (${charge.amount})")
    
    try:
        # Simulate external payment gateway & database lock duration (1.5s)
        time.sleep(1.5)
        
        # Record transaction in database
        tx = PaymentTransaction(customer_name=charge.customer_name, amount=charge.amount, status="SUCCESS")
        db.add(tx)
        db.commit()
        db.refresh(tx)
        
        elapsed = time.time() - start_time
        logger.info(f"Payment successful for '{charge.customer_name}' in {elapsed:.2f}s (TxID: {tx.id})")
        return {
            "status": "SUCCESS",
            "transaction_id": tx.id,
            "customer": charge.customer_name,
            "amount": charge.amount,
            "processing_time": round(elapsed, 2)
        }
        
    except DBTimeoutError as e:
        logger.error(f"DATABASE TIMEOUT: Pool limit exceeded for customer '{charge.customer_name}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection pool exhausted: QueuePool limit of size {config.POOL_SIZE} reached."
        )
    except Exception as e:
        logger.error(f"UNHANDLED ERROR processing payment for '{charge.customer_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

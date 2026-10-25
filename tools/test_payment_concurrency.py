"""
Project UMBRELLA: Real Concurrency Stress Test on Target Payment Service
Simulates 5 customers attempting to pay simultaneously when the connection pool can only handle 2.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy.exc import TimeoutError as DBTimeoutError



WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

from target_system.payment_service import database
from target_system.payment_service.models import PaymentTransaction
from target_system.payment_service import config

# Ensure tables are created
database.Base.metadata.create_all(bind=database.engine)

CUSTOMERS = [
    {"customer_name": "Customer-1 (Alice)", "amount": 49.99},
    {"customer_name": "Customer-2 (Bob)", "amount": 89.50},
    {"customer_name": "Customer-3 (Charlie)", "amount": 120.00},
    {"customer_name": "Customer-4 (Diana)", "amount": 35.25},
    {"customer_name": "Customer-5 (Evan)", "amount": 210.00},
]

def simulate_charge(customer_data):
    start = time.time()
    customer = customer_data["customer_name"]
    amount = customer_data["amount"]
    
    # Each concurrent customer request attempts to acquire a DB connection from QueuePool
    db = None
    try:
        db = database.SessionLocal()
        # Force connection checkout from pool
        conn = db.connection()
        
        # Simulate payment gateway lock & processing delay (1.5 seconds)
        time.sleep(1.5)
        
        tx = PaymentTransaction(customer_name=customer, amount=amount, status="SUCCESS")
        db.add(tx)
        db.commit()
        db.refresh(tx)
        
        elapsed = round(time.time() - start, 2)
        return {
            "customer": customer,
            "status_code": 201,
            "transaction_id": tx.id,
            "detail": "Payment Successful",
            "latency": elapsed
        }
    except DBTimeoutError as e:
        elapsed = round(time.time() - start, 2)
        return {
            "customer": customer,
            "status_code": 500,
            "transaction_id": None,
            "detail": f"Database Pool Timeout: QueuePool limit of size {config.POOL_SIZE} reached (timeout={config.POOL_TIMEOUT}s)",
            "latency": elapsed
        }
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return {
            "customer": customer,
            "status_code": 500,
            "transaction_id": None,
            "detail": str(e),
            "latency": elapsed
        }
    finally:
        if db:
            db.close()

def run_concurrency_test():
    print("=" * 80)
    print("TARGET SYSTEM LIVE CONCURRENCY TEST: 5 CUSTOMERS PAYING AT THE SAME TIME")
    print(f"Service Database Config: POOL_SIZE = {config.POOL_SIZE} | MAX_OVERFLOW = {config.MAX_OVERFLOW} | TIMEOUT = {config.POOL_TIMEOUT}s")
    print("=" * 80)
    
    print("\nFiring 5 concurrent payment requests simultaneously...\n")
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(simulate_charge, CUSTOMERS))
        
    total_time = round(time.time() - t0, 2)
    
    success_count = 0
    failure_count = 0
    
    print(f"{'Customer':<24} | {'Status':<12} | {'Latency':<8} | {'Result Summary'}")
    print("-" * 80)
    for res in results:
        status_label = "201 OK" if res["status_code"] == 201 else f"500 FAILED"
        if res["status_code"] == 201:
            success_count += 1
            summary = f"TxID #{res['transaction_id']} - Payment Approved"
        else:
            failure_count += 1
            summary = res["detail"][:45] + "..."
            
        print(f"{res['customer']:<24} | {status_label:<12} | {res['latency']:>5.2f}s  | {summary}")
        
    print("-" * 80)
    print(f"Total Test Time: {total_time}s | Successful: {success_count}/5 | Crashed/Failed: {failure_count}/5")
    print(f"Observed Incident Failure Rate: {(failure_count / 5.0) * 100:.1f}%")
    print("=" * 80)

    return results

if __name__ == "__main__":
    run_concurrency_test()

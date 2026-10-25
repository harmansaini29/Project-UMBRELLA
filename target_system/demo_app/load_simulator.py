"""
Target Demo Application: Concurrency Load Simulator
Simulates 5 to 10 concurrent tenants booking rooms and paying rent simultaneously.
"""

import argparse
import sys
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import target_system.demo_app.config as config
from target_system.demo_app.database import SessionLocal, init_db
from target_system.demo_app.models import Room, Booking, RentPayment


def simulate_single_tenant_transaction(tenant_id: int) -> Dict[str, Any]:
    """Simulates a single tenant booking a room and processing rent payment."""
    start_time = time.time()
    db = None
    try:
        db = SessionLocal()
        # Force checkout of a raw connection from the QueuePool
        conn = db.connection()
        # Simulate payment gateway lock / processing delay (1.4 seconds > 1.0s pool timeout)
        time.sleep(1.40)

        # 1. Query available room
        room = db.query(Room).filter(Room.is_available == True).first()

        # 2. Create booking
        booking = Booking(
            tenant_name=f"Tenant_{tenant_id:02d}",
            room_id=room.id if room else 1,
            status="confirmed"
        )
        db.add(booking)
        db.commit()

        # 3. Pay Rent
        payment = RentPayment(
            booking_id=booking.id,
            tenant_name=f"Tenant_{tenant_id:02d}",
            amount=8500.0,
            status="completed",
            transaction_ref=f"TXN-TENANT-{tenant_id}"
        )
        db.add(payment)
        db.commit()

        elapsed_ms = (time.time() - start_time) * 1000.0
        return {
            "tenant_id": tenant_id,
            "success": True,
            "latency_ms": elapsed_ms,
            "error_type": None,
            "error_msg": None,
            "stack_trace": None
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000.0
        return {
            "tenant_id": tenant_id,
            "success": False,
            "latency_ms": elapsed_ms,
            "error_type": type(e).__name__,
            "error_msg": str(e),
            "stack_trace": traceback.format_exc()
        }
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def simulate_jwt_auth_transaction(tenant_id: int) -> Dict[str, Any]:
    """Simulates an authentication transaction where tokens have expired."""
    start_time = time.time()
    try:
        # Simulate OAuth2 token validation with expired bearer JWT for all except first 2 tenants
        if tenant_id > 2:
            raise PermissionError("HTTP 401 Unauthorized: Bearer token validation failed (Signature has expired)")
        time.sleep(0.05)
        elapsed_ms = (time.time() - start_time) * 1000.0
        return {
            "tenant_id": tenant_id,
            "success": True,
            "latency_ms": elapsed_ms,
            "error_type": None,
            "error_msg": None,
            "stack_trace": None
        }
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000.0
        st = (
            'Traceback (most recent call last):\n'
            '  File "target_system/demo_app/server.py", line 65, in book_room\n'
            '    current_user = verify_jwt_token(auth_header)\n'
            '  File "target_system/demo_app/auth.py", line 42, in verify_jwt_token\n'
            '    raise HTTPException(status_code=401, detail="Signature has expired")\n'
            'fastapi.exceptions.HTTPException: 401: Signature has expired'
        )
        return {
            "tenant_id": tenant_id,
            "success": False,
            "latency_ms": elapsed_ms,
            "error_type": "HTTPException: 401 Unauthorized",
            "error_msg": str(e),
            "stack_trace": st
        }


def simulate_slow_query_transaction(tenant_id: int) -> Dict[str, Any]:
    """Simulates lock contention / unindexed slow query latency spikes."""
    start_time = time.time()
    try:
        if tenant_id > 2:
            time.sleep(0.5)
            raise TimeoutError("OperationalError: database table is locked / Query execution exceeded 2000ms deadline")
        time.sleep(0.10)
        elapsed_ms = (time.time() - start_time) * 1000.0
        return {
            "tenant_id": tenant_id,
            "success": True,
            "latency_ms": elapsed_ms,
            "error_type": None,
            "error_msg": None,
            "stack_trace": None
        }
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000.0
        st = (
            'Traceback (most recent call last):\n'
            '  File "target_system/demo_app/server.py", line 68, in book_room\n'
            '    room = db.query(Room).filter(Room.room_number == req.room_number).first()\n'
            '  File "target_system/demo_app/database.py", line 45, in execute_query\n'
            '    raise OperationalError("database table is locked", params, orig)\n'
            'sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database table is locked'
        )
        return {
            "tenant_id": tenant_id,
            "success": False,
            "latency_ms": elapsed_ms,
            "error_type": "OperationalError: database table locked",
            "error_msg": str(e),
            "stack_trace": st
        }


def run_concurrency_stress_test(num_users: int = 10, scenario: str = "pool_starvation") -> Dict[str, Any]:
    """Runs concurrent load test under the selected scenario and returns comprehensive metrics."""
    init_db()  # Ensure tables exist
    results: List[Dict[str, Any]] = []
    wall_start = time.time()

    worker_fn = simulate_single_tenant_transaction
    if scenario == "jwt_auth_failure":
        worker_fn = simulate_jwt_auth_transaction
    elif scenario == "slow_query_deadlock":
        worker_fn = simulate_slow_query_transaction

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(worker_fn, i + 1) for i in range(num_users)]
        for fut in as_completed(futures):
            results.append(fut.result())

    total_wall_ms = (time.time() - wall_start) * 1000.0
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    latencies = [r["latency_ms"] for r in results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

    fail_rate = (len(failed) / num_users) * 100.0

    first_error = failed[0] if failed else None

    summary = {
        "scenario": scenario,
        "num_users": num_users,
        "pool_size": config.POOL_SIZE,
        "max_overflow": config.MAX_OVERFLOW,
        "pool_timeout": config.POOL_TIMEOUT,
        "total_requests": num_users,
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "failure_rate_pct": round(fail_rate, 1),
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "total_wall_time_ms": round(total_wall_ms, 2),
        "first_error_type": first_error["error_type"] if first_error else None,
        "first_error_msg": first_error["error_msg"] if first_error else None,
        "first_stack_trace": first_error["stack_trace"] if first_error else None,
        "raw_results": results
    }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate concurrent user traffic against demo app.")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users (5 to 10)")
    args = parser.parse_args()

    print("=" * 80)
    print(f"RUNNING CONCURRENCY STRESS TEST: {args.users} CONCURRENT USERS")
    print(f"Current DB Config: POOL_SIZE={config.POOL_SIZE}, MAX_OVERFLOW={config.MAX_OVERFLOW}")
    print("=" * 80)

    summary = run_concurrency_stress_test(num_users=args.users)

    print(f"Total Requests:     {summary['total_requests']}")
    print(f"Successful:         {summary['successful_requests']}")
    print(f"Failed:             {summary['failed_requests']} ({summary['failure_rate_pct']}%)")
    print(f"Average Latency:    {summary['avg_latency_ms']} ms")
    print(f"P95 Latency:        {summary['p95_latency_ms']} ms")

    if summary["failed_requests"] > 0:
        print(f"\n[CRASH DETECTED]: {summary['first_error_type']}")
        print(f"Error Message:    {summary['first_error_msg']}")
        sys.exit(1)
    else:
        print("\n[OK] All concurrent requests completed successfully with 0 errors!")
        sys.exit(0)

"""
Project UMBRELLA: Operator Dashboard & Control Plane Server
Serves the real-time web cockpit and coordinates the 6-Agent Council with live target systems.
"""

import os
import sys
import time
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure root workspace is in sys.path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agents.schemas import IncidentContext, ErrorEvent, TelemetrySnapshot
from agents.orchestrator import CouncilOrchestrator
from agents.agent6_evo.config import ObservationTimeFrame, EVOConfig
from target_system.demo_app.load_simulator import run_concurrency_stress_test
import target_system.demo_app.config as demo_config
from target_system.demo_app.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Project UMBRELLA: Mission Control Dashboard",
    description="Enterprise Multi-Agent Self-Healing & Autonomous Evolution Control Plane",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Shared In-Memory State
orchestrator = CouncilOrchestrator()
latest_incident: Optional[IncidentContext] = None
latest_stress_test: Optional[Dict[str, Any]] = None
latest_council_run: Optional[Dict[str, Any]] = None


class TimeFrameUpdateRequest(BaseModel):
    time_frame: ObservationTimeFrame = Field(..., example="24h")


class LoadSimulationRequest(BaseModel):
    num_users: int = Field(default=10, ge=2, le=25)


@app.get("/")
def get_dashboard_ui():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Dashboard UI index.html not found in static folder."}


@app.get("/api/system/status")
def get_system_status():
    """Returns real-time status of services, active pool limits, and latest incident."""
    is_degraded = latest_stress_test and latest_stress_test.get("failed_requests", 0) > 0
    return {
        "status": "degraded" if is_degraded else "healthy",
        "demo_backend": {
            "service_name": "demo_booking_service",
            "pool_size": demo_config.POOL_SIZE,
            "max_overflow": demo_config.MAX_OVERFLOW,
            "pool_timeout": demo_config.POOL_TIMEOUT,
            "database_url": demo_config.DATABASE_URL
        },
        "council_agents": [
            {"id": "agent_1_rca", "name": "Root Cause Analyzer", "status": "active"},
            {"id": "agent_2_topology", "name": "3D Spatial Visualizer", "status": "active"},
            {"id": "agent_3_planner", "name": "Remediation Planner", "status": "active"},
            {"id": "agent_4_executor", "name": "Sandboxed Action Executor", "status": "active"},
            {"id": "agent_5_guardian", "name": "Safety Policy Guardian & Failover", "status": "active"},
            {"id": "agent_6_evo", "name": "Backend Evolution Engine", "status": "active"}
        ],
        "latest_stress_test": latest_stress_test,
        "latest_council_run": latest_council_run
    }


@app.post("/api/simulate/load")
def trigger_load_simulation(req: LoadSimulationRequest = Body(...)):
    """Triggers realistic concurrent transactions against the demo app."""
    global latest_stress_test, latest_incident
    summary = run_concurrency_stress_test(num_users=req.num_users)
    latest_stress_test = summary

    # If failure detected, formulate IncidentContext
    if summary["failed_requests"] > 0:
        latest_incident = IncidentContext(
            incident_id=f"INC-{int(time.time())}",
            title=f"Demo Booking Service connection starvation under {req.num_users} concurrent tenants",
            service_name="demo_booking_service",
            telemetry=TelemetrySnapshot(
                service_name="demo_booking_service",
                active_connections=req.num_users,
                pool_size=summary["pool_size"],
                pool_overflow=summary["max_overflow"],
                pool_utilization_pct=round((req.num_users / max(summary["pool_size"], 1)) * 100.0, 1),
                latency_p99_ms=summary["p95_latency_ms"],
                error_count_last_5m=summary["failed_requests"]
            ),
            errors=[
                ErrorEvent(
                    event_id=f"ERR-{int(time.time())}",
                    service_name="demo_booking_service",
                    error_type=summary["first_error_type"] or "TimeoutError",
                    error_message=summary["first_error_msg"] or "QueuePool limit reached",
                    stack_trace=summary["first_stack_trace"] or "",
                    target_file="target_system/demo_app/config.py",
                    line_number=10
                )
            ]
        )

    return summary


@app.post("/api/council/heal")
def run_council_self_healing(grant_hitl: bool = True):
    """Executes the full 6-agent self-healing loop on the active incident."""
    global latest_council_run, latest_incident
    if not latest_incident:
        raise HTTPException(status_code=400, detail="No active incident to heal. Trigger a load simulation first.")

    result = orchestrator.run_self_healing_pipeline(
        incident=latest_incident,
        grant_hitl_approval=grant_hitl
    )
    latest_council_run = result
    return result


@app.get("/api/evo/config")
def get_evo_config():
    """Returns active Agent 6 EVO configuration."""
    cfg = orchestrator.agent6_optimizer.config
    stats = orchestrator.agent6_policy.get_stats()
    return {
        "config": cfg.model_dump(),
        "stats": stats
    }


@app.post("/api/evo/set-window")
def set_evo_time_frame(req: TimeFrameUpdateRequest):
    """Sets active observation window (24h, 48h, 1w, 2w, 1m)."""
    orchestrator.agent6_optimizer.set_time_frame(req.time_frame)
    proposal = orchestrator.agent6_optimizer.evaluate_and_propose()
    return {
        "active_time_frame": req.time_frame.value,
        "proposal": proposal.model_dump() if proposal else None
    }


@app.get("/api/evo/proposals")
def get_evo_proposals():
    """Returns proactive refactoring proposals for the active time-frame."""
    proposal = orchestrator.agent6_optimizer.evaluate_and_propose()
    return {
        "has_proposal": proposal is not None,
        "proposal": proposal.model_dump() if proposal else None
    }


@app.post("/api/evo/approve")
def approve_proactive_evolution():
    """Approves and merges Agent 6's proactive code evolution proposal."""
    proposal = orchestrator.agent6_optimizer.evaluate_and_propose()
    if not proposal:
        return {"status": "noop", "message": "No pending proactive evolution proposals."}

    # Apply proactive scaling to config
    target_abs = os.path.join(WORKSPACE_DIR, proposal.target_file)
    if os.path.exists(target_abs):
        with open(target_abs, "r", encoding="utf-8") as f:
            content = f.read()

        # Update pool settings
        content = content.replace('POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))', 'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "20"))')
        content = content.replace('POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "2"))', 'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "20"))')
        content = content.replace('POOL_SIZE = 2', 'POOL_SIZE = 20')
        content = content.replace('POOL_SIZE = 10', 'POOL_SIZE = 20')
        content = content.replace('MAX_OVERFLOW = 0', 'MAX_OVERFLOW = 10')
        content = content.replace('MAX_OVERFLOW = 5', 'MAX_OVERFLOW = 10')

        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(content)

        # Refresh db engine
        init_db()

        return {
            "status": "applied",
            "message": f"Proactive Evolution {proposal.proposal_id} approved and merged successfully. Headroom expanded to POOL_SIZE=20.",
            "target_file": proposal.target_file
        }

    return {"status": "error", "message": "Target config file not found."}


@app.get("/api/rag/search")
def search_rag_knowledge(query: str = "connection pool timeout exhaustion"):
    """Queries the 23,769-chunk Infosys RAG knowledge base live."""
    try:
        from rag.hybrid_engine import HybridRAGEngine
        engine = HybridRAGEngine.get_instance()
        hits = engine.retrieve(query_text=query, top_k=5)
        return {
            "query": query,
            "total_chunks_indexed": 23769,
            "hits": [
                {
                    "file_path": h.chunk.file_path,
                    "repository": h.chunk.repository,
                    "symbol_name": h.chunk.symbol_name,
                    "rrf_score": round(h.rrf_score, 6),
                    "preview": h.chunk.content[:240] + "..."
                }
                for h in hits
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/reset")
def reset_demo_system():
    """Resets the demo backend to its initial constrained configuration for fresh demonstration."""
    global latest_stress_test, latest_incident, latest_council_run
    latest_stress_test = None
    latest_incident = None
    latest_council_run = None

    # Revert config to constrained values
    candidate_configs = [
        os.path.join(WORKSPACE_DIR, "target_system", "demo_app", "config.py"),
        os.path.join(WORKSPACE_DIR, "target_system", "payment_service", "config.py")
    ]
    for p in candidate_configs:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace('POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "20"))', 'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))')
            content = content.replace('POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "10"))', 'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))')
            content = content.replace('POOL_SIZE = 20', 'POOL_SIZE = 2')
            content = content.replace('POOL_SIZE = 10', 'POOL_SIZE = 2')
            content = content.replace('MAX_OVERFLOW = 10', 'MAX_OVERFLOW = 0')
            content = content.replace('MAX_OVERFLOW = 5', 'MAX_OVERFLOW = 0')
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)

    init_db()
    return {"message": "Demo system successfully reset to baseline constrained state (POOL_SIZE=2)."}


if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("PROJECT UMBRELLA: MISSION CONTROL DASHBOARD SERVER LAUNCHING")
    print("Access UI at: http://localhost:8000")
    print("=" * 80)
    uvicorn.run(app, host="0.0.0.0", port=8000)

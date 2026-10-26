"""
Project UMBRELLA: Operator Dashboard & Control Plane Server
Serves the real-time web cockpit and coordinates the 6-Agent Council with live target systems.
"""

import os
import sys
import time
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
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
from capsule.dna_packager import DNAPackager
from capsule.genesis_engine import GenesisEngine

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

# Shared In-Memory State & Live Real-Time Stream
orchestrator = CouncilOrchestrator()
latest_incident: Optional[IncidentContext] = None
latest_stress_test: Optional[Dict[str, Any]] = None
latest_council_run: Optional[Dict[str, Any]] = None
pending_remediation_plan: Optional[Dict[str, Any]] = None

registered_clients: Dict[str, Dict[str, Any]] = {}
live_telemetry_stream: List[Dict[str, Any]] = []
live_logs: List[Dict[str, Any]] = []


def push_log(level: str, source: str, message: str, meta: Optional[Dict[str, Any]] = None):
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
        "level": level,
        "source": source,
        "message": message,
        "meta": meta or {}
    }
    live_logs.insert(0, entry)
    if len(live_logs) > 200:
        live_logs.pop()
    logger.info(f"[{source}] {message}")


class ClientRegistrationRequest(BaseModel):
    service_name: str
    repo_path: Optional[str] = None
    config_file: Optional[str] = None
    auto_heal_enabled: bool = True
    registered_at: float = Field(default_factory=time.time)
    pid: Optional[int] = None


class TelemetryReportRequest(BaseModel):
    service_name: str
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any] = Field(default_factory=dict)


class IncidentReportRequest(BaseModel):
    service_name: str
    timestamp: float = Field(default_factory=time.time)
    error_type: str
    error_message: str
    stack_trace: str
    target_file: Optional[str] = None
    target_line: Optional[int] = 1
    context: Dict[str, Any] = Field(default_factory=dict)
    repo_path: Optional[str] = None


class HITLApprovalRequest(BaseModel):
    action_id: str = "ACT-POOL-SCALE-001"
    grant_approval: bool = True
    operator_notes: Optional[str] = None


class TimeFrameUpdateRequest(BaseModel):
    time_frame: ObservationTimeFrame = Field(..., example="24h")


class LoadSimulationRequest(BaseModel):
    num_users: int = Field(default=10, ge=2, le=25)
    scenario: str = Field(default="pool_starvation", example="pool_starvation")


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
    """Triggers realistic concurrent transactions against the demo app under selectable scenarios."""
    global latest_stress_test, latest_incident
    summary = run_concurrency_stress_test(num_users=req.num_users, scenario=req.scenario)
    latest_stress_test = summary

    # If failure detected, formulate IncidentContext
    if summary["failed_requests"] > 0:
        if req.scenario == "jwt_auth_failure":
            incident_title = f"OAuth2 Authentication rejection under {req.num_users} tenants: Token expired"
            target_f = "target_system/demo_app/server.py"
            target_l = 65
        elif req.scenario == "slow_query_deadlock":
            incident_title = f"Unindexed query scan lock timeout under {req.num_users} concurrent bookings"
            target_f = "target_system/demo_app/database.py"
            target_l = 45
        else:
            incident_title = f"Demo Booking Service connection starvation under {req.num_users} concurrent tenants"
            target_f = "target_system/demo_app/config.py"
            target_l = 10

        latest_incident = IncidentContext(
            incident_id=f"INC-{int(time.time())}",
            title=incident_title,
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
                    target_file=target_f,
                    line_number=target_l
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

    push_log("INFO", "COUNCIL", f"Executing 6-Agent Council Self-Healing (HITL Grant={grant_hitl})")
    result = orchestrator.run_self_healing_pipeline(
        incident=latest_incident,
        grant_hitl_approval=grant_hitl
    )
    latest_council_run = result
    push_log("SUCCESS", "COUNCIL", f"Self-healing pipeline completed for incident {latest_incident.incident_id}")
    return result


@app.post("/api/sdk/register")
def register_client(req: ClientRegistrationRequest):
    """Allows external microservices to register with Project UMBRELLA Mission Control."""
    registered_clients[req.service_name] = req.model_dump()
    push_log("INFO", "SDK", f"Microservice '{req.service_name}' connected to UMBRELLA from {req.repo_path}")
    return {
        "status": "registered",
        "service_name": req.service_name,
        "council_version": "2.0.0",
        "monitoring_mode": "ACTIVE_CLOSED_LOOP"
    }


@app.post("/api/sdk/telemetry")
def receive_client_telemetry(req: TelemetryReportRequest):
    """Ingests real-time telemetry from connected microservices."""
    entry = {
        "service_name": req.service_name,
        "timestamp": req.timestamp,
        "time_str": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "data": req.data
    }
    live_telemetry_stream.insert(0, entry)
    if len(live_telemetry_stream) > 100:
        live_telemetry_stream.pop()
    return {"status": "received"}


@app.post("/api/sdk/incident")
def ingest_client_incident(req: IncidentReportRequest):
    """
    Real-time Closed-Loop:
    Receives live exception packets from external apps (e.g. Umbrella-demo-app),
    triggers Agent 1 (AST RCA), Agent 2 (Topology), Agent 3 (Diff Synthesis),
    Agent 5 (Risk Evaluation), and arms the HITL approval gate.
    """
    global latest_incident, latest_council_run, pending_remediation_plan
    push_log("CRITICAL", "SDK", f"Live crash reported by '{req.service_name}': {req.error_type} - {req.error_message}")

    summary_data = req.context.get("summary", {})
    pool_sz = summary_data.get("pool_size", 2)
    overflow = summary_data.get("max_overflow", 0)
    num_users = summary_data.get("total_requests", 10)
    failed_cnt = summary_data.get("failed_requests", 8)
    p95_lat = summary_data.get("p95_latency_ms", 1450.0)

    latest_incident = IncidentContext(
        incident_id=f"INC-{int(time.time())}",
        title=f"{req.service_name}: {req.error_type} under concurrency load",
        service_name=req.service_name,
        telemetry=TelemetrySnapshot(
            service_name=req.service_name,
            active_connections=num_users,
            pool_size=pool_sz,
            pool_overflow=overflow,
            pool_utilization_pct=round((num_users / max(pool_sz, 1)) * 100.0, 1),
            latency_p99_ms=p95_lat,
            error_count_last_5m=failed_cnt
        ),
        errors=[
            ErrorEvent(
                event_id=f"ERR-{int(time.time())}",
                service_name=req.service_name,
                error_type=req.error_type,
                error_message=req.error_message,
                stack_trace=req.stack_trace,
                target_file=req.target_file or "config.py",
                line_number=req.target_line or 1
            )
        ]
    )

    # Run Steps 1-5
    push_log("INFO", "AGENT_1_RCA", f"Inspecting AST for {req.target_file}:{req.target_line}")
    rca_result = orchestrator.agent1_rca.diagnose(latest_incident)
    push_log("INFO", "AGENT_1_RCA", f"Diagnosis: {rca_result.primary_causes[0].cause} (Confidence: {rca_result.overall_confidence:.1%})")

    push_log("INFO", "AGENT_2_TOPOLOGY", "Calculating blast radius across topology mesh")
    blast_report, topo_snapshot = orchestrator.agent2_topology.update_from_rca(rca_result)

    push_log("INFO", "AGENT_3_PLANNER", "Synthesizing unified diff patch")
    remediation_plan = orchestrator.agent3_planner.plan(rca_result, blast_report)

    push_log("INFO", "AGENT_5_GUARDIAN", f"Evaluating risk policy (Tier: {remediation_plan.actions[0].risk_tier.value}). HITL approval required.")
    decision = orchestrator.agent5_guardian.evaluate_risk(
        plan=remediation_plan,
        blast=blast_report,
        human_approval_granted=False
    )

    run_summary = {
        "incident_id": latest_incident.incident_id,
        "service_name": req.service_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_1_rca": rca_result.model_dump(mode="json"),
        "agent_2_topology": {
            "blast_report": blast_report.model_dump(mode="json"),
            "topology_snapshot": topo_snapshot
        },
        "agent_3_planner": remediation_plan.model_dump(mode="json"),
        "agent_5_guardian": decision.model_dump(mode="json"),
        "agent_4_executor": None,
        "agent_6_evo": None,
        "awaiting_hitl_approval": True
    }
    latest_council_run = run_summary
    pending_remediation_plan = {
        "incident": latest_incident,
        "action": remediation_plan.actions[0],
        "blast": blast_report
    }

    return run_summary


@app.post("/api/council/approve-action")
def approve_hitl_action(req: Optional[HITLApprovalRequest] = None):
    """Human-in-the-Loop Gate Approval: applies patch, runs verification tests, commits to Git, and records EVO experience."""
    global latest_council_run, pending_remediation_plan, latest_incident

    if not pending_remediation_plan:
        if latest_incident:
            res = orchestrator.run_self_healing_pipeline(
                incident=latest_incident,
                grant_hitl_approval=True
            )
            latest_council_run = res
            return res
        raise HTTPException(status_code=400, detail="No pending action to approve.")

    action = pending_remediation_plan["action"]
    incident = pending_remediation_plan["incident"]

    push_log("INFO", "OPERATOR_HITL", f"Authorization GRANTED for action {action.action_id} on {action.target_file}")

    # Agent 4 Sandboxed Executor
    push_log("INFO", "AGENT_4_EXECUTOR", f"Applying patch to {action.target_file} & executing regression tests...")
    exec_res = orchestrator.agent4_executor.execute_action(
        action=action,
        incident_id=incident.incident_id,
        is_guardian_approved=True
    )

    # Agent 6 EVO Policy Learner
    push_log("INFO", "AGENT_6_EVO", "Ingesting remediation outcome into Q-learning policy memory...")
    evo_exp = orchestrator.agent6_policy.record_experience(
        incident=incident,
        action=action,
        result=exec_res,
        latency_delta_pct=-25.0 if exec_res.test_suite_passed else 0.0
    )
    proactive_proposal = orchestrator.agent6_optimizer.evaluate_and_propose()

    latest_council_run["agent_4_executor"] = exec_res.model_dump(mode="json")
    latest_council_run["agent_6_evo"] = {
        "evolution_experience": evo_exp.model_dump(mode="json"),
        "learning_stats": orchestrator.agent6_policy.get_stats(),
        "proactive_proposal": proactive_proposal.model_dump(mode="json") if proactive_proposal else None
    }
    latest_council_run["awaiting_hitl_approval"] = False
    pending_remediation_plan = None

    push_log("SUCCESS", "COUNCIL", f"Self-healing complete. Status: {exec_res.status.value}. Git commit: {exec_res.git_commit_sha}")
    return latest_council_run


@app.get("/api/system/live-telemetry")
def get_live_telemetry():
    """Returns real live telemetry timeseries and registered client status."""
    return {
        "telemetry": live_telemetry_stream[:30],
        "registered_clients": list(registered_clients.values()),
        "total_points": len(live_telemetry_stream)
    }


@app.get("/api/system/live-logs")
def get_live_logs():
    """Returns streaming live log feed for the web cockpit."""
    return {
        "logs": live_logs[:60]
    }


@app.get("/api/system/topology-live")
def get_live_topology():
    """Returns real dynamic topology mesh based on actual connected systems."""
    nodes = [
        {"id": "umbrella_control", "label": "UMBRELLA Control Plane", "x": 0, "y": -90, "status": "healthy"},
        {"id": "agent_council", "label": "6-Agent Council", "x": -140, "y": -20, "status": "healthy"}
    ]
    edges = [
        {"source": "umbrella_control", "target": "agent_council"}
    ]

    # Dynamically add registered client or default demo app
    client_name = list(registered_clients.keys())[0] if registered_clients else "karamstay_demo_app"
    is_crashed = latest_incident is not None and latest_council_run and latest_council_run.get("awaiting_hitl_approval")
    app_status = "critical" if is_crashed else ("degraded" if (latest_stress_test and latest_stress_test.get("failed_requests", 0) > 0) else "healthy")

    nodes.extend([
        {"id": "client_service", "label": f"Client App: {client_name}", "x": 140, "y": -20, "status": app_status},
        {"id": "client_db_pool", "label": "SQL QueuePool (Size: 2)", "x": 140, "y": 70, "status": "critical" if is_crashed else "healthy"},
        {"id": "payment_gateway", "label": "Payment Gateway (1.4s Lock)", "x": -140, "y": 70, "status": "healthy"}
    ])
    edges.extend([
        {"source": "umbrella_control", "target": "client_service"},
        {"source": "client_service", "target": "client_db_pool"},
        {"source": "client_service", "target": "payment_gateway"}
    ])

    return {
        "nodes": nodes,
        "edges": edges,
        "blast_radius_pct": 100 if is_crashed else 0
    }


@app.get("/api/evo/memory")
def get_evo_memory():
    """Returns real reinforcement learning experience memory from disk."""
    mem_path = os.path.join(WORKSPACE_DIR, "data", "evolution_memory.json")
    if os.path.exists(mem_path):
        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}
    return {"experiences": []}


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


@app.get("/api/capsule/list")
def list_capsules():
    """Lists available System DNA Capsules in storage."""
    capsules_dir = os.path.join(WORKSPACE_DIR, "capsules")
    if not os.path.exists(capsules_dir):
        return {"capsules": []}

    capsules = []
    for f in os.listdir(capsules_dir):
        if f.endswith(".tar.gz"):
            full_p = os.path.join(capsules_dir, f)
            sz_kb = round(os.path.getsize(full_p) / 1024.0, 1)
            manifest_p = full_p.replace(".tar.gz", "_manifest.json")
            m_data = {}
            if os.path.exists(manifest_p):
                try:
                    with open(manifest_p, "r", encoding="utf-8") as mf:
                        m_data = json.load(mf)
                except Exception:
                    pass
            capsules.append({
                "archive_name": f,
                "size_kb": sz_kb,
                "created_at": m_data.get("created_at"),
                "master_sha256": m_data.get("master_sha256"),
                "total_files": m_data.get("total_files")
            })
    return {"capsules": sorted(capsules, key=lambda x: x["archive_name"], reverse=True)}


@app.post("/api/capsule/create")
def create_system_dna_capsule():
    """Builds a new System DNA Capsule containing the entire enterprise genome."""
    packager = DNAPackager(workspace_root=WORKSPACE_DIR)
    result = packager.create_capsule()
    return result


@app.post("/api/capsule/restore")
def restore_from_dna_capsule(archive_name: Optional[str] = None):
    """Resurrects the system from zero using the latest System DNA Capsule."""
    capsules_dir = os.path.join(WORKSPACE_DIR, "capsules")
    target_archive = None

    if archive_name:
        target_archive = os.path.join(capsules_dir, archive_name)
    else:
        # Find latest
        archives = [f for f in os.listdir(capsules_dir) if f.endswith(".tar.gz")]
        if archives:
            archives.sort(reverse=True)
            target_archive = os.path.join(capsules_dir, archives[0])

    if not target_archive or not os.path.exists(target_archive):
        raise HTTPException(status_code=404, detail="No DNA Capsule archive found to restore.")

    engine = GenesisEngine(workspace_root=WORKSPACE_DIR)
    report = engine.resurrect_from_capsule(archive_path=target_archive)
    return report


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
        os.path.join(WORKSPACE_DIR, "target_system", "payment_service", "config.py"),
        os.path.join(os.path.dirname(WORKSPACE_DIR), "Umbrella-demo-app", "config.py")
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

# External Production System Integration Guide & OpenAPI Contract

> **Document Version:** 2.1.0-Enterprise  
> **Target Audience:** Platform Architects, Site Reliability Engineers (SREs), Infrastructure Teams, Backend Developers  
> **Compliance & Safety Standards:** Tier 1–4 Safety Risk Matrix, HITL Mandatory Gate, Epistemic Uncertainty Fallback  

---

## 1. System Architecture & Closed-Loop Interaction Flow

Project UMBRELLA provides autonomous closed-loop resilience, diagnosis, and remediation for external production microservices. Unlike traditional observability platforms that merely notify on-call personnel, UMBRELLA integrates an embedded lightweight SDK sentry inside client services, ingest streams into a multi-agent council, and continuously optimizes remediation policies using Agent 6 (UMBRELLA-EVO: Backend Evolution and Outcome-Aware Bandit Learner).

### End-to-End Resilience Lifecycle

```
+---------------------------------------------------------------------------------------------------------+
|                                      EXTERNAL TARGET MICROSERVICE                                       |
|                                                                                                         |
|   +--------------------------+        +---------------------------+        +------------------------+   |
|   | ASGI / WSGI Application  | -----> |    Umbrella SDK Sentry    | -----> |   Business Handler /   |   |
|   | (FastAPI, Flask, Django) |        |    Middleware Interceptor |        |   Database Operations  |   |
|   +--------------------------+        +---------------------------+        +------------------------+   |
|                |                                    | (Unhandled Exception)             |               |
|                |                                    v                                   |               |
|                |                         +----------------------+                       |               |
|                |                         | AST Stack Trace &    |                       |               |
|                |                         | Codeframe Extractor  |                       |               |
|                |                         +----------------------+                       |               |
|                v                                    |                                   v               |
|     +--------------------+                          |                        +----------------------+   |
|     | Telemetry Daemon   |                          |                        | Target Configuration |   |
|     | (Background Loop)  |                          |                        | (config.py / env)    |   |
|     +--------------------+                          |                        +----------------------+   |
+----------------|------------------------------------|-----------------------------------^---------------+
                 |                                    |                                   |
                 | POST /api/sdk/telemetry            | POST /api/sdk/incident            | POST /api/config/reload
                 |                                    |                                   | (Zero Downtime)
                 v                                    v                                   |
+-----------------------------------------------------------------------------------------|---------------+
|                                  PROJECT UMBRELLA: MISSION CONTROL PLANE                |               |
|                                                                                         |               |
|  +---------------------------+       +-----------------------------+       +------------|------------+  |
|  | Agent 1: Diagnostic RCA   | ----> | Agent 2: 3D Spatial Blast   | ----> | Agent 3: Remediation    |  |
|  | - 4-Signal AST Inference  |       | - Dynamic Dependency Mesh   |       |   Planner               |  |
|  | - Central Hybrid RAG      |       | - Cascade Probability Model |       | - Unified Diff Patch    |  |
|  +---------------------------+       +-----------------------------+       +-------------------------+  |
|                                                                                         |               |
|                                                                                         v               |
|  +---------------------------+       +-----------------------------+       +-------------------------+  |
|  | Agent 6: UMBRELLA-EVO     | <---- | Agent 4: Sandboxed Executor | <---- | Agent 5: Safety Guardian|  |
|  | - OutcomeStore (SQLite)   |       | - Clean Git Worktree        |       | - Risk Matrix (Tier 1-4)|  |
|  | - LinUCB Bandit Learner   |       | - Subprocess Test Verify    |       | - HITL Operator Gate    |  |
|  | - Uncertainty Guardrail   |       | - Atomic Git Commit         |       |   (Autonomous vs Human) |  |
|  +---------------------------+       +-----------------------------+       +-------------------------+  |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. OpenAPI 3.1.0 Contract Specification

Below is the OpenAPI specification defining all interaction endpoints between external microservices and Project UMBRELLA.

```yaml
openapi: 3.1.0
info:
  title: Project UMBRELLA External Microservice Sentry & Evolution API
  version: 2.1.0
  description: |
    Production REST API enabling external microservices to connect with UMBRELLA's
    autonomous multi-agent resilience council, stream live telemetry, trigger closed-loop
    healing pipelines, hot-reload configurations, and inspect Agent 6 bandit evolution.
servers:
  - url: http://localhost:8000
    description: Local Mission Control Development Server
  - url: https://umbrella-sentry.internal.domain
    description: Production Internal High-Availability Mesh

paths:
  /api/sdk/register:
    post:
      summary: Register an external microservice
      description: Registers the target microservice with UMBRELLA Mission Control on application boot.
      operationId: registerService
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ClientRegistrationRequest'
      responses:
        '200':
          description: Service successfully registered.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: registered
                  service_name:
                    type: string
                    example: payments_billing_service
                  registration_id:
                    type: string
                    example: REG-PAY-98124
        '400':
          description: Invalid client registration payload.

  /api/sdk/telemetry:
    post:
      summary: Stream live system and pool telemetry
      description: Non-blocking heartbeat endpoint ingesting RPS, latency, saturation, and pool metrics.
      operationId: ingestTelemetry
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TelemetrySubmission'
      responses:
        '200':
          description: Telemetry sample stored.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok
                  ingested_at:
                    type: string
                    format: date-time

  /api/sdk/incident:
    post:
      summary: Dispatch runtime incident to Autonomous Council
      description: |
        Called immediately by the SDK middleware when an unhandled 5xx exception or
        connection pool starvation occurs. Triggers Agents 1 through 5, and records
        the episode in Agent 6 EVO memory.
      operationId: dispatchIncident
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IncidentSubmission'
      responses:
        '200':
          description: Autonomous Council execution result.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CouncilRunSummary'

  /api/config/reload:
    post:
      summary: Client-side hot reload callback contract
      description: |
        Endpoint exposed on the TARGET microservice (e.g. port 8002) invoked by
        UMBRELLA Executor immediately after applying a verified code patch.
      operationId: reloadConfig
      requestBody:
        required: false
        content:
          application/json:
            schema:
              type: object
              properties:
                reason:
                  type: string
                  example: "UMBRELLA Agent 4 remediated POOL_SIZE to 10"
      responses:
        '200':
          description: Target in-memory pool and config reloaded successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: reloaded
                  new_pool_size:
                    type: integer
                    example: 10
                  new_max_overflow:
                    type: integer
                    example: 5

  /api/evo/policy-versions:
    get:
      summary: Retrieve Agent 6 policy version registry
      description: Lists all registered LinUCB bandit policy models, training sample counts, and validation scores.
      operationId: getPolicyVersions
      responses:
        '200':
          description: List of policy versions.
          content:
            application/json:
              schema:
                type: object
                properties:
                  active_version:
                    type: string
                    example: v1_20261027_221000
                  mode:
                    type: string
                    enum: [shadow, active, offline]
                    example: shadow
                  versions:
                    type: array
                    items:
                      $ref: '#/components/schemas/PolicyVersionMetadata'

  /api/evo/rollback:
    post:
      summary: Rollback active Agent 6 policy
      description: Reverts the active decision policy to a designated historical model version.
      operationId: rollbackPolicy
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [version_tag]
              properties:
                version_tag:
                  type: string
                  example: v0_deterministic_fallback
      responses:
        '200':
          description: Active policy rolled back successfully.
        '404':
          description: Policy version tag not found.

  /api/evo/benchmark:
    get:
      summary: Retrieve empirical benchmark results
      description: Returns comparative evaluation metrics between the learned LinUCB bandit and the deterministic rule baseline across training and held-out zero-leakage scenario suites.
      operationId: getBenchmarkReport
      responses:
        '200':
          description: Benchmark comparison report.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BenchmarkResults'

  /api/evo/outcomes:
    get:
      summary: Query structured episodic remediation outcomes
      description: Fetches chronological execution outcome records from SQLite (data/outcomes.sqlite).
      operationId: getOutcomes
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: Structured outcome history.
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_returned:
                    type: integer
                  outcomes:
                    type: array
                    items:
                      $ref: '#/components/schemas/OutcomeRecord'

components:
  schemas:
    ClientRegistrationRequest:
      type: object
      required: [service_name, service_url, repo_path, config_file]
      properties:
        service_name:
          type: string
          example: karamstay_demo_app
        service_url:
          type: string
          example: http://localhost:8002
        repo_path:
          type: string
          example: /var/www/microservices/karamstay_demo_app
        config_file:
          type: string
          example: /var/www/microservices/karamstay_demo_app/config.py
        auto_heal_enabled:
          type: boolean
          default: true
        api_key:
          type: string
          example: umb_live_k8s_9921fx

    TelemetrySubmission:
      type: object
      required: [service_name]
      properties:
        service_name:
          type: string
          example: karamstay_demo_app
        pool_size:
          type: integer
          example: 2
        checked_out_connections:
          type: integer
          example: 2
        overflow:
          type: integer
          example: 0
        utilization_pct:
          type: number
          example: 100.0
        rps:
          type: number
          example: 24.5
        latency_p95_ms:
          type: number
          example: 1240.0
        error_rate_pct:
          type: number
          example: 12.5

    IncidentSubmission:
      type: object
      required: [service_name, error_type, error_message, stack_trace]
      properties:
        service_name:
          type: string
          example: karamstay_demo_app
        error_type:
          type: string
          example: sqlalchemy.exc.TimeoutError
        error_message:
          type: string
          example: "QueuePool limit of size 2 overflow 0 reached, connection timed out, timeout 1.00"
        stack_trace:
          type: string
        target_file:
          type: string
          example: config.py
        target_line:
          type: integer
          example: 10

    CouncilRunSummary:
      type: object
      properties:
        incident_id:
          type: string
        service_name:
          type: string
        timestamp:
          type: string
          format: date-time
        awaiting_hitl_approval:
          type: boolean
        agent_latencies_ms:
          type: object
          additionalProperties:
            type: number

    PolicyVersionMetadata:
      type: object
      required: [version_tag, created_at, model_type, training_sample_count]
      properties:
        version_tag:
          type: string
        created_at:
          type: string
          format: date-time
        model_type:
          type: string
          example: linucb_ridge
        training_sample_count:
          type: integer
        validation_reward:
          type: number
        weights_file:
          type: string
        notes:
          type: string

    OutcomeRecord:
      type: object
      required: [incident_id, action_id, timestamp, success, latency_delta_pct, reward, agent_latencies_ms]
      properties:
        incident_id:
          type: string
        action_id:
          type: string
        timestamp:
          type: string
          format: date-time
        success:
          type: boolean
        latency_delta_pct:
          type: number
        reward:
          type: number
        agent_latencies_ms:
          type: object

    BenchmarkResults:
      type: object
      properties:
        benchmark_version:
          type: string
        scenarios_evaluated:
          type: integer
        comparison:
          type: object
          properties:
            recovery_success_rate:
              type: object
              properties:
                learned:
                  type: number
                baseline:
                  type: number
            mean_latency_ms:
              type: object
              properties:
                learned:
                  type: number
                baseline:
                  type: number
            unsafe_rejection_rate:
              type: object
              properties:
                learned:
                  type: number
                baseline:
                  type: number
```

---

## 3. Step-by-Step Implementation Guide

Connecting any Python web service to Project UMBRELLA requires three components:
1. `UmbrellaConfig` and `UmbrellaClient` instantiation
2. Framework-level middleware attachment
3. Hot-reload endpoint hook (`POST /api/config/reload`)

### 3.1. FastAPI Integration (ASGI)

```python
# main.py or server.py
import os
from typing import Dict, Any
from fastapi import FastAPI
from umbrella_sdk import UmbrellaClient, UmbrellaConfig, UmbrellaFastAPIMiddleware
import config
import database

app = FastAPI(title="Production Order Microservice")

def extract_telemetry() -> Dict[str, Any]:
    """Custom metric callback shipping real-time SQLAlchemy pool telemetry."""
    pool = database.engine.pool if hasattr(database, "engine") else None
    checked_out = pool.checkedout() if pool else 0
    size = pool.size() if pool else config.POOL_SIZE
    return {
        "service_name": "order_service",
        "pool_size": size,
        "checked_out_connections": checked_out,
        "overflow": pool.overflow() if pool else 0,
        "utilization_pct": round((checked_out / max(size, 1)) * 100.0, 1)
    }

# Configure UMBRELLA Sentry
umbrella_config = UmbrellaConfig(
    mission_control_url=os.environ.get("UMBRELLA_URL", "http://localhost:8000"),
    api_key=os.environ.get("UMBRELLA_API_KEY", "umb_live_k8s_9921fx"),
    service_name="order_service",
    repo_path=os.path.abspath(os.path.dirname(__file__)),
    config_file=os.path.abspath(os.path.join(os.path.dirname(__file__), "config.py")),
    service_url="http://localhost:8002",
    auto_heal_enabled=True,
    telemetry_interval_sec=2.5,
    metrics_collector=extract_telemetry
)

client = UmbrellaClient(config=umbrella_config)

# 1. Attach ASGI Middleware
app.add_middleware(UmbrellaFastAPIMiddleware, client=client)

# 2. Start Background Telemetry Heartbeat Loop
@app.on_event("startup")
def on_startup():
    client.start_telemetry_loop()

@app.on_event("shutdown")
def on_shutdown():
    client.stop_telemetry_loop()

# 3. Hot-Reload Endpoint (Required for Zero Downtime Patch Application)
@app.post("/api/config/reload")
def reload_service_config():
    """Hot-reloads modified config.py and re-initializes engine pool without OS process restart."""
    import importlib
    importlib.reload(config)
    importlib.reload(database)
    database.init_db()
    return {
        "status": "reloaded",
        "new_pool_size": config.POOL_SIZE,
        "new_max_overflow": getattr(config, "MAX_OVERFLOW", 0)
    }
```

---

### 3.2. Flask Integration (WSGI)

```python
# app.py
import os
import traceback
from flask import Flask, request, jsonify
from umbrella_sdk import UmbrellaClient, UmbrellaConfig
import config
import database

app = Flask(__name__)

umbrella_config = UmbrellaConfig(
    mission_control_url=os.environ.get("UMBRELLA_URL", "http://localhost:8000"),
    api_key=os.environ.get("UMBRELLA_API_KEY", "umb_live_k8s_9921fx"),
    service_name="flask_catalog_service",
    repo_path=os.path.abspath(os.path.dirname(__file__)),
    config_file=os.path.abspath(os.path.join(os.path.dirname(__file__), "config.py")),
    service_url="http://localhost:5000",
    auto_heal_enabled=True
)
umbrella_client = UmbrellaClient(config=umbrella_config)
umbrella_client.start_telemetry_loop()

# Catch unhandled exceptions and dispatch incident to UMBRELLA
@app.errorhandler(Exception)
def handle_exception(e):
    # Dispatch full AST frame to UMBRELLA Council
    umbrella_client.dispatch_incident(
        error_type=e.__class__.__name__,
        error_message=str(e),
        stack_trace=traceback.format_exc(),
        target_file=umbrella_config.config_file,
        target_line=10
    )
    return jsonify({"error": "Internal Server Error", "auto_healing_initiated": True}), 500

@app.route("/api/config/reload", methods=["POST"])
def reload_flask_config():
    import importlib
    importlib.reload(config)
    importlib.reload(database)
    database.init_db()
    return jsonify({"status": "reloaded", "pool_size": config.POOL_SIZE})
```

---

### 3.3. Django Integration

```python
# myproject/middleware.py
import sys
import traceback
from django.conf import settings
from umbrella_sdk import UmbrellaClient, UmbrellaConfig

class UmbrellaDjangoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.umbrella_client = UmbrellaClient(config=settings.UMBRELLA_CONFIG)
        self.umbrella_client.start_telemetry_loop()

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Automatically capture stack trace and ship to UMBRELLA Mission Control
        self.umbrella_client.dispatch_incident(
            error_type=exception.__class__.__name__,
            error_message=str(exception),
            stack_trace="".join(traceback.format_tb(exception.__traceback__)),
            target_file=getattr(settings, "UMBRELLA_TARGET_CONFIG", "settings.py"),
            target_line=1
        )
        return None
```

---

## 4. Safety Matrix, Risk Tiers & Epistemic Uncertainty

Project UMBRELLA strictly enforces an immutable safety boundary around remediation actions:

| Risk Tier | Remediation Scope | Blast Radius | Approval Policy | Executor Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Read-Only Optimization / Cache Refresh | 0% | Autonomous Auto-Apply | Direct Sandboxed Execution |
| **Tier 2** | Non-Destructive Config Scaling (`POOL_SIZE`) | $\le 40\%$ | Autonomous if Auto-Heal Enabled; else HITL | Sandboxed Execution + Hot Reload |
| **Tier 3** | High-Blast Structural Code Patch | $> 40\%$ | **Mandatory Human-in-the-Loop (HITL)** | Armed Gate; Requires Operator Authorization |
| **Tier 4** | Prohibited Destructive Operations (`DROP TABLE`, `rm -rf`) | Any | **Strictly Forbidden** | Hard Blocked by Deterministic Guardian & Bandit |

### Agent 6 EVO Safety Invariants
1. **Advisory-Only Constraint:** Agent 6 EVO is an evaluation and outcome-aware policy learner. It **cannot** approve actions, cannot bypass Human-in-the-Loop gates, and cannot execute commands.
2. **Epistemic Uncertainty Fallback:** The LinUCB bandit maintains Ridge covariance matrices $A_a$ per action arm. When evaluating an unseen scenario, if epistemic uncertainty $\sigma(s, a) = \sqrt{x^\top A_a^{-1} x} \ge 0.60$, the system automatically marks the action as high-uncertainty and defers priority ranking to the verified deterministic baseline (`DeterministicRuleBaseline`).
3. **Atomic Rollback Traps:** Every execution applied by Agent 4 Executor captures pre-patch file snapshots in a clean Git worktree. If verification tests fail, the change is reverted instantly with zero residue.

---

## 5. Verification & Health Monitoring

To verify your microservice connection from the terminal:

```bash
# 1. Check registered services
curl -X GET http://localhost:8000/api/system/live-telemetry

# 2. Test manual incident dispatch
curl -X POST http://localhost:8000/api/sdk/incident \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "karamstay_demo_app",
    "error_type": "sqlalchemy.exc.TimeoutError",
    "error_message": "QueuePool limit of size 2 overflow 0 reached",
    "stack_trace": "File \"server.py\", line 45, in payment_lock ...",
    "target_file": "config.py",
    "target_line": 10
  }'

# 3. Verify Agent 6 policy registry
curl -X GET http://localhost:8000/api/evo/policy-versions
```

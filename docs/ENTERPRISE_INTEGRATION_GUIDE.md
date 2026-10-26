# Enterprise Integration Guide: Connecting Any Microservice to Project UMBRELLA

> **Document Status**: Production Standard  
> **Target Audience**: Platform Engineers, SREs, Enterprise Architects, Backend Developers  
> **Platform Version**: Project UMBRELLA v2.0 Enterprise

---

## 1. Architectural Overview & Closed-Loop Resilience

Project UMBRELLA provides an autonomous, multi-agent closed-loop resilience and self-healing platform. Unlike legacy APM tools that merely alert on-call engineers via PagerDuty or Slack, UMBRELLA actively diagnoses root causes down to AST code syntax nodes, synthesizes git-compliant unified diff patches, enforces safety policies through an automated Guardian Gate (HITL), applies sandboxed test-verified patches, and triggers zero-downtime hot-reloads on the target service.

```
+-----------------------------------------------------------------------------------+
|                            TARGET MICROSERVICE RUNTIME                            |
|                                                                                   |
|   +-----------------------+      +--------------------+     +-----------------+   |
|   | ASGI / Web Framework  | ---> | Umbrella Middleware| --->| Business Logic  |   |
|   +-----------------------+      +--------------------+     +-----------------+   |
|               |                            | (on unhandled)          |            |
|               |                            v                         |            |
|               |                 +--------------------+               |            |
|               |                 | AST Stack-Trace    |               |            |
|               |                 | Isolation Engine   |               |            |
|               |                 +--------------------+               |            |
|               v                            |                         v            |
|      +-----------------+                   | (Incident Dispatch) +--------------+ |
|      | Background      |                   |                     | Target DB /  | |
|      | Telemetry Loop  |                   v                     | QueuePool    | |
+------+-----------------+-------------------+---------------------+--------------+-+
               |                               |                              ^
               | POST /api/sdk/telemetry       | POST /api/sdk/incident       | POST /api/config/reload
               v                               v                              | (Zero-Downtime Reload)
+-----------------------------------------------------------------------------+-----+
|                     PROJECT UMBRELLA: MISSION CONTROL CONTROL PLANE               |
|                                                                                   |
|  +--------------------+   +---------------------+   +--------------------------+  |
|  | Agent 1 (RCA):     |-->| Agent 2 (Topology): |-->| Agent 3 (Planner):       |  |
|  | 4-Signal AST & RAG |   | 3D Spatial Blast    |   | Unified Diff Synthesizer |  |
|  +--------------------+   +---------------------+   +--------------------------+  |
|                                                                  |                |
|                                                                  v                |
|  +--------------------+   +---------------------+   +--------------------------+  |
|  | Agent 6 (EVO):     |<--| Agent 4 (Executor): |<--| Agent 5 (Guardian):      |  |
|  | Q-Learning Memory  |   | Sandboxed Patch Git |   | Safety Policy HITL Gate  |  |
|  +--------------------+   +---------------------+   +--------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. How the Target System Connects Today: `Umbrella-demo-app` Walkthrough

The target application (`Umbrella-demo-app`, modeling the high-concurrency KaramStay PG Rental Platform) connects to UMBRELLA using the official `umbrella_sdk`. Below is the exact step-by-step implementation currently active in `Umbrella-demo-app/server.py`:

### Step 2.1: Configuration Object (`UmbrellaConfig`)
The microservice instantiates `UmbrellaConfig` specifying the Mission Control endpoint, its service identifier, physical repository location, target configuration file, callback service URL, and a custom telemetry collector hook:

```python
from umbrella_sdk import UmbrellaClient, UmbrellaConfig, UmbrellaFastAPIMiddleware

def collect_telemetry() -> Dict[str, Any]:
    """Extracts real-time connection pool metrics for UMBRELLA Mission Control."""
    checkedout = engine.pool.checkedout() if engine and hasattr(engine, "pool") else 0
    size = engine.pool.size() if engine and hasattr(engine, "pool") else config.POOL_SIZE
    return {
        "service_name": "karamstay_demo_app",
        "pool_size": size,
        "checked_out_connections": checkedout,
        "overflow": engine.pool.overflow() if engine and hasattr(engine, "pool") else 0,
        "utilization_pct": round((checkedout / max(size, 1)) * 100.0, 1),
        "database_url": config.DATABASE_URL,
        "repo_path": os.path.abspath(os.path.dirname(__file__))
    }

umbrella_config = UmbrellaConfig(
    mission_control_url=config.UMBRELLA_MISSION_CONTROL_URL, # "http://localhost:8000"
    api_key=config.UMBRELLA_API_KEY,                         # "umb_live_k8s_9921fx"
    service_name="karamstay_demo_app",
    repo_path=os.path.abspath(os.path.dirname(__file__)),
    config_file=os.path.abspath(os.path.join(os.path.dirname(__file__), "config.py")),
    service_url="http://localhost:8002",
    auto_heal_enabled=True,
    telemetry_interval_sec=2.0,
    metrics_collector=collect_telemetry
)

umbrella_client = UmbrellaClient(config=umbrella_config)
```

### Step 2.2: Middleware Attachment
The ASGI middleware transparently intercepts all incoming HTTP requests:

```python
# Attached to the FastAPI application instance
app.add_middleware(UmbrellaFastAPIMiddleware, client=umbrella_client)
```

### Step 2.3: Telemetry Background Loop Activation
On microservice startup, the background telemetry loop starts shipping non-blocking health heartbeats:

```python
umbrella_client.start_telemetry_loop()
```

### Step 2.4: Zero-Downtime Hot-Reload Callback (`POST /api/config/reload`)
When UMBRELLA's Council applies an authorized code patch to `config.py` (e.g., scaling `POOL_SIZE = 2` to `POOL_SIZE = 10`), UMBRELLA calls this endpoint to hot-reload in-memory module state without restarting the OS process:

```python
@app.post("/api/config/reload")
def reload_config():
    """Dynamically reloads config.py and recreates database pool after UMBRELLA patch application."""
    import importlib
    importlib.reload(config)
    import database
    importlib.reload(database)
    database.init_db()
    log_event("CONFIG_RELOADED", f"Capacity reloaded: POOL_SIZE={config.POOL_SIZE}, MAX_OVERFLOW={config.MAX_OVERFLOW}", 200)
    return {
        "status": "reloaded",
        "pool_size": config.POOL_SIZE,
        "max_overflow": config.MAX_OVERFLOW,
        "pool_timeout": config.POOL_TIMEOUT
    }
```

---

## 3. Deep-Dive: Core SDK Architecture

The `umbrella_sdk` is composed of four decoupled subsystems designed for zero runtime overhead:

### 3.1. ASGI Middleware (`UmbrellaFastAPIMiddleware`)
- Inherits from Starlette's `BaseHTTPMiddleware`.
- Measures exact HTTP transaction latency in milliseconds (`elapsed_ms`).
- In normal flow: Passes requests transparently with `<0.1ms` overhead.
- In exception flow (`try...except Exception as exc`):
  1. Intercepts the unhandled exception before it crashes the process.
  2. Enriches the context with `http_method`, `path`, `client_ip`, and `elapsed_ms`.
  3. Calls `client.report_incident(exc, context)`.
  4. Formats a clean HTTP 500 JSON payload declaring that Project UMBRELLA autonomous remediation is in progress.

### 3.2. AST Stack-Trace Isolation Engine
When a framework crashes, the raw Python traceback usually ends deep inside a third-party dependency (e.g. `sqlalchemy/pool/base.py`, line 350, `QueuePool.get()`). If an agent blindly targeted that file, it would corrupt site-packages.

The AST Stack-Trace Isolation Engine in `umbrella_sdk/client.py` solves this via reverse frame traversal:
```python
tb_frames = traceback.extract_tb(exception.__traceback__) if exception.__traceback__ else []
target_file = self.config.config_file
target_line = 1
found_app_frame = False

if tb_frames:
    for frame in reversed(tb_frames):
        fname = frame.filename
        # Check if frame belongs to target service repo or is not internal site-package
        if self.config.repo_path and os.path.abspath(self.config.repo_path) in os.path.abspath(fname):
            target_file = fname
            target_line = frame.lineno
            found_app_frame = True
            break
        elif "site-packages" not in fname.lower() and "lib" not in fname.lower().split(os.sep):
            target_file = fname
            target_line = frame.lineno
            found_app_frame = True
            break
```
If the entire traceback is in third-party libraries, the engine automatically falls back to `self.config.config_file`, directing Agent 1 (AST RCA) to the application's configuration parameters.

### 3.3. Background Non-Blocking Telemetry Loop
- Operates on a dedicated daemon thread (`umbrella-telemetry-thread`).
- Executes the user-supplied `metrics_collector` callback every `telemetry_interval_sec` (default 2.0s).
- Dispatches metrics to `/api/sdk/telemetry` using Python's standard `urllib.request` with a 5-second socket timeout.
- Will never block incoming user requests, allocate excessive memory, or cause cascading thread starvation.

---

## 4. The Complete REST Ingestion Contract

Any service—regardless of programming language—can connect to Project UMBRELLA by adhering to the following HTTP REST contract:

### 4.1. Microservice Registration (`POST /api/sdk/register`)
Sent once during microservice startup to handshake with UMBRELLA Mission Control.

**Headers**:
```http
Content-Type: application/json
X-Umbrella-API-Key: <api_key>
User-Agent: UmbrellaSDK/<service_name>
```

**Request Payload**:
```json
{
  "service_name": "payment_service",
  "repo_path": "/var/services/payment_service",
  "config_file": "/var/services/payment_service/config.py",
  "service_url": "http://payment-service.internal:8001",
  "auto_heal_enabled": true,
  "registered_at": 1729954716.42,
  "pid": 48201
}
```

**Response (HTTP 200)**:
```json
{
  "status": "registered",
  "service_name": "payment_service",
  "council_version": "2.0.0",
  "monitoring_mode": "ACTIVE_CLOSED_LOOP"
}
```

---

### 4.2. Operational Telemetry Snapshot (`POST /api/sdk/telemetry`)
Sent periodically (e.g., every 2 to 5 seconds) to maintain live topology health status and resource saturation meters.

**Request Payload**:
```json
{
  "service_name": "payment_service",
  "timestamp": 1729954720.15,
  "data": {
    "pool_size": 2,
    "checked_out_connections": 2,
    "overflow": 0,
    "utilization_pct": 100.0,
    "active_workers": 4,
    "latency_p99_ms": 1420.5
  }
}
```

**Response (HTTP 200)**:
```json
{
  "status": "received"
}
```

---

### 4.3. Live Incident Dispatch (`POST /api/sdk/incident`)
Sent immediately when an unhandled exception or system threshold crash occurs. This triggers the 6-Agent Council pipeline.

**Request Payload**:
```json
{
  "service_name": "payment_service",
  "timestamp": 1729954722.84,
  "error_type": "TimeoutError",
  "error_message": "QueuePool limit of size 2 overflow 0 reached, connection timed out, timeout 1.00",
  "stack_trace": "Traceback (most recent call last):\n  File \"server.py\", line 75, in book_room\n    conn = db.connection()\nTimeoutError: QueuePool limit reached",
  "target_file": "/var/services/payment_service/config.py",
  "target_line": 10,
  "config_file": "/var/services/payment_service/config.py",
  "repo_path": "/var/services/payment_service",
  "context": {
    "http_method": "POST",
    "path": "/pay-rent",
    "elapsed_ms": 1004.2,
    "client_ip": "10.0.4.12"
  }
}
```

**Council Execution Response (HTTP 200)**:
```json
{
  "incident_id": "INC-1729954722",
  "service_name": "payment_service",
  "timestamp": "2026-10-26T14:58:42.840Z",
  "agent_1_rca": {
    "overall_confidence": 0.88,
    "primary_causes": [{
      "cause": "QueuePool capacity saturated (POOL_SIZE=2, OVERFLOW=0)",
      "target_file": "config.py",
      "line_number": 10
    }]
  },
  "agent_2_topology": {
    "blast_report": { "blast_radius_score": 1.0, "impacted_node_ids": ["client_service", "client_db_pool"] }
  },
  "agent_3_planner": {
    "actions": [{
      "action_id": "ACT-POOL-SCALE-001",
      "risk_tier": "low",
      "target_file": "config.py",
      "unified_diff": "--- a/config.py\n+++ b/config.py\n@@ -10,1 +10,1 @@\n-POOL_SIZE = 2\n+POOL_SIZE = 10\n"
    }]
  },
  "agent_5_guardian": {
    "approved": false,
    "reason": "Human-in-the-Loop review required for production code modification"
  },
  "awaiting_hitl_approval": true
}
```

---

### 4.4. Zero-Downtime Hot-Reload Callback (`POST /api/config/reload`)
Called by UMBRELLA Agent 4 (Executor) on the target microservice after applying and verifying the patch.

**Request Payload**:
```json
{}
```

**Expected Response (HTTP 200)**:
```json
{
  "status": "reloaded",
  "pool_size": 10,
  "max_overflow": 5
}
```

---

## 5. Universal Integration Guide for Any Microservice

### 5.1. Integrating with Python (Flask, Django, Starlette)

#### Flask Application:
```python
from flask import Flask, jsonify, request
from umbrella_sdk import UmbrellaClient, UmbrellaConfig

app = Flask(__name__)
client = UmbrellaClient(UmbrellaConfig(
    mission_control_url="http://localhost:8000",
    service_name="billing_flask_service",
    config_file="config.py"
))
client.start_telemetry_loop()

@app.errorhandler(Exception)
def handle_exception(exc):
    client.report_incident(exc, context={"url": request.url, "method": request.method})
    return jsonify({"error": "Internal Error", "umbrella_remediation": True}), 500
```

#### Django Application:
In `settings.py`:
```python
MIDDLEWARE = [
    'umbrella_sdk.django_middleware.UmbrellaDjangoMiddleware',
    # ... standard middlewares
]
```

---

### 5.2. Integrating Non-Python Microservices (Node.js, Go, Java, Rust)

Because Project UMBRELLA exposes a standard REST interface, non-Python backends integrate effortlessly by dispatching standard JSON HTTP POST requests to `/api/sdk/incident` and `/api/sdk/telemetry`.

#### Node.js / Express Example:
```javascript
const express = require('express');
const axios = require('axios');
const app = express();

const UMBRELLA_URL = "http://localhost:8000";

// Error handling middleware
app.use((err, req, res, next) => {
  console.error("Crash detected:", err);

  // Dispatch incident to UMBRELLA
  axios.post(`${UMBRELLA_URL}/api/sdk/incident`, {
    service_name: "node_inventory_service",
    error_type: err.name || "Error",
    error_message: err.message,
    stack_trace: err.stack || "",
    target_file: "config.js",
    target_line: 12,
    context: { path: req.path, method: req.method }
  }).catch(e => console.warn("Failed to report to UMBRELLA:", e.message));

  res.status(500).json({ error: "Internal Server Error", monitored_by_umbrella: true });
});
```

#### Go (Golang / Gin) Example:
```go
package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"runtime/debug"
	"github.com/gin-gonic/gin"
)

func UmbrellaRecoveryMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if r := recover(); r != nil {
				stack := string(debug.Stack())
				payload := map[string]interface{}{
					"service_name": "go_auth_service",
					"error_type":   "PanicRecovered",
					"error_message": r,
					"stack_trace":  stack,
					"target_file":  "config.go",
				}
				data, _ := json.Marshal(payload)
				http.Post("http://localhost:8000/api/sdk/incident", "application/json", bytes.NewBuffer(data))
				c.AbortWithStatusJSON(500, gin.H{"error": "Internal Server Error", "umbrella_healing": true})
			}
		}()
		c.Next()
	}
}
```

---

## 6. Security, Hardening, and Production Checklist

| Category | Requirement | Implementation in Project UMBRELLA |
|---|---|---|
| **Authentication** | Shared API Key | `X-Umbrella-API-Key` enforced on all `/api/sdk/*` routes |
| **Fault Isolation** | Non-blocking dispatch | SDK uses short timeouts (2.0s - 5.0s) and thread pools |
| **Safety Policy** | Human-in-the-Loop Gate | Agent 5 evaluates risk tier; requires operator click to commit patches |
| **Disaster Recovery** | Rollback Trap | Agent 4 creates an immutable git worktree branch before applying patches |
| **Zero-Downtime** | Dynamic In-Memory Reload | Mission Control signals `/api/config/reload` via client HTTP hook |
| **Audit Log** | Immutable Record | Agent 4 records git commit hash, Agent 6 records Q-learning reward into `data/evolution_memory.json` |

---

*Project UMBRELLA: Autonomous Multi-Agent Resilience & Self-Healing Platform*

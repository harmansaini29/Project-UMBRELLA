# Project UMBRELLA: MVP1 Engineering & Research Blueprint

> **A Risk-Aware Multi-Agent Framework for Autonomous Fault Detection, Diagnosis, Remediation, and Self-Healing of Software Systems**  
> *Author*: Harman Saini | *Version*: 1.0 (October 2026)

---

## 1. Executive Implementation Decision

**Core Rule**: Prove reliability first; add bounded intelligence second; prove learning with controlled experiments.  
The system must be built as a deterministic, testable self-healing core first. The Backend Evolution Agent acts as an evidence-backed proposal and evaluation layer. Only after stable outcome records exist should the system learn to rank approved recovery actions.

```
       [ Telemetry & Probes ]
                 │
                 ▼
     [ Fault Detection & RCA ]
                 │
                 ▼
       [ Hybrid Agentic RAG ] ◄── Curated Operational Runbooks & Repositories
                 │
                 ▼
     [ Remediation Planning ]
                 │
                 ▼
     [ Risk & Policy Engine ] ──(Exceeds Low-Risk Tier)──► [ Human Approval Gate ]
                 │ (Approved)
                 ▼
  [ Sandboxed Execution Agent ] (Isolated Git Worktree / Container)
                 │
                 ▼
    [ Verification & Health ] ──(Verification Failed)──► [ Automated Rollback ]
                 │ (Passed)
                 ▼
   [ System Evolution Memory ]
                 │
                 ▼
 [ Agent 6: Outcome Ranker ] ──► (Improves future action rankings)
```

---

## 2. The 5 Specialist Agents + Agent 6 Architecture

| Agent | Functional Name | Role / Mental Model | Main Question Answered |
|---|---|---|---|
| **Agent 1** | **Root Cause Analyzer (RCA)** | Investigator | *What happened, where, and why?* Ingests telemetry, logs, exceptions, and traces. |
| **Agent 2** | **3D Topology Visualizer** | Digital-Twin Mapper | *Which components, dependencies, and blast radii are affected?* |
| **Agent 3** | **Remediation Planner** | Incident Strategist / Cheat Sheet | *What should we do, in what order, and with what fallback?* Queries Hybrid RAG. |
| **Agent 4** | **Action Executor** | Controlled Operator | *How do we safely execute the approved patch or command in a sandbox?* |
| **Agent 5** | **Leader Governor / Guardian** | Incident Commander & Safety Controller | *Is the plan safe, permitted by policy, verified healthy, or escalated?* |
| **Agent 6** | **Backend Evolution Agent** | Outcome Learner & System Memory | *Which approved recovery action worked best in similar historical incidents?* |

---

## 3. Action Risk Tiers & Mandatory Safety Controls

### Risk Tiers
- **Tier 0 (Observe)**: Health probes, read-only Prometheus metrics, log queries. Permitted automatically with read-only credentials and secret redaction.
- **Tier 1 (Low-Risk Reversible)**: Restarting an isolated worker, toggling a disposable test flag. Executed automatically under strict allowlists and timeouts with automated verification and rollback.
- **Tier 2 (Material Change)**: Source code diff, configuration changes, dependency updates. Requires isolated sandbox testing, automated test suite pass, and **mandatory human-in-the-loop (HITL) approval**.
- **Tier 3 (High-Impact / Destructive)**: Database drop, production schema migration, broad access mutation. **Blocked by default** in autonomous mode.

### Invariant Safety Principles
1. **Deny by Default**: Unrecognized action IDs, parameters, or models are rejected.
2. **Propose vs. Execute Separation**: An LLM can recommend an action, but only the deterministic policy engine can authorize execution.
3. **No Direct Secret Exposure**: Passwords, API tokens, and private keys are never passed into LLM prompts or indexed in RAG vectors.
4. **Sandboxed Patch Testing**: All code patches run in ephemeral Git worktrees with restricted network and filesystem access.
5. **Circuit Breakers**: Prevent runaway loops, oscillation, or cascading remediation actions.

---

## 4. System Evolution Memory: Relational Data Schema

The system tracks every incident from observation to recovery outcome:

```sql
-- 1. Incidents Table
CREATE TABLE incidents (
    id VARCHAR(64) PRIMARY KEY,
    service_name VARCHAR(128) NOT NULL,
    environment VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL, -- OPEN, INVESTIGATING, MITIGATING, VERIFIED, ROLLED_BACK
    severity VARCHAR(16) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 2. Telemetry Observations Table
CREATE TABLE observations (
    id VARCHAR(64) PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    signal_type VARCHAR(64) NOT NULL, -- HTTP_5XX, DB_TIMEOUT, LATENCY_SPIKE
    raw_payload_sanitized JSONB NOT NULL
);

-- 3. Diagnostic Hypotheses Table
CREATE TABLE diagnoses (
    id VARCHAR(64) PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id),
    hypothesis TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    evidence_references JSONB NOT NULL
);

-- 4. Remediation Actions Catalogue & Runs
CREATE TABLE action_definitions (
    action_id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(16) NOT NULL,
    risk_tier INT NOT NULL, -- 0, 1, 2, 3
    parameters_schema JSONB NOT NULL,
    timeout_seconds INT NOT NULL,
    rollback_handler VARCHAR(128)
);

CREATE TABLE action_runs (
    id VARCHAR(64) PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id),
    action_id VARCHAR(64) REFERENCES action_definitions(action_id),
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(32) NOT NULL,
    applied_diff_hash VARCHAR(64),
    approver_identity VARCHAR(128),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 5. Verified Outcome Lineage (Consumed by Agent 6)
CREATE TABLE outcome_records (
    id VARCHAR(64) PRIMARY KEY,
    incident_id VARCHAR(64) REFERENCES incidents(id),
    action_run_id VARCHAR(64) REFERENCES action_runs(id),
    recovery_verified BOOLEAN NOT NULL,
    time_to_recover_seconds FLOAT NOT NULL,
    regression_detected BOOLEAN DEFAULT FALSE,
    observation_window_seconds INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 5. Development Phases & Gates

- **Phase 0 — Baseline & Environment Freeze**: Disposable testbed, reproducible fault injection harness.
- **Phase 1 — Deterministic Self-Healing Core**: Health probes, incident lifecycle, allowlisted actions, rollback engine.
- **Phase 2 — Diagnosis & RAG Knowledge Bridge**: Hybrid retrieval (BM25 + FAISS + AST chunker), RCA hypothesis formulation.
- **Phase 3 — Backend Evolution Agent (Controlled Auto-Dev)**: Ephemeral Git worktree patching, sandbox validation, HITL review interface.
- **Phase 4 — System Evolution Memory & Outcome-Aware Ranking**: Agent 6 learning loop, weighting actions by historical success.
- **Phase 5 — Multi-Agent Coordination & 3D Topology Visualization**: Inter-agent typed schemas, React Flow / Three.js digital twin.
- **Phase 6 — Controlled Experiments, Ablation & Research Freeze**: Running repeated fault injection, statistical verification, and paper freeze.

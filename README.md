# Project UMBRELLA

### A Risk-Aware Multi-Agent Framework for Autonomous Backend Self-Healing, Behavioral Evolution, and Long-Term Recovery

**Author**: Harman Saini  
**Affiliation**: Department of Computer Science and Engineering (Artificial Intelligence and Machine Learning), Chhatrapati Shivaji Maharaj University, India  
**Repository**: `harmansaini29/Project-UMBRELLA`  
**License**: Apache-2.0  
**Research Status**: MVP1 Implementation (Phase 1 Complete)

---

## 🌟 Executive Overview
Modern cloud backends face increasing operational complexity: high-frequency deployments, microservice inter-dependencies, and sudden transient or logical failures create cascading outages. Traditional automated remediation approaches are brittle, hard-coded rule scripts, while naive LLM-based autonomous coding creates immense risk: hallucinated fixes, unvetted secret exposures, regression bugs, and unauthorized production commits.

**Project UMBRELLA** solves this by operating as an external **Risk-Aware Reliability Control Plane** over a managed backend ecosystem:
- **Central Hybrid Agentic RAG**: Dual-stream retrieval (AST syntax-aware chunking + BM25 keyword matching + FAISS dense semantic embeddings) providing evidence-grounded code repair recommendations.
- **5 Specialist Agents**: Dedicated agents for Root Cause Analysis (Agent 1), 3D Spatial Topology Visualization (Agent 2), Remediation Planning (Agent 3), Sandboxed Action Execution (Agent 4), and Leader Governance / Safety Guardianship (Agent 5).
- **Agent 6 (Backend Evolution Agent)**: Outcome-aware adaptation loop that learns from verified historical remediations to continuously improve future recovery action rankings.
- **Closed-Loop Reliability**: Programmatic test validation in ephemeral sandboxes with automated rollback on failure.

---

## 🏛️ System Architecture

```
[ Backend Ecosystem ] ──► [ Telemetry / Probes ] ──► [ Agent 1: Root Cause Analyzer ]
                                                              │
                                                              ▼
[ Hybrid Agentic RAG ] ◄────────────────────────────── [ Agent 3: Remediation Planner ]
  (BM25 + FAISS + AST)                                        │
                                                              ▼
                                                 [ Agent 5: Leader Governor ]
                                                  (Risk Policy & Approval Gate)
                                                              │ (Approved)
                                                              ▼
                                                 [ Agent 4: Action Executor ]
                                                  (Sandbox Git Worktree / CI)
                                                              │
                                                              ▼
                                                 [ Verification & Rollback ]
                                                              │ (Passed)
                                                              ▼
                                                 [ Agent 6: Evolution Memory ]
```

---

## 📁 Repository Structure

```
Project-UMBRELLA/
├── core/                         # Shared utilities, Pydantic schemas, and logging
├── telemetry/                    # Monitoring probes, OpenTelemetry, log parsers
├── rag/                          # Phase 2: Central Hybrid Agentic RAG Engine
│   ├── chunking/                 # AST syntax-aware code & markdown chunkers
│   ├── index/                    # BM25 keyword index + FAISS vector index
│   └── retrieval/                # RRF reranker and evidence synthesizer
├── agents/                       # Phase 3: Specialist Agent Council
│   ├── agent1_rca/               # Root Cause & Diagnostic Analyzer
│   ├── agent2_topology/          # 3D Spatial Visualizer & Blast Radius Mapper
│   ├── agent3_planner/           # Remediation Strategist & Cheat Sheet Generator
│   ├── agent4_executor/          # Sandboxed Patch Runner & Rollback Engine
│   └── agent5_guardian/          # Leader Governor (Risk, Policy & Approval Gate)
├── evolution/                    # Phase 4: Agent 6 Backend Evolution & Learning
│   ├── memory/                   # System Evolution Memory (Relational Schema)
│   └── ranker/                   # Outcome-Aware Recovery Action Ranker
├── umbrella-curated-reference/   # Curated knowledge base (2,219 verified files)
├── docs/                         # Official research papers, blueprints & roadmaps
│   ├── PROJECT_CHARTER_AND_RESEARCH_PAPER.md
│   ├── MVP1_ENGINEERING_BLUEPRINT.md
│   ├── SYSTEM_ARCHITECTURE_AND_WORKFLOWS.md
│   └── ROADMAP_AND_EXECUTION_STATE.md
├── tools/                        # Curation, PDF generator, and verification scripts
└── UMBRELLA_Infosys_Knowledge_Reference.pdf # Publication-quality 7-page technical report
```

---

## 🚀 Current Milestone & Next Steps

| Milestone | Status | Details |
|---|---|---|
| **Phase 1: Knowledge Acquisition & Curation** | **COMPLETED** | Acquired 4 Infosys repositories, curated 2,219 files with 0 secret leaks, generated `manifest.json` and 7-page PDF. |
| **Phase 2: Hybrid Agentic RAG Engine** | **UPCOMING (STEP 1)** | Implementing AST code chunking, BM25 exact search, FAISS dense embeddings, and RRF reranking. |
| **Phase 3: Specialist Agent Council** | Queued | Connecting Agents 1–5 via typed Pydantic contracts and safety gates. |
| **Phase 4: Agent 6 Behavioral Evolution** | Queued | Outcome-aware action ranking evaluated on reproducible testbeds. |

---

## 📚 Master Documentation
- [Official Research Paper & Charter](docs/PROJECT_CHARTER_AND_RESEARCH_PAPER.md)
- [MVP1 Engineering & Research Blueprint](docs/MVP1_ENGINEERING_BLUEPRINT.md)
- [System Architecture & Visual Workflows](docs/SYSTEM_ARCHITECTURE_AND_WORKFLOWS.md)
- [Live Execution Roadmap](docs/ROADMAP_AND_EXECUTION_STATE.md)
- [Technical Reference PDF Report](UMBRELLA_Infosys_Knowledge_Reference.pdf)

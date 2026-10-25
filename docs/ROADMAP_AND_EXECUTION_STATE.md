# Project UMBRELLA: Roadmap & Live Execution State

> **Author**: Harman Saini | **Project**: UMBRELLA  
> **Repository**: [`harmansaini29/Project-UMBRELLA`](https://github.com/harmansaini29/Project-UMBRELLA)  
> **Last Updated**: October 2026 | **Current Status**: All 4 Phases Complete & Functionally Verified (12/12 Tests Passing)

---

## 1. Overall Major Project Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Knowledge Acquisition & Curation                             │
│ [STATUS: COMPLETED & COMMITTED (Commit 0fe221d)]                       │
│ • Acquired 4 Infosys Open-Source Repositories                          │
│ • Screened 8,245 files, removed 6,026 bloat files                      │
│ • Curated 2,219 high-value files into umbrella-curated-reference/     │
│ • Audited secrets: 0 credentials leaked                                │
│ • Generated 7-page PDF Architecture Report                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Hybrid Agentic RAG Engine (rag/)                              │
│ [STATUS: COMPLETED & BENCHMARKED (Commit 8890141)]                     │
│ • Syntax-Aware AST Code Parsing & Chunking (23,769 chunks)             │
│ • Lexical Exact Match (BM25: 827,975 terms)                            │
│ • Dense Semantic Vector Search (FAISS IndexFlatIP: 23,769 vectors)     │
│ • Reciprocal Rank Fusion (RRF k=60) running at 8.64ms average latency  │
│ • Responsible AI Hallucination Guard Grounding                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Specialist Agent Council (agents/)                            │
│ [STATUS: COMPLETED & VERIFIED (Commit 66c0640)]                        │
│ • Agent 1: Root Cause & AST Diagnostic Analyzer (87.8% confidence)     │
│ • Agent 2: 3D Topology & Blast-Radius Visualizer (BFS propagation)     │
│ • Agent 3: Remediation Planner & Cheat Sheet Generator (Unified Diffs) │
│ • Agent 4: Sandboxed Action Executor & Zero-Downtime Rollback Engine   │
│ • Agent 5: Leader Governor / Safety Guardian & Surrogate Failover Watch│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Target Demo App, UI Cockpit & EVO Time Engine (dashboard/)   │
│ [STATUS: COMPLETED & OPERATIONAL (Commit de8afbe)]                     │
│ • Multi-Tenant Room Booking & Payment Microservice (target_system/)    │
│ • 5–10 Tenant Concurrency Stress Simulator (load_simulator.py)         │
│ • Agent 6 EVO Config Engine: Selectable 24h, 48h, 1w, 2w, 1m windows   │
│ • Mission Control UI/UX Operator Dashboard (FastAPI + SVG/Canvas Cockpit)│
│ • Academic Research Paper Evidence PDF (reports/ 5 pages, PyPDF2 OK)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Layout Invariant (Clean, Enterprise-Grade)

To prevent clutter and ensure maximum modularity, all components follow this directory standard:

```
Project-UMBRELLA/
├── core/                         # Core schemas, config, and logging
├── telemetry/                    # Monitoring probes, OpenTelemetry, log parsers
├── rag/                          # Phase 2: Central Hybrid Agentic RAG
│   ├── chunking/                 # AST syntax-aware code and markdown chunkers
│   ├── index/                    # BM25 index + FAISS vector index
│   ├── retrieval/                # RRF reranker and evidence synthesizer
│   └── models/                   # Pydantic search query & citation schemas
├── agents/                       # Phase 3: Specialist Agents
│   ├── agent1_rca/               # Root cause analyzer
│   ├── agent2_topology/          # 3D spatial visualizer
│   ├── agent3_planner/           # Remediation strategist
│   ├── agent4_executor/          # Sandboxed patch runner
│   └── agent5_guardian/          # Leader governor & safety gate
├── evolution/                    # Phase 4: Agent 6 Learning Engine
│   ├── memory/                   # System Evolution Memory database
│   └── ranker/                   # Outcome-aware preference optimizer
├── umbrella-curated-reference/   # Curated knowledge base (2,219 files)
├── docs/                         # Master research papers and blueprints
├── tools/                        # Curation, PDF generator, and verification
└── tests/                        # Unit, integration, and fault-injection tests
```

---

## 3. Immediate Milestone: Step 1 (Building the Hybrid Agentic RAG Engine)

### Primary Objectives
1. **AST-Aware Syntax Chunker**:
   - Parse Python files into complete classes, functions, and docstrings using Python's native `ast` module.
   - Retain parent module imports, function names, decorators, and line ranges.
   - Chunk Markdown and YAML documentation by semantic headers (`#`, `##`, `###`).
2. **Dual-Index Architecture**:
   - **Lexical BM25 Index**: For exact keywords (`OperationalError`, `/api/v1/health`, `connection_pool`).
   - **FAISS Vector Index**: Using local lightweight sentence embeddings or API embeddings for conceptual queries.
3. **Reciprocal Rank Fusion (RRF)**:
   - Combine top-$k$ results from BM25 and vector search using standard RRF:
     $$RRF\_Score(d) = \sum_{m \in \{\text{BM25}, \text{Vector}\}} \frac{1}{60 + \text{rank}_m(d)}$$
4. **Verification & Grounding**:
   - Ensure every retrieval result returns exact `file_path`, `start_line`, `end_line`, `commit_sha`, and `source_repo`.

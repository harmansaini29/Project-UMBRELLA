# Project UMBRELLA: Roadmap & Live Execution State

> **Author**: Harman Saini | **Project**: UMBRELLA  
> **Repository**: [`harmansaini29/Project-UMBRELLA`](https://github.com/harmansaini29/Project-UMBRELLA)  
> **Last Updated**: October 2026 | **Current Status**: Phase 1 Complete -> Transitioning to Phase 2 (Hybrid Agentic RAG)

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
│ [STATUS: READY TO BUILD NEXT - STEP 1]                                 │
│ • Syntax-Aware AST Code Parsing & Chunking                             │
│ • Lexical Exact Match (BM25) for routes, exception logs, and configs   │
│ • Dense Semantic Vector Search (FAISS) for runbooks & documentation    │
│ • Reciprocal Rank Fusion (RRF) Reranking Engine                        │
│ • Source Citations with exact file paths and line ranges               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Specialist Agent Council (agents/)                            │
│ [STATUS: PENDING RAG FOUNDATION]                                       │
│ • Agent 1: Root Cause & Diagnostic Analyzer (RCA)                      │
│ • Agent 2: 3D Topology & Blast-Radius Visualizer                       │
│ • Agent 3: Remediation Planner & Cheat Sheet Generator                 │
│ • Agent 4: Sandboxed Action Executor & Rollback Engine                 │
│ • Agent 5: Leader Governor / Safety Guardian (Risk & HITL Gate)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Backend Evolution Agent (Agent 6) (evolution/)                │
│ [STATUS: PENDING AGENT COUNCIL]                                        │
│ • System Evolution Memory (Relational Schema for Incident Lineage)     │
│ • Outcome-Aware Recovery Action Ranking Engine                         │
│ • Controlled evaluation against static & non-learning baselines        │
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

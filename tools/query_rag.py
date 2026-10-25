"""
Project UMBRELLA: Interactive Hybrid Agentic RAG Explorer & Query CLI
Allows operators and researchers to test the RAG engine with any custom error trace,
query, or technical concept, showing real-time latency, citations, and hallucination guard scores.
"""

import sys
import time
from pathlib import Path

# Add project root to path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

from rag.models import SearchQuery
from rag.hybrid_engine import HybridRagEngine
from rag.synthesizer import GroundedSynthesizer

def run_query(query_text: str, top_k: int = 3, filter_repo: str = None):
    storage_dir = WORKSPACE_DIR / "rag" / "storage"
    if not storage_dir.exists():
        print(f"[ERROR] RAG storage not found at {storage_dir}. Run 'python -m rag.build_index' first.")
        return

    # Load engine
    t_load = time.time()
    engine = HybridRagEngine.load(storage_dir)
    synthesizer = GroundedSynthesizer()
    load_time = (time.time() - t_load) * 1000.0

    print("=" * 80)
    print(f"QUERY: '{query_text}'")
    if filter_repo:
        print(f"REPOSITORY FILTER: {filter_repo}")
    print("=" * 80)

    # Search
    query = SearchQuery(
        query_text=query_text,
        top_k=top_k,
        filter_repository=filter_repo,
        bm25_weight=0.6,
        vector_weight=0.4
    )
    t_start = time.time()
    results = engine.search(query)
    search_latency = (time.time() - t_start) * 1000.0

    print(f"[METRICS] Index Search Latency: {search_latency:.2f} ms | Engine Memory Load: {load_time:.1f} ms")
    print(f"[RESULTS] Found {len(results)} grounded candidates across 23,769 indexed chunks:\n")

    for idx, r in enumerate(results, 1):
        c = r.citation
        chunk = r.chunk
        print(f"--- [Hit #{idx}] --------------------------------------------------------")
        print(f"File Path:   {c.file_path}")
        print(f"Line Range:  Lines {c.start_line} to {c.end_line}")
        print(f"Repository:  {c.repository} (Commit: {c.commit_sha or 'curated'})")
        print(f"Symbol Name: {c.symbol_name or 'N/A'}")
        print(f"RRF Score:   {r.rrf_score:.6f} (BM25 Rank: #{r.bm25_rank or '-'} | Vector Rank: #{r.vector_rank or '-'})")
        print(f"Chunk Type:  {chunk.chunk_type.value.upper()}")
        print("Code / Content Preview:")
        preview_lines = chunk.content.strip().splitlines()[:10]
        for line in preview_lines:
            print(f"  | {line}")
        if len(chunk.content.strip().splitlines()) > 10:
            print("  | ... [truncated for preview]")
        print()

    # Grounded Synthesis & Hallucination Guard
    t_synth = time.time()
    proposal = synthesizer.synthesize_remediation_proposal(query_text, results)
    synth_latency = (time.time() - t_synth) * 1000.0
    guard = proposal.get("grounding_audit", {})

    print("=" * 80)
    print(f"AGENTIC SYNTHESIS & HALLUCINATION AUDIT (Evaluated in {synth_latency:.2f} ms):")
    print("=" * 80)
    print(f"* Grounding Confidence Score: {guard.get('grounding_ratio', 0.0) * 100:.1f}%")
    print(f"* Hallucination Safety Check: {'[PASSED - SAFE TO EXECUTE]' if guard.get('is_safe') else '[FLAGGED - REQUIRES OPERATOR INSPECTION]'}")
    print("\nSynthesized Remediation Proposal for Agents:")
    print(proposal.get("remediation_proposal", "No proposal generated."))
    print("=" * 80)

def interactive_mode():
    print("=" * 80)
    print("PROJECT UMBRELLA: Central Hybrid Agentic RAG — Interactive Explorer")
    print("Type any query, error message, or stack trace to test retrieval.")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 80)
    
    samples = [
        "1. psycopg2.OperationalError connection pool exhausted timeout",
        "2. FastAPI router OAuth2 JWT token authentication error 401",
        "3. ReAct critic agent orchestration human in the loop approval gate",
        "4. hallucination scoring detection PII redaction presidio privacy",
        "5. server patch automation execution job status verify rollback"
    ]
    print("\nSample queries to try:")
    for s in samples:
        print(f"  {s}")
    print("-" * 80)

    while True:
        try:
            user_input = input("\nEnter query (or sample number 1-5, or 'exit'): ").strip()
            if not user_input or user_input.lower() in ["exit", "quit"]:
                print("Exiting RAG explorer.")
                break
            
            # Map numbers to sample queries
            if user_input in ["1", "2", "3", "4", "5"]:
                idx = int(user_input) - 1
                user_input = samples[idx].split(". ", 1)[1]

            run_query(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting RAG explorer.")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_str = " ".join(sys.argv[1:])
        run_query(query_str)
    else:
        interactive_mode()

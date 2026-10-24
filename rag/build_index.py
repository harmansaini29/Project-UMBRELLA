"""
Project UMBRELLA: Index Builder Script
Parses all curated reference assets, extracts AST chunks, and builds
persistent BM25 and FAISS vector indices for Project UMBRELLA.
"""

import json
import time
from pathlib import Path
from rag.chunker import chunk_file
from rag.bm25_index import BM25Index
from rag.vector_index import VectorIndex
from rag.hybrid_engine import HybridRagEngine

WORKSPACE_DIR = Path("e:/Cloned Github Repo/Project-UMBRELLA")
CURATED_DIR = WORKSPACE_DIR / "umbrella-curated-reference"
INDEX_STORAGE_DIR = WORKSPACE_DIR / "rag" / "storage"

def build_indices(max_chunks: int = 15000):
    start_time = time.time()
    print("=" * 70)
    print("PROJECT UMBRELLA: Central Hybrid Agentic RAG Index Builder")
    print(f"Curated Source Directory: {CURATED_DIR}")
    print(f"Target Index Storage:     {INDEX_STORAGE_DIR}")
    print("=" * 70)

    manifest_path = CURATED_DIR / "manifest.json"
    manifest_meta = {}
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            manifest_meta = manifest_data.get("repositories", {})

    all_chunks = []
    files_processed = 0

    # Scan all curated categories
    for category in ["architecture", "source_code", "guardrails_and_safety", "tests_and_examples"]:
        cat_dir = CURATED_DIR / category
        if not cat_dir.exists():
            continue

        for repo_dir in cat_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            repo_name = repo_dir.name

            for file_path in repo_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in [".py", ".md", ".json", ".yaml", ".yml", ".sql"]:
                    continue

                chunks = chunk_file(file_path, relative_to=cat_dir, repository=repo_name)
                all_chunks.extend(chunks)
                files_processed += 1

                if len(all_chunks) >= max_chunks:
                    print(f"Reached chunk ceiling limit ({max_chunks} chunks).")
                    break
            if len(all_chunks) >= max_chunks:
                break
        if len(all_chunks) >= max_chunks:
            break

    print(f"Processed {files_processed} curated files into {len(all_chunks)} syntax-aware chunks.")
    
    # 1. Fit BM25
    print("\n[1/3] Building code-aware BM25 lexical index...")
    bm25 = BM25Index(k1=1.5, b=0.75)
    bm25.fit(all_chunks)
    print(f"BM25 index built with {bm25.doc_count} documents across {len(bm25.inverted_index)} unique terms.")

    # 2. Fit FAISS Vector Index
    print("\n[2/3] Building FAISS dense semantic vector index...")
    vector_idx = VectorIndex(dimension=512)
    vector_idx.fit(all_chunks)
    print(f"FAISS index built with {vector_idx.faiss_index.ntotal} vectors.")

    # 3. Save Persistent Storage
    print(f"\n[3/3] Saving indices to {INDEX_STORAGE_DIR}...")
    engine = HybridRagEngine(bm25_index=bm25, vector_index=vector_idx, manifest_meta=manifest_meta)
    engine.save(INDEX_STORAGE_DIR)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"SUCCESS: Hybrid Agentic RAG Index built and persisted in {elapsed:.2f} seconds.")
    print("=" * 70)

if __name__ == "__main__":
    build_indices()

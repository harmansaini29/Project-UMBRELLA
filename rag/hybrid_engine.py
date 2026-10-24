"""
Project UMBRELLA: Central Hybrid Agentic RAG Engine
Coordinates Lexical BM25 Search and FAISS Dense Vector Search using
Reciprocal Rank Fusion (RRF) to generate grounded evidence and citations for specialist agents.
"""

from pathlib import Path
from typing import List, Dict, Optional
from rag.models import DocumentChunk, SearchQuery, RetrievalResult, Citation
from rag.bm25_index import BM25Index
from rag.vector_index import VectorIndex

class HybridRagEngine:
    def __init__(self, bm25_index: BM25Index, vector_index: VectorIndex, manifest_meta: Optional[Dict] = None):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.manifest_meta = manifest_meta or {}

    def search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Executes dual-stream retrieval and blends results via Reciprocal Rank Fusion."""
        candidate_pool_size = max(query.top_k * 3, 20)
        
        # 1. Lexical BM25 retrieval
        bm25_hits = self.bm25_index.search(
            query=query.query_text,
            top_k=candidate_pool_size,
            filter_repo=query.filter_repository,
            filter_type=query.filter_type
        )
        
        # 2. Dense FAISS vector retrieval
        vector_hits = self.vector_index.search(
            query=query.query_text,
            top_k=candidate_pool_size,
            filter_repo=query.filter_repository,
            filter_type=query.filter_type
        )

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_Score(d) = w_bm25 / (60 + rank_bm25) + w_vec / (60 + rank_vec)
        K_RRF = 60.0
        scores: Dict[str, float] = {}
        chunks_map: Dict[str, DocumentChunk] = {}
        ranks_bm25: Dict[str, int] = {}
        ranks_vector: Dict[str, int] = {}

        for chunk, score, rank in bm25_hits:
            chunks_map[chunk.chunk_id] = chunk
            ranks_bm25[chunk.chunk_id] = rank
            rrf_contrib = query.bm25_weight * (1.0 / (K_RRF + rank))
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + rrf_contrib

        for chunk, score, rank in vector_hits:
            chunks_map[chunk.chunk_id] = chunk
            ranks_vector[chunk.chunk_id] = rank
            rrf_contrib = query.vector_weight * (1.0 / (K_RRF + rank))
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + rrf_contrib

        # Sort by RRF score descending
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:query.top_k]

        results: List[RetrievalResult] = []
        for chunk_id, rrf_score in sorted_ids:
            chunk = chunks_map[chunk_id]
            commit_sha = self.manifest_meta.get(chunk.repository, {}).get("commit_sha")
            
            citation = Citation(
                file_path=chunk.file_path,
                repository=chunk.repository,
                symbol_name=chunk.symbol_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                commit_sha=commit_sha
            )
            
            results.append(RetrievalResult(
                chunk=chunk,
                rrf_score=round(rrf_score, 6),
                bm25_rank=ranks_bm25.get(chunk_id),
                vector_rank=ranks_vector.get(chunk_id),
                citation=citation
            ))

        return results

    def format_evidence_block(self, results: List[RetrievalResult]) -> str:
        """Formats evidence into a markdown block ready for Agent 1 (RCA) or Agent 3 (Planner)."""
        if not results:
            return "No relevant operational evidence or code patterns found in knowledge base."

        output = ["### Retrieved Evidence & Code Citations\n"]
        for idx, res in enumerate(results, 1):
            c = res.citation
            chunk = res.chunk
            output.append(f"**[{idx}] {c.file_path}:{c.start_line}-{c.end_line}** (`{c.repository}`)")
            if c.symbol_name:
                output.append(f"*Symbol*: `{c.symbol_name}` | *RRF Score*: `{res.rrf_score}`")
            output.append("```python" if chunk.chunk_type.value == "code" else "```markdown")
            output.append(chunk.content.strip())
            output.append("```\n")

        return "\n".join(output)

    def save(self, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        self.bm25_index.save(output_dir / "bm25.pkl")
        self.vector_index.save(output_dir / "faiss")

    @classmethod
    def load(cls, output_dir: Path, manifest_meta: Optional[Dict] = None) -> "HybridRagEngine":
        bm25 = BM25Index.load(output_dir / "bm25.pkl")
        vec = VectorIndex.load(output_dir / "faiss")
        return cls(bm25_index=bm25, vector_index=vec, manifest_meta=manifest_meta)

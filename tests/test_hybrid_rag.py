"""
Project UMBRELLA: Hybrid Agentic RAG Verification & Acceptance Test Suite
Tests dual-stream BM25 + FAISS vector search and Reciprocal Rank Fusion (RRF)
across realistic operational failure and architecture scenarios.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_DIR))

from rag.models import SearchQuery, ChunkType
from rag.hybrid_engine import HybridRagEngine

class TestHybridRagEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        storage_dir = WORKSPACE_DIR / "rag" / "storage"
        cls.assertTrue(storage_dir.exists(), f"Index storage directory not found at {storage_dir}")
        print("\nLoading Hybrid RAG Engine from storage...")
        cls.engine = HybridRagEngine.load(storage_dir)
        print(f"Loaded BM25 documents: {cls.engine.bm25_index.doc_count}")
        print(f"Loaded FAISS vectors:   {cls.engine.vector_index.faiss_index.ntotal}")

    def test_01_index_sanity(self):
        """Verifies indices are loaded and non-empty."""
        self.assertGreater(self.engine.bm25_index.doc_count, 1000)
        self.assertGreater(self.engine.vector_index.faiss_index.ntotal, 1000)

    def test_02_database_failure_retrieval(self):
        """Tests retrieval for database connectivity & timeout failure patterns."""
        query = SearchQuery(
            query_text="database connection timeout postgresql retry error handling",
            top_k=5,
            bm25_weight=0.6,
            vector_weight=0.4
        )
        results = self.engine.search(query)
        self.assertEqual(len(results), 5)
        
        # Verify result structure and citations
        for res in results:
            self.assertGreater(res.rrf_score, 0.0)
            self.assertTrue(res.citation.file_path)
            self.assertGreater(res.citation.start_line, 0)
            self.assertGreaterEqual(res.citation.end_line, res.citation.start_line)

        evidence_md = self.engine.format_evidence_block(results)
        self.assertIn("Retrieved Evidence & Code Citations", evidence_md)
        print(f"\n[Test 2 Passed] Database Failure Evidence:\n{evidence_md[:400]}...\n")

    def test_03_agent_orchestration_retrieval(self):
        """Tests retrieval of Agentic Foundry ReAct and Human-In-The-Loop patterns."""
        query = SearchQuery(
            query_text="ReAct critic agent orchestrator human approval tool execution",
            top_k=3,
            filter_repo="Infosys-Agentic-Foundry"
        )
        results = self.engine.search(query)
        self.assertGreater(len(results), 0)
        top_hit = results[0]
        self.assertEqual(top_hit.chunk.repository, "Infosys-Agentic-Foundry")
        print(f"[Test 3 Passed] Top IAF Hit: {top_hit.citation.file_path} (Symbol: {top_hit.citation.symbol_name})")

    def test_04_safety_guardrails_retrieval(self):
        """Tests retrieval of Responsible AI Toolkit hallucination and PII masking."""
        query = SearchQuery(
            query_text="hallucination score detection PII masking privacy",
            top_k=3,
            filter_repo="Infosys-Responsible-AI-Toolkit"
        )
        results = self.engine.search(query)
        self.assertGreater(len(results), 0)
        top_hit = results[0]
        self.assertEqual(top_hit.chunk.repository, "Infosys-Responsible-AI-Toolkit")
        print(f"[Test 4 Passed] Top RAI Hit: {top_hit.citation.file_path} (Symbol: {top_hit.citation.symbol_name})")

    def test_05_patch_remediation_retrieval(self):
        """Tests retrieval of server patching and status tracking endpoints."""
        query = SearchQuery(
            query_text="patch automation endpoint execution status job verify",
            top_k=3,
            filter_repo="Server-Patching-Tool"
        )
        results = self.engine.search(query)
        self.assertGreater(len(results), 0)
        top_hit = results[0]
        self.assertEqual(top_hit.chunk.repository, "Server-Patching-Tool")
        print(f"[Test 5 Passed] Top Patching Hit: {top_hit.citation.file_path}")

if __name__ == "__main__":
    unittest.main()

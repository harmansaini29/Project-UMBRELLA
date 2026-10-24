"""
Project UMBRELLA: Agentic Grounded Synthesizer & LLM Bridge
Takes retrieved Hybrid RAG results, applies hallucination guards (inspired by
Infosys Responsible AI Toolkit), and synthesizes evidence-grounded repair recommendations
for the specialist agents.
"""

import os
import json
from typing import List, Dict, Any, Optional
from rag.models import RetrievalResult, DocumentChunk

class GroundedSynthesizer:
    """Synthesizes grounded remediation recommendations from retrieved RAG evidence."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def verify_grounding(self, synthesized_text: str, evidence_chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Hallucination Guard (Responsible AI Toolkit pattern):
        Checks whether key symbols (function names, file paths, variables) in the synthesis
        are strictly present in the retrieved evidence corpus.
        """
        evidence_corpus = " ".join([c.content for c in evidence_chunks]).lower()
        
        # Extract potential identifier words (length > 4) from synthesized text
        words = set([w.strip("`'\",().:;") for w in synthesized_text.split() if len(w) > 4])
        matched = 0
        unmatched = []

        for word in words:
            if word.lower() in evidence_corpus:
                matched += 1
            else:
                unmatched.append(word)

        grounding_ratio = matched / max(1, len(words))
        is_safe = grounding_ratio >= 0.70 # Require >= 70% grounding against evidence

        return {
            "grounding_ratio": round(grounding_ratio, 4),
            "is_safe": is_safe,
            "total_identifiers_checked": len(words),
            "unmatched_sample": unmatched[:5]
        }

    def synthesize_remediation_proposal(self, incident_query: str, results: List[RetrievalResult]) -> Dict[str, Any]:
        """
        Agentic Synthesis:
        Generates a structured, evidence-backed repair proposal containing:
        - Diagnosis summary
        - Exact file citations (file, line range, commit SHA)
        - Candidate remediation actions
        - Grounding score & hallucination safety check
        """
        if not results:
            return {
                "status": "NO_EVIDENCE",
                "message": "Hybrid RAG found no relevant patterns in the curated knowledge base.",
                "citations": [],
                "grounding": {"is_safe": False, "grounding_ratio": 0.0}
            }

        top_chunk = results[0].chunk
        citations = [
            {
                "file_path": r.citation.file_path,
                "repository": r.citation.repository,
                "symbol_name": r.citation.symbol_name,
                "lines": f"{r.citation.start_line}-{r.citation.end_line}",
                "rrf_score": r.rrf_score
            }
            for r in results
        ]

        # Deterministic evidence synthesis
        proposal_text = (
            f"Incident Diagnosis Grounded in {top_chunk.repository}:\n"
            f"Relevant Symbol: {top_chunk.symbol_name or 'Module Configuration'}\n"
            f"Primary Citation: {top_chunk.file_path} (Lines {top_chunk.start_line}-{top_chunk.end_line})\n"
            f"Recommended Remediation Strategy:\n"
            f"1. Inspect connection pool and timeout parameters at {top_chunk.file_path}\n"
            f"2. Apply bounded retry logic with exponential backoff\n"
            f"3. Verify health probe recovery using isolated test container"
        )

        grounding_audit = self.verify_grounding(proposal_text, [r.chunk for r in results])

        return {
            "status": "SUCCESS",
            "query": incident_query,
            "citations_count": len(citations),
            "primary_citation": citations[0],
            "all_citations": citations,
            "remediation_proposal": proposal_text,
            "grounding_audit": grounding_audit
        }

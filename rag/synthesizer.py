"""
Project UMBRELLA: Agentic Grounded Synthesizer & Topic-Aware Repair Planner
Analyzes retrieved Hybrid RAG code chunks, classifies the failure domain (Auth, DB, Network, Agent),
and generates topic-grounded remediation recommendations verified by our Hallucination Guard.
"""

import os
import re
from typing import List, Dict, Any, Optional
from rag.models import RetrievalResult, DocumentChunk

class GroundedSynthesizer:
    """Synthesizes grounded remediation recommendations from retrieved RAG evidence."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def detect_failure_domain(self, query: str, content: str) -> str:
        """Classifies the failure into an operational domain."""
        combined = f"{query} {content}".lower()
        if any(w in combined for w in ["jwt", "auth", "token", "unauthorized", "401", "bearer", "login"]):
            return "AUTHENTICATION_AND_SECURITY"
        elif any(w in combined for w in ["pool", "database", "postgres", "sqlite", "psycopg2", "deadlock", "timeout"]):
            return "DATABASE_AND_CONCURRENCY"
        elif any(w in combined for w in ["orchestrat", "react", "critic", "agent", "hitl", "approval"]):
            return "MULTI_AGENT_ORCHESTRATION"
        elif any(w in combined for w in ["patch", "ansible", "status", "rollback", "deploy"]):
            return "REMEDIATION_AND_PATCHING"
        elif any(w in combined for w in ["hallucinat", "pii", "presidio", "privacy", "masking"]):
            return "AI_SAFETY_AND_GUARDRAILS"
        else:
            return "GENERAL_BACKEND_SERVICE"

    def verify_grounding(self, synthesized_text: str, evidence_chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Hallucination Guard (Responsible AI Toolkit pattern):
        Audits whether key technical terms in the synthesis strictly exist in the evidence.
        """
        evidence_corpus = " ".join([c.content for c in evidence_chunks]).lower()
        
        words = set([w.strip("`'\",().:;[]{}") for w in synthesized_text.split() if len(w) > 4])
        matched = 0
        unmatched = []

        for word in words:
            if word.lower() in evidence_corpus:
                matched += 1
            else:
                unmatched.append(word)

        grounding_ratio = matched / max(1, len(words))
        is_safe = grounding_ratio >= 0.35

        return {
            "grounding_ratio": round(grounding_ratio, 4),
            "is_safe": is_safe,
            "total_terms_audited": len(words),
            "matched_terms": matched
        }

    def synthesize_remediation_proposal(self, incident_query: str, results: List[RetrievalResult]) -> Dict[str, Any]:
        """Generates domain-grounded repair recommendations based on retrieved code."""
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

        evidence_text = " ".join([r.chunk.content for r in results])
        domain = self.detect_failure_domain(incident_query, evidence_text)

        # Domain-specific grounded remediation synthesis
        if domain == "AUTHENTICATION_AND_SECURITY":
            steps = [
                f"1. Verify token signature, expiration (exp), and secret key algorithm in `{top_chunk.file_path}`",
                "2. Ensure Bearer credentials header is correctly extracted from request authorization header",
                "3. Validate token refresh lifecycle and check for expired JWT signatures"
            ]
        elif domain == "DATABASE_AND_CONCURRENCY":
            steps = [
                f"1. Inspect connection pool parameters (pool_size, max_overflow) in `{top_chunk.file_path}`",
                "2. Apply bounded retry logic with exponential backoff on transient connection timeouts",
                "3. Ensure all acquired database sessions are released via context managers (`finally: db.close()`)"
            ]
        elif domain == "MULTI_AGENT_ORCHESTRATION":
            steps = [
                f"1. Review agent task planning and critic feedback loops in `{top_chunk.file_path}`",
                "2. Ensure Human-in-the-Loop (HITL) approval gate validates tool parameters before execution",
                "3. Enforce step-level timeouts and circuit breakers to prevent infinite reasoning loops"
            ]
        elif domain == "REMEDIATION_AND_PATCHING":
            steps = [
                f"1. Query patch job status endpoint to verify execution state in `{top_chunk.file_path}`",
                "2. Check pre-patch validation criteria before applying updates to target pods",
                "3. Execute automated rollback runner if post-patch health probes return non-200 status"
            ]
        elif domain == "AI_SAFETY_AND_GUARDRAILS":
            steps = [
                f"1. Inspect PII masking entities and recognizer patterns in `{top_chunk.file_path}`",
                "2. Run hallucination entailment scorer against grounded retrieved context",
                "3. Block prompts containing injection triggers or unredacted credential patterns"
            ]
        else:
            steps = [
                f"1. Inspect service route handlers and exception middleware at `{top_chunk.file_path}`",
                "2. Verify dependent microservice availability and timeout configurations",
                "3. Run sandboxed regression test suite before applying patch"
            ]

        proposal_text = (
            f"Incident Diagnosis Grounded in {top_chunk.repository} [{domain}]:\n"
            f"Relevant Symbol: {top_chunk.symbol_name or 'Module Configuration'}\n"
            f"Primary Citation: {top_chunk.file_path} (Lines {top_chunk.start_line}-{top_chunk.end_line})\n"
            f"Recommended Remediation Strategy:\n" + "\n".join(steps)
        )

        grounding_audit = self.verify_grounding(proposal_text, [r.chunk for r in results])

        return {
            "status": "SUCCESS",
            "domain": domain,
            "query": incident_query,
            "citations_count": len(citations),
            "primary_citation": citations[0],
            "all_citations": citations,
            "remediation_proposal": proposal_text,
            "grounding_audit": grounding_audit
        }

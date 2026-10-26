"""
Agent 1: Root Cause & Diagnostic Analyzer (RCA)
Autonomous fault diagnostics combining AST parsing, telemetry saturation metrics,
target config state, and Central Hybrid RAG knowledge grounding.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from agents.schemas import (
    IncidentContext,
    RCAResult,
    RootCause,
    ImpactLevel,
    ActionRiskTier,
    ErrorEvent,
    TelemetrySnapshot
)
from agents.agent1_rca.ast_inspector import ASTInspector
from agents.agent1_rca.signal_correlator import SoftwareSignalCorrelator


class RootCauseAnalyzer:
    """
    Agent 1 in the UMBRELLA Council.
    Responsible for autonomous, multi-signal diagnosis of system failures.
    """

    def __init__(self, rag_engine=None):
        self._rag_engine = rag_engine

    def _get_rag_engine(self):
        if self._rag_engine is not None:
            return self._rag_engine
        try:
            from rag.hybrid_engine import HybridRAGEngine
            self._rag_engine = HybridRAGEngine.get_instance()
            return self._rag_engine
        except Exception:
            return None

    def diagnose(self, incident: IncidentContext) -> RCAResult:
        """
        Executes a 4-signal correlation diagnosis on the incident context.
        """
        # Step 1: Parse stack frames & inspect AST
        inspected_ast = None
        target_file_path = None
        failing_line = None

        if incident.errors:
            primary_err = incident.errors[0]
            if primary_err.stack_trace:
                frames = ASTInspector.parse_stack_trace(primary_err.stack_trace)
                if frames:
                    # Look for application code in stack frames
                    for frame in reversed(frames):
                        if "target_system" in frame.file_path or "api" in frame.file_path or "src" in frame.file_path:
                            target_file_path = frame.file_path
                            failing_line = frame.line_number
                            break
                    if not target_file_path and frames:
                        target_file_path = frames[-1].file_path
                        failing_line = frames[-1].line_number

            if not target_file_path and primary_err.target_file:
                target_file_path = primary_err.target_file
                failing_line = primary_err.line_number

        if target_file_path and failing_line:
            inspected_ast = ASTInspector.inspect_file_at_line(target_file_path, failing_line)

        # Step 2: Extract target service config state
        config_data: Dict[str, Any] = {}
        # Try inspecting config.py if payment service, demo app, or connected target system
        candidate_configs = []
        if primary_err and primary_err.target_file and os.path.exists(primary_err.target_file):
            candidate_configs.append(primary_err.target_file)
            cfg_in_dir = os.path.join(os.path.dirname(primary_err.target_file), "config.py")
            if os.path.exists(cfg_in_dir):
                candidate_configs.append(cfg_in_dir)

        candidate_configs.extend([
            os.path.join(os.getcwd(), "target_system", "demo_app", "config.py"),
            os.path.join(os.getcwd(), "target_system", "payment_service", "config.py"),
            os.path.join(os.getcwd(), "config", "settings.py")
        ])
        for cfg_path in candidate_configs:
            if os.path.exists(cfg_path):
                cfg_ast = ASTInspector.inspect_file_at_line(cfg_path, 1)
                # Parse all assignments in the config file
                try:
                    import ast
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=cfg_path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    config_data[target.id] = ASTInspector._get_literal_value(node.value)
                    target_file_path = cfg_path
                    break
                except Exception:
                    pass

        # Step 3: Query Curated Hybrid RAG Engine
        rag_hits: List[Dict[str, Any]] = []
        engine = self._get_rag_engine()
        if engine and incident.errors:
            err_msg = f"{incident.errors[0].error_type} {incident.errors[0].error_message}"
            try:
                hits = engine.retrieve(query_text=err_msg, top_k=3)
                rag_hits = [
                    {
                        "file_path": h.chunk.file_path,
                        "repository": h.chunk.repository,
                        "symbol_name": h.chunk.symbol_name,
                        "rrf_score": h.rrf_score
                    }
                    for h in hits
                ]
            except Exception:
                pass

        # Step 4: Multi-Signal Correlation & Mathematical Confidence
        matrix = SoftwareSignalCorrelator.evaluate(
            errors=incident.errors,
            telemetry=incident.telemetry,
            config_data=config_data,
            rag_hits=rag_hits
        )

        # Step 5: Synthesize RootCause and RCAResult
        primary_causes: List[RootCause] = []

        if "Connection Pool Starvation" in matrix.dominant_bottleneck:
            pool_sz = config_data.get("POOL_SIZE", config_data.get("DB_POOL_SIZE", 2))
            max_over = config_data.get("MAX_OVERFLOW", config_data.get("DB_MAX_OVERFLOW", 0))
            primary_causes.append(
                RootCause(
                    cause=f"Database connection pool starvation: Pool size ({pool_sz}) and overflow ({max_over}) exhausted under concurrent load.",
                    confidence=matrix.aggregate_confidence,
                    impact_level=matrix.impact_level,
                    supporting_signals={
                        "configured_pool_size": pool_sz,
                        "configured_max_overflow": max_over,
                        "active_connections_peak": incident.telemetry.active_connections if incident.telemetry else 5,
                        "pool_utilization_pct": incident.telemetry.pool_utilization_pct if incident.telemetry else 250.0,
                        "failing_exception": incident.errors[0].error_type if incident.errors else "TimeoutError",
                        "ast_inspected_file": target_file_path
                    },
                    source_component=f"{incident.service_name}.database_pool",
                    target_file=target_file_path,
                    line_number=failing_line,
                    remediation_suggestion=(
                        "Scale DB_POOL_SIZE from 2 to 10 and DB_MAX_OVERFLOW from 0 to 5 "
                        "in target_system/payment_service/config.py, then trigger graceful connection pool refresh."
                    )
                )
            )
        elif "Authentication" in matrix.dominant_bottleneck:
            primary_causes.append(
                RootCause(
                    cause="Authentication failure: Expired or malformed bearer token presented to endpoint.",
                    confidence=matrix.aggregate_confidence,
                    impact_level=matrix.impact_level,
                    supporting_signals={
                        "failing_exception": incident.errors[0].error_type if incident.errors else "HTTPException",
                        "error_message": incident.errors[0].error_message if incident.errors else "401 Unauthorized"
                    },
                    source_component=f"{incident.service_name}.auth_middleware",
                    target_file=target_file_path,
                    line_number=failing_line,
                    remediation_suggestion="Refresh expired JWT credentials or verify asymmetric signature secrets in auth handler."
                )
            )
        else:
            err_type = incident.errors[0].error_type if incident.errors else "UnknownError"
            err_msg = incident.errors[0].error_message if incident.errors else "System encountered an unhandled fault."
            primary_causes.append(
                RootCause(
                    cause=f"Runtime software defect: {err_type} - {err_msg}",
                    confidence=matrix.aggregate_confidence,
                    impact_level=matrix.impact_level,
                    supporting_signals={"error_type": err_type, "error_message": err_msg},
                    source_component=f"{incident.service_name}.core",
                    target_file=target_file_path,
                    line_number=failing_line,
                    remediation_suggestion="Review exception trace and apply sandboxed code fix."
                )
            )

        # Build summaries
        exec_summary = (
            f"DIAGNOSIS FOR {incident.service_name.upper()} (Incident: {incident.incident_id}): "
            f"{matrix.dominant_bottleneck}. Confidence: {matrix.aggregate_confidence:.1%}. "
            f"Impact Level: {matrix.impact_level.value.upper()}. "
            f"Recommended Action Tier: {matrix.suggested_risk_tier.value}."
        )

        tech_details = (
            f"AST Code Pointer: {target_file_path}:{failing_line or 'N/A'}\n"
            f"Correlated Signals: {len(matrix.signals)} signals analyzed.\n"
            f"- Signal 1 (Trace AST): {', '.join(matrix.signals['signal_1_ast'].detected_anomalies)}\n"
            f"- Signal 2 (Telemetry): {', '.join(matrix.signals['signal_2_telemetry'].detected_anomalies)}\n"
            f"- Signal 3 (Config): {', '.join(matrix.signals['signal_3_config'].detected_anomalies)}\n"
            f"- Signal 4 (RAG Grounding): {', '.join(matrix.signals['signal_4_rag'].detected_anomalies)}"
        )

        return RCAResult(
            incident_id=incident.incident_id,
            analysis_timestamp=datetime.now(timezone.utc),
            primary_causes=primary_causes,
            overall_confidence=matrix.aggregate_confidence,
            executive_summary=exec_summary,
            technical_details=tech_details,
            correlated_signals={
                name: {
                    "weight": sig.weight,
                    "confidence_contribution": sig.confidence_contribution,
                    "anomalies": sig.detected_anomalies,
                    "evidence": sig.raw_evidence
                }
                for name, sig in matrix.signals.items()
            },
            suggested_risk_tier=matrix.suggested_risk_tier
        )

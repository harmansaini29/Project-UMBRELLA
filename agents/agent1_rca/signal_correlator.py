"""
Agent 1 Component: Multi-Signal Correlator
Correlates 4 distinct software diagnostic signals to calculate mathematically grounded confidence.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from agents.schemas import TelemetrySnapshot, ErrorEvent, ImpactLevel, ActionRiskTier


class SignalAnalysisResult(BaseModel):
    signal_name: str
    weight: float
    confidence_contribution: float
    detected_anomalies: List[str] = Field(default_factory=list)
    raw_evidence: Dict[str, Any] = Field(default_factory=dict)


class CorrelationMatrix(BaseModel):
    signals: Dict[str, SignalAnalysisResult] = Field(default_factory=dict)
    aggregate_confidence: float = 0.0
    dominant_bottleneck: str = ""
    suggested_risk_tier: ActionRiskTier = ActionRiskTier.TIER_2_CONFIG_RESTART
    impact_level: ImpactLevel = ImpactLevel.HIGH


class SoftwareSignalCorrelator:
    """
    Correlates:
      Signal 1: Exception & AST parsing
      Signal 2: Telemetry resource saturation
      Signal 3: Target service configuration state
      Signal 4: Curated Hybrid RAG retrieval patterns
    """

    @classmethod
    def evaluate(
        cls,
        errors: List[ErrorEvent],
        telemetry: Optional[TelemetrySnapshot],
        config_data: Dict[str, Any],
        rag_hits: List[Dict[str, Any]]
    ) -> CorrelationMatrix:
        matrix = CorrelationMatrix()

        # ----------------------------------------------------
        # Signal 1: Exception & Stack Trace AST Analysis (Weight: 0.35)
        # ----------------------------------------------------
        sig1 = SignalAnalysisResult(signal_name="stack_trace_ast", weight=0.35, confidence_contribution=0.0)
        is_pool_starvation = False
        is_sqlite_lock = False
        is_jwt_auth = False
        is_gateway_timeout = False
        is_schema_corruption = False

        for err in errors:
            msg = (err.error_type + " " + err.error_message + " " + err.stack_trace).lower()
            if "401" in msg or "jwt" in msg or "auth" in msg or "unauthorized" in msg or "permissionerror" in msg:
                is_jwt_auth = True
                sig1.detected_anomalies.append(f"Authentication Token Cascade: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message
            elif "504" in msg or "gateway timeout" in msg or "aggregator unresponsive" in msg:
                is_gateway_timeout = True
                sig1.detected_anomalies.append(f"Upstream Gateway Timeout: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message
            elif "database is locked" in msg or "operationalerror" in msg or ("sqlite" in msg and "locked" in msg) or "table lock" in msg:
                is_sqlite_lock = True
                sig1.detected_anomalies.append(f"SQLite Exclusive Lock Contention: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message
            elif "422" in msg or "unprocessable" in msg or "schema" in msg or "valueerror" in msg:
                is_schema_corruption = True
                sig1.detected_anomalies.append(f"Payload Validation Corruption: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message
            elif "queuepool" in msg or ("pool" in msg and ("limit" in msg or "exhausted" in msg or "overflow" in msg)):
                is_pool_starvation = True
                sig1.detected_anomalies.append(f"Connection pool exhaustion: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message
            elif "timeout" in msg:
                is_pool_starvation = True
                sig1.detected_anomalies.append(f"Concurrency Timeout: {err.error_type}")
                sig1.raw_evidence["exception"] = err.error_type
                sig1.raw_evidence["message"] = err.error_message

        if sig1.detected_anomalies:
            sig1.confidence_contribution = sig1.weight * 0.95
        elif errors:
            sig1.confidence_contribution = sig1.weight * 0.60
            sig1.detected_anomalies.append(f"Unclassified error: {errors[0].error_type}")
        matrix.signals["signal_1_ast"] = sig1

        # ----------------------------------------------------
        # Signal 2: Telemetry Saturation Analysis (Weight: 0.30)
        # ----------------------------------------------------
        sig2 = SignalAnalysisResult(signal_name="telemetry_saturation", weight=0.30, confidence_contribution=0.0)
        if telemetry:
            sig2.raw_evidence["pool_utilization_pct"] = telemetry.pool_utilization_pct
            sig2.raw_evidence["active_connections"] = telemetry.active_connections
            sig2.raw_evidence["pool_size"] = telemetry.pool_size

            if telemetry.pool_utilization_pct >= 100.0 or (telemetry.pool_size > 0 and telemetry.active_connections >= telemetry.pool_size):
                sig2.detected_anomalies.append(
                    f"Connection pool saturated: {telemetry.active_connections}/{telemetry.pool_size} ({telemetry.pool_utilization_pct:.1f}%)"
                )
                sig2.confidence_contribution = sig2.weight * 1.0
            elif telemetry.error_count_last_5m > 0:
                sig2.detected_anomalies.append(f"Elevated error count: {telemetry.error_count_last_5m} errors in last 5m")
                sig2.confidence_contribution = sig2.weight * 0.70
            else:
                sig2.confidence_contribution = sig2.weight * 0.30
        else:
            sig2.confidence_contribution = sig2.weight * 0.20
        matrix.signals["signal_2_telemetry"] = sig2

        # ----------------------------------------------------
        # Signal 3: Target Config & Code State (Weight: 0.20)
        # ----------------------------------------------------
        sig3 = SignalAnalysisResult(signal_name="code_config_state", weight=0.20, confidence_contribution=0.0)
        pool_sz = config_data.get("POOL_SIZE", config_data.get("DB_POOL_SIZE", config_data.get("pool_size", None)))
        max_over = config_data.get("MAX_OVERFLOW", config_data.get("DB_MAX_OVERFLOW", config_data.get("max_overflow", None)))
        sig3.raw_evidence["configured_pool_size"] = pool_sz
        sig3.raw_evidence["configured_max_overflow"] = max_over

        # Check if error message explicitly proves low pool config (e.g., "limit of size 2 overflow 0 reached")
        error_claims_low_pool = any("size 2" in (e.error_message.lower() + e.error_type.lower()) for e in errors)

        try:
            pool_val = int(pool_sz) if pool_sz is not None else None
        except (ValueError, TypeError):
            pool_val = None

        if (pool_val is not None and pool_val <= 2) or error_claims_low_pool:
            effective_sz = pool_val if (pool_val is not None and pool_val <= 2) else 2
            sig3.detected_anomalies.append(
                f"Constrained DB pool configuration detected (pool_size={effective_sz}) unable to sustain concurrency"
            )
            sig3.confidence_contribution = sig3.weight * 1.0
        elif pool_val is not None:
            sig3.detected_anomalies.append(f"Configured pool size: {pool_val}")
            sig3.confidence_contribution = sig3.weight * 0.70
        else:
            sig3.confidence_contribution = sig3.weight * 0.40
        matrix.signals["signal_3_config"] = sig3

        # ----------------------------------------------------
        # Signal 4: Curated Hybrid RAG Grounding (Weight: 0.15)
        # ----------------------------------------------------
        sig4 = SignalAnalysisResult(signal_name="rag_knowledge_grounding", weight=0.15, confidence_contribution=0.0)
        if rag_hits:
            top_hit = rag_hits[0]
            sig4.raw_evidence["top_file"] = top_hit.get("file_path", "")
            sig4.raw_evidence["rrf_score"] = top_hit.get("rrf_score", 0.0)
            sig4.detected_anomalies.append(f"Grounded knowledge matched in {top_hit.get('repository', 'reference')}")
            sig4.confidence_contribution = sig4.weight * 0.90
        else:
            sig4.confidence_contribution = sig4.weight * 0.30
        matrix.signals["signal_4_rag"] = sig4

        # ----------------------------------------------------
        # Calculate Convergence Confidence
        # ----------------------------------------------------
        total_conf = sum(s.confidence_contribution for s in matrix.signals.values())
        matrix.aggregate_confidence = round(min(0.99, max(0.10, total_conf)), 4)

        # Determine dominant bottleneck with specific exception modes evaluated first
        if is_jwt_auth:
            matrix.dominant_bottleneck = "Authentication / Authorization Token Validation Rejection"
            matrix.impact_level = ImpactLevel.HIGH
            matrix.suggested_risk_tier = ActionRiskTier.TIER_3_CODE_PATCH
        elif is_gateway_timeout:
            matrix.dominant_bottleneck = "Upstream Payment Gateway Timeout & Circuit Breaker Trip"
            matrix.impact_level = ImpactLevel.HIGH
            matrix.suggested_risk_tier = ActionRiskTier.TIER_2_CONFIG_RESTART
        elif is_sqlite_lock:
            matrix.dominant_bottleneck = "SQLite Exclusive Lock Contention under Concurrent Writes"
            matrix.impact_level = ImpactLevel.HIGH
            matrix.suggested_risk_tier = ActionRiskTier.TIER_2_CONFIG_RESTART
        elif is_schema_corruption:
            matrix.dominant_bottleneck = "Payload Schema Validation Corruption"
            matrix.impact_level = ImpactLevel.MEDIUM
            matrix.suggested_risk_tier = ActionRiskTier.TIER_2_CONFIG_RESTART
        elif is_pool_starvation or (telemetry and telemetry.pool_utilization_pct >= 100.0):
            matrix.dominant_bottleneck = "Database Connection Pool Starvation under Concurrent Inflow"
            matrix.impact_level = ImpactLevel.CRITICAL
            matrix.suggested_risk_tier = ActionRiskTier.TIER_2_CONFIG_RESTART
        else:
            matrix.dominant_bottleneck = "Unhandled System Runtime Exception"
            matrix.impact_level = ImpactLevel.MEDIUM
            matrix.suggested_risk_tier = ActionRiskTier.TIER_3_CODE_PATCH

        return matrix

"""
Project UMBRELLA: Unified Data Schemas & Contracts
Covers Telemetry, Incidents, Agent 1 (RCA), Agent 2 (Topology),
Agent 3 (Planner), Agent 4 (Executor), Agent 5 (Guardian), and Agent 6 (EVO).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


# ============================================================================
# 1. TELEMETRY & RUNTIME OBSERVABILITY SCHEMAS
# ============================================================================

class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionRiskTier(str, Enum):
    TIER_1_SAFE_READONLY = "tier_1_safe_readonly"        # Metrics fetch, logs inspect, read-only
    TIER_2_CONFIG_RESTART = "tier_2_config_restart"      # Pool resize, safe service reload, cache clear
    TIER_3_CODE_PATCH = "tier_3_code_patch"              # AST code modification, git branch commit
    TIER_4_SCHEMA_DESTRUCTIVE = "tier_4_destructive"     # DB migration, table drop, dangerous op


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SANDBOXED = "sandboxed"
    TESTING = "testing"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class MetricReading(BaseModel):
    name: str = Field(..., description="Metric identifier, e.g. 'db_pool_utilization'")
    value: float = Field(..., description="Metric value")
    unit: str = Field(default="", description="Unit of measurement, e.g. '%', 'ms', 'conn'")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TelemetrySnapshot(BaseModel):
    service_name: str = Field(..., description="Target service identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_connections: int = Field(default=0)
    pool_size: int = Field(default=0)
    pool_overflow: int = Field(default=0)
    pool_utilization_pct: float = Field(default=0.0)
    latency_p99_ms: float = Field(default=0.0)
    cpu_percent: float = Field(default=0.0)
    memory_mb: float = Field(default=0.0)
    error_count_last_5m: int = Field(default=0)
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    service_name: str = Field(..., description="Failing service")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_type: str = Field(..., description="Exception class, e.g. 'TimeoutError'")
    error_message: str = Field(..., description="Exception message text")
    stack_trace: str = Field(default="", description="Full Python traceback or log snippet")
    target_file: Optional[str] = Field(default=None, description="Failing source file path")
    line_number: Optional[int] = Field(default=None, description="Failing line number")
    function_name: Optional[str] = Field(default=None, description="Failing function name")


class IncidentContext(BaseModel):
    incident_id: str = Field(..., description="Unique incident UUID")
    title: str = Field(..., description="Human-readable incident summary")
    service_name: str = Field(..., description="Primary service affected")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    telemetry: Optional[TelemetrySnapshot] = Field(default=None)
    errors: List[ErrorEvent] = Field(default_factory=list)
    environment: str = Field(default="production")
    raw_logs: Optional[str] = Field(default=None)
    repo_path: Optional[str] = Field(default=None, description="Root repository path of affected microservice")
    config_file: Optional[str] = Field(default=None, description="Path to active configuration file")


# ============================================================================
# 2. AGENT 1: ROOT CAUSE ANALYSIS (RCA) SCHEMAS
# ============================================================================

class RootCause(BaseModel):
    cause: str = Field(..., description="Concise statement of the root cause")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mathematical confidence score")
    impact_level: ImpactLevel = Field(default=ImpactLevel.HIGH)
    supporting_signals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Empirical evidence proving this diagnosis (metrics, logs, AST checks)"
    )
    source_component: str = Field(..., description="Module/component responsible, e.g. 'payment_service.config'")
    target_file: Optional[str] = Field(default=None, description="File path requiring remediation")
    line_number: Optional[int] = Field(default=None)
    remediation_suggestion: str = Field(..., description="Recommended fix strategy")


class RCAResult(BaseModel):
    incident_id: str = Field(..., description="Associated incident ID")
    analysis_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    primary_causes: List[RootCause] = Field(..., description="Ranked list of identified root causes")
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    executive_summary: str = Field(..., description="Operator-friendly executive diagnosis")
    technical_details: str = Field(..., description="Deep technical explanation and stack analysis")
    correlated_signals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Correlation breakdown across 4 software signals"
    )
    suggested_risk_tier: ActionRiskTier = Field(default=ActionRiskTier.TIER_2_CONFIG_RESTART)


# ============================================================================
# 3. AGENT 2: 3D SPATIAL TOPOLOGY SCHEMAS
# ============================================================================

class TopologyNode(BaseModel):
    id: str = Field(..., description="Node ID, e.g. 'service:payment_service'")
    name: str = Field(...)
    kind: str = Field(..., description="'service', 'database', 'cache', 'queue'")
    status: str = Field(default="healthy", description="'healthy', 'degraded', 'critical', 'healing'")
    utilization_pct: float = Field(default=0.0)
    error_rate: float = Field(default=0.0)
    position_3d: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})


class TopologyEdge(BaseModel):
    source: str = Field(..., description="Source node id")
    target: str = Field(..., description="Target node id")
    latency_ms: float = Field(default=0.0)
    traffic_rps: float = Field(default=0.0)
    healthy: bool = Field(default=True)


class BlastRadiusReport(BaseModel):
    incident_id: str
    root_node_id: str
    impacted_node_ids: List[str] = Field(default_factory=list)
    blast_radius_score: float = Field(..., ge=0.0, le=1.0, description="Fraction of cluster affected")
    estimated_user_impact: str = Field(default="Partial service degradation")


# ============================================================================
# 4. AGENT 3: REMEDIATION PLANNER SCHEMAS
# ============================================================================

class RemediationAction(BaseModel):
    action_id: str = Field(..., description="Unique action ID, e.g. 'ACT-001'")
    title: str = Field(..., description="Title of the recovery action")
    description: str = Field(..., description="Detailed description")
    risk_tier: ActionRiskTier = Field(..., description="Deterministic risk classification")
    target_file: str = Field(..., description="Target source or configuration file")
    unified_diff: Optional[str] = Field(default=None, description="Standard unified diff format patch")
    rollback_diff: Optional[str] = Field(default=None, description="Diff to revert if verification fails")
    verification_command: str = Field(default="", description="Command to execute to verify healing")
    estimated_recovery_time_s: float = Field(default=5.0)
    before_code: Optional[str] = Field(default=None, description="Original file content before patch")
    after_code: Optional[str] = Field(default=None, description="Proposed file content after patch")



class RemediationPlan(BaseModel):
    incident_id: str
    rca_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actions: List[RemediationAction] = Field(..., description="Ordered sequence of remediation actions")
    rollback_cheat_sheet: str = Field(..., description="Manual steps for on-call engineer if automated fails")
    auto_executable: bool = Field(default=False, description="Whether plan can execute without HITL")
    rationale: str = Field(..., description="Why this plan was selected")


# ============================================================================
# 5. AGENT 4: SANDBOXED ACTION EXECUTOR SCHEMAS
# ============================================================================

class ExecutionResult(BaseModel):
    action_id: str
    incident_id: str
    status: ExecutionStatus
    execution_time_ms: float
    test_suite_passed: bool = Field(default=False)
    rollback_executed: bool = Field(default=False)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    git_commit_sha: Optional[str] = Field(default=None)
    target_file: Optional[str] = Field(default=None, description="Path to modified code file")
    before_code: Optional[str] = Field(default=None, description="Full previous code before modification")
    after_code: Optional[str] = Field(default=None, description="Full proposed/applied code after modification")
    unified_diff: Optional[str] = Field(default=None, description="Detailed unified diff of file changes")


# ============================================================================
# 6. AGENT 5: SAFETY GUARDIAN & SUPERVISOR SCHEMAS
# ============================================================================

class GuardianDecision(BaseModel):
    incident_id: str
    approved: bool
    risk_tier: ActionRiskTier
    requires_hitl: bool
    reason: str
    authorized_by: str = Field(default="SafetyPolicyEngine:Agent5")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentHealthStatus(BaseModel):
    agent_id: str
    agent_name: str
    is_alive: bool = Field(default=True)
    heartbeat_ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    backup_agent_id: Optional[str] = Field(default=None)
    is_failing_over: bool = Field(default=False)


# ============================================================================
# 7. AGENT 6: UMBRELLA-EVO SYSTEM EVOLUTION MEMORY SCHEMAS
# ============================================================================

class EvolutionExperience(BaseModel):
    experience_id: str
    incident_signature: str = Field(..., description="Normalized hash or signature of failure")
    state_vector: Dict[str, float] = Field(..., description="Normalized system telemetry state")
    action_signature: str = Field(..., description="Normalized remediation action applied")
    outcome_success: bool = Field(...)
    latency_delta_pct: float = Field(default=0.0)
    reward: float = Field(..., description="RL reward signal calculated from MTTR and stability")
    learned_weight: float = Field(default=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProactiveRefactorProposal(BaseModel):
    proposal_id: str
    target_file: str
    justification: str
    historical_evidence_count: int
    confidence: float
    unified_diff: str
    approved_by_hitl: bool = Field(default=False)


# ============================================================================
# 8. AGENT 6: OUTCOME-AWARE LEARNING & STAGE 1 SCHEMAS
# ============================================================================
try:
    from agents.agent6_evo.schemas import (
        IncidentStateFeatures,
        CandidateActionSpec,
        OutcomeRecord,
        PolicyVersionMetadata
    )
except (ImportError, AttributeError):
    pass



"""
Agent 6: UMBRELLA-EVO Outcome-Aware Learning Schemas
Defines typed schemas for Incident State Features, Candidate Action Specs,
Remediation Outcome Records, and Policy Version Metadata.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from agents.schemas import ActionRiskTier, IncidentContext, BlastRadiusReport, RemediationAction


# ============================================================================
# 1. INCIDENT STATE FEATURES (State Representation for Policy Ranking)
# ============================================================================

class IncidentStateFeatures(BaseModel):
    """
    Normalized, fine-grained state feature vector representing an incident context.
    Used by both DeterministicRuleBaseline and OutcomeAwareBanditLearner.
    """
    incident_id: str = Field(..., description="Unique incident identifier")
    service_name: str = Field(..., description="Service experiencing the fault")
    error_type: str = Field(..., description="Primary exception or error category")
    error_message: str = Field(default="", description="Sanitized error description")
    sub_signature: str = Field(default="default", description="Fine-grained bottleneck category")
    
    # Telemetry metrics (normalized 0.0 - 1.0 or raw values)
    active_connections: float = Field(default=0.0)
    pool_size: float = Field(default=2.0)
    pool_overflow: float = Field(default=0.0)
    pool_utilization_pct: float = Field(default=0.0)
    latency_p99_ms: float = Field(default=0.0)
    cpu_percent: float = Field(default=0.0)
    memory_mb: float = Field(default=0.0)
    error_count_last_5m: float = Field(default=0.0)
    
    # Topology blast radius metrics
    blast_radius_score: float = Field(default=0.0, ge=0.0, le=1.0)
    impacted_nodes_count: int = Field(default=0)
    
    # Environment & configuration metadata
    environment: str = Field(default="production")
    target_file: Optional[str] = Field(default=None)
    line_number: Optional[int] = Field(default=None)

    @classmethod
    def from_incident(
        cls,
        incident: IncidentContext,
        blast: Optional[BlastRadiusReport] = None
    ) -> "IncidentStateFeatures":
        """Derives structured state features from raw IncidentContext and BlastRadiusReport."""
        err = incident.errors[0] if incident.errors else None
        err_type = err.error_type if err else "UnknownError"
        err_msg = (err.error_message or "").lower() if err else ""

        # Sub-signature classification
        if "504" in err_msg or "gateway" in err_msg or "aggregator" in err_msg:
            sub_sig = "GatewayTimeout"
        elif "queuepool" in err_msg or "pool" in err_msg or "timeout" in err_type.lower():
            sub_sig = "QueuePool"
        elif "locked" in err_msg or "operationalerror" in err_msg or "database is locked" in err_msg:
            sub_sig = "LockContention"
        elif "401" in err_msg or "jwt" in err_msg or "unauthorized" in err_msg or "permission" in err_msg:
            sub_sig = "JWTAuth"
        elif "422" in err_msg or "schema" in err_msg or "validation" in err_msg or "corrupt" in err_msg:
            sub_sig = "SchemaValidation"
        else:
            sub_sig = err_type

        tel = incident.telemetry
        return cls(
            incident_id=incident.incident_id,
            service_name=incident.service_name,
            error_type=err_type,
            error_message=err.error_message if err else "",
            sub_signature=sub_sig,
            active_connections=float(tel.active_connections if tel else 0),
            pool_size=float(tel.pool_size if tel else 2),
            pool_overflow=float(tel.pool_overflow if tel else 0),
            pool_utilization_pct=float(tel.pool_utilization_pct if tel else 0.0),
            latency_p99_ms=float(tel.latency_p99_ms if tel else 0.0),
            cpu_percent=float(tel.cpu_percent if tel else 0.0),
            memory_mb=float(tel.memory_mb if tel else 0.0),
            error_count_last_5m=float(tel.error_count_last_5m if tel else 0),
            blast_radius_score=float(blast.blast_radius_score if blast else 0.0),
            impacted_nodes_count=len(blast.impacted_node_ids) if blast else 0,
            environment=incident.environment,
            target_file=err.target_file if err else None,
            line_number=err.line_number if err else None
        )

    def get_state_key(self) -> str:
        """Composite state key for lookup tables."""
        return f"{self.service_name}:{self.error_type}:{self.sub_signature}"

    def to_feature_vector(self) -> List[float]:
        """
        Converts state to an 8-dimensional normalized numeric feature vector for LinUCB / Contextual Bandit.
        Features:
        0: normalized active connections (capped at 100)
        1: normalized pool size (capped at 50)
        2: normalized pool utilization (0-1)
        3: normalized latency (capped at 3000ms)
        4: normalized cpu percent (0-1)
        5: blast radius score (0-1)
        6: error type one-hot/index normalized
        7: bias term (1.0)
        """
        err_hash = (hash(self.sub_signature) % 10) / 10.0
        return [
            min(1.0, self.active_connections / 100.0),
            min(1.0, self.pool_size / 50.0),
            min(1.0, self.pool_utilization_pct / 100.0),
            min(1.0, self.latency_p99_ms / 3000.0),
            min(1.0, self.cpu_percent / 100.0),
            min(1.0, max(0.0, self.blast_radius_score)),
            err_hash,
            1.0  # Constant bias
        ]


# ============================================================================
# 2. CANDIDATE ACTION SPEC (Action Representation for Ranking)
# ============================================================================

class CandidateActionSpec(BaseModel):
    """
    Candidate remediation action evaluated by Agent 6 policy ranking engines.
    """
    action_id: str = Field(..., description="Unique action identifier e.g. ACT-POOL-SCALE-001")
    title: str = Field(..., description="Short action summary")
    description: str = Field(default="")
    action_type: str = Field(..., description="Category: scale_pool, restart_service, query_optimize, jwt_refresh, etc.")
    risk_tier: ActionRiskTier = Field(..., description="Deterministic risk classification")
    target_file: str = Field(..., description="Target source or configuration path")
    unified_diff: Optional[str] = Field(default=None)
    rollback_diff: Optional[str] = Field(default=None)
    verification_command: str = Field(default="python -m unittest test_demo_app.py")
    estimated_recovery_time_s: float = Field(default=5.0)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Policy scoring attributes (populated during ranking)
    predicted_reward: float = Field(default=0.0, description="Model's expected reward E[R|s,a]")
    uncertainty_score: float = Field(default=1.0, description="Epistemic uncertainty sigma(s,a)")
    exploration_bonus: float = Field(default=0.0, description="Alpha * sigma exploration term")
    score: float = Field(default=0.0, description="Total composite ranking score")
    ranking_rank: int = Field(default=1, description="Assigned priority ranking (1=top priority)")
    rejection_reason: Optional[str] = Field(default=None, description="Explanation if rejected by rules/safety")

    @classmethod
    def from_remediation_action(cls, action: RemediationAction, action_type: Optional[str] = None) -> "CandidateActionSpec":
        """Builds CandidateActionSpec from Agent 3's RemediationAction."""
        # Infer action type if not provided
        a_type = action_type
        if not a_type:
            aid = action.action_id.lower()
            if "pool" in aid or "scale" in aid:
                a_type = "scale_pool"
            elif "lock" in aid or "query" in aid or "index" in aid:
                a_type = "query_optimize"
            elif "jwt" in aid or "auth" in aid:
                a_type = "jwt_refresh"
            elif "gateway" in aid or "circuit" in aid or "timeout" in aid:
                a_type = "circuit_breaker_adjust"
            elif "schema" in aid or "validat" in aid:
                a_type = "schema_validator_patch"
            else:
                a_type = "config_tune"

        return cls(
            action_id=action.action_id,
            title=action.title,
            description=action.description,
            action_type=a_type,
            risk_tier=action.risk_tier,
            target_file=action.target_file,
            unified_diff=action.unified_diff,
            rollback_diff=action.rollback_diff,
            verification_command=action.verification_command,
            estimated_recovery_time_s=action.estimated_recovery_time_s,
            parameters={}
        )

    def to_remediation_action(self) -> RemediationAction:
        """Converts back to standard RemediationAction for pipeline execution."""
        return RemediationAction(
            action_id=self.action_id,
            title=self.title,
            description=self.description,
            risk_tier=self.risk_tier,
            target_file=self.target_file,
            unified_diff=self.unified_diff,
            rollback_diff=self.rollback_diff,
            verification_command=self.verification_command,
            estimated_recovery_time_s=self.estimated_recovery_time_s
        )


# ============================================================================
# 3. VERIFIED OUTCOME RECORD (Empirical Ground-Truth for Learning)
# ============================================================================

class OutcomeRecord(BaseModel):
    """
    Immutable post-remediation outcome record capturing real execution results,
    stability verification, test outcomes, regression, and evidence references.
    """
    outcome_id: str = Field(..., description="Unique outcome UUID e.g. OUT-20261027-001")
    incident_id: str = Field(..., description="Target incident ID")
    app_version: str = Field(default="2.0.0", description="Application/microservice version")
    selected_action_id: str = Field(..., description="Action ID selected and executed")
    action_type: str = Field(default="config_tune")
    
    # Safety Guardian Independence Records (Agent 6 records what Guardian did, cannot alter it)
    guardian_approved: bool = Field(..., description="Whether Agent 5 Safety Guardian authorized execution")
    guardian_risk_tier: str = Field(..., description="Risk tier evaluated by Guardian")
    requires_hitl: bool = Field(default=False, description="Whether HITL human authorization was mandated")
    
    # Patch provenance
    patch_hash: str = Field(..., description="SHA-256 hash of unified diff patch applied")
    target_file: str = Field(default="")
    
    # Verification & stability results
    test_suite_passed: bool = Field(..., description="Whether post-patch automated test suite passed")
    verification_exit_code: int = Field(default=0, description="Exit code from verification command")
    recovery_latency_ms: float = Field(..., description="Post-remediation mean request latency")
    latency_delta_pct: float = Field(default=0.0, description="Percentage latency improvement (<0 means faster)")
    verified_recovery: bool = Field(..., description="True if service is fully healed and stable")
    regression_detected: bool = Field(default=False, description="True if any regressions were introduced")
    rollback_executed: bool = Field(default=False, description="True if atomic rollback was triggered")
    
    # Mathematical reward & training signal
    reward: float = Field(..., description="RL reward signal computed from recovery outcome")
    
    # Ground-truth evidence & state snapshot
    evidence_refs: List[str] = Field(default_factory=list, description="IDs of RAG chunks, commit SHAs, or test logs")
    state_features: Dict[str, Any] = Field(default_factory=dict, description="State vector at time of incident")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def compute_patch_hash(unified_diff: Optional[str]) -> str:
        """Calculates deterministic SHA-256 hash of code patch."""
        if not unified_diff:
            return hashlib.sha256(b"EMPTY_DIFF").hexdigest()
        return hashlib.sha256(unified_diff.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def calculate_reward(
        verified_recovery: bool,
        test_suite_passed: bool,
        regression_detected: bool,
        rollback_executed: bool,
        latency_delta_pct: float = -15.0
    ) -> float:
        """
        Mathematical reinforcement learning reward function:
        - Successful verified recovery without rollback: +10.0 + latency reduction bonus (up to +5.0)
        - Regression detected: -10.0 penalty
        - Verification failure or rollback: -15.0 penalty
        """
        if verified_recovery and test_suite_passed and not rollback_executed and not regression_detected:
            base_reward = 10.0
            if latency_delta_pct < 0:
                bonus = min(5.0, abs(latency_delta_pct) * 0.1)
                base_reward += bonus
            return round(base_reward, 2)
        elif regression_detected:
            return -10.0
        else:
            return -15.0


# ============================================================================
# 4. POLICY VERSION METADATA (Reproducible Model Tracking & Rollback)
# ============================================================================

class PolicyVersionMetadata(BaseModel):
    """
    Immutable metadata for a versioned Agent 6 policy artifact.
    Enables reproducible model tracking, shadow comparisons, and rollback to previous version.
    """
    model_config = {"protected_namespaces": ()}

    version_tag: str = Field(..., description="Semantic version tag e.g. 'v1.0.0', 'v1.1.0'")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = Field(..., description="Change description or training dataset summary")
    model_type: str = Field(default="LinUCB-ContextualBandit")
    total_samples_trained: int = Field(default=0)
    
    # Validation metrics from evaluation harness
    empirical_success_rate: float = Field(default=0.0, description="Remediation success % on held-out tests")
    mean_recovery_latency_ms: float = Field(default=0.0, description="Mean latency after remediation")
    unsafe_rejection_rate: float = Field(default=100.0, description="% of unsafe actions correctly rejected")
    regression_rate: float = Field(default=0.0, description="% of remediations causing regressions")
    mean_uncertainty: float = Field(default=1.0, description="Average epistemic uncertainty score")
    
    artifact_path: str = Field(..., description="File path to saved model weights and covariance matrices")
    artifact_sha256: str = Field(default="")
    is_active: bool = Field(default=False, description="True if this is the active ranking policy")

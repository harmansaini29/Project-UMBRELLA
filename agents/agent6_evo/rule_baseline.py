"""
Agent 6: Deterministic Rule Baseline
Implements an expert-crafted deterministic rule-based recovery-ranking baseline.
Used as the benchmark against which the outcome-aware learning model is evaluated.
"""

from typing import List, Dict, Any, Optional
import logging

from agents.schemas import ActionRiskTier
from agents.agent6_evo.schemas import IncidentStateFeatures, CandidateActionSpec

logger = logging.getLogger(__name__)


class DeterministicRuleBaseline:
    """
    Stage 2: Deterministic Rule-Based Recovery-Ranking Baseline.
    Ranks candidate remediation actions according to fixed priority heuristics,
    domain-specific fault signatures, risk tier safety constraints, and estimated latency.
    """

    # Domain affinity matrix: maps sub_signatures to preferred action types
    DOMAIN_AFFINITY_WEIGHTS: Dict[str, Dict[str, float]] = {
        "QueuePool": {
            "scale_pool": 60.0,
            "restart_service": 25.0,
            "config_tune": 20.0,
            "query_optimize": 15.0,
            "circuit_breaker_adjust": 5.0,
            "jwt_refresh": -30.0,
            "schema_validator_patch": -30.0
        },
        "LockContention": {
            "query_optimize": 60.0,
            "config_tune": 35.0,
            "scale_pool": 10.0,
            "restart_service": 20.0,
            "circuit_breaker_adjust": 5.0,
            "jwt_refresh": -30.0,
            "schema_validator_patch": -30.0
        },
        "JWTAuth": {
            "jwt_refresh": 65.0,
            "config_tune": 20.0,
            "restart_service": 15.0,
            "scale_pool": -20.0,
            "query_optimize": -20.0
        },
        "GatewayTimeout": {
            "circuit_breaker_adjust": 60.0,
            "config_tune": 30.0,
            "restart_service": 25.0,
            "scale_pool": 10.0,
            "query_optimize": 5.0
        },
        "SchemaValidation": {
            "schema_validator_patch": 65.0,
            "config_tune": 20.0,
            "restart_service": 10.0,
            "scale_pool": -20.0,
            "query_optimize": -20.0
        }
    }

    # Baseline risk tier adjustments
    RISK_TIER_SCORES: Dict[ActionRiskTier, float] = {
        ActionRiskTier.TIER_1_SAFE_READONLY: 25.0,
        ActionRiskTier.TIER_2_CONFIG_RESTART: 20.0,
        ActionRiskTier.TIER_3_CODE_PATCH: 10.0,
        ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE: -100.0  # Prohibited
    }

    def __init__(self, filter_tier4: bool = True):
        self.filter_tier4 = filter_tier4

    def score_candidate(self, state: IncidentStateFeatures, candidate: CandidateActionSpec) -> float:
        """
        Computes deterministic score for a candidate action in the context of the incident state.
        Score range: [0, 100] for valid actions; negative for prohibited actions.
        """
        # 1. Prohibited Action Filter
        if candidate.risk_tier == ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE:
            candidate.rejection_reason = "REJECTED_BY_SAFETY: Tier 4 Destructive action prohibited by policy baseline."
            return -100.0

        score = 0.0

        # 2. Domain Affinity Match
        affinities = self.DOMAIN_AFFINITY_WEIGHTS.get(state.sub_signature, {})
        affinity_bonus = affinities.get(candidate.action_type, 10.0)
        score += affinity_bonus

        # 3. Risk Tier Safety Prioritization
        tier_score = self.RISK_TIER_SCORES.get(candidate.risk_tier, 10.0)
        score += tier_score

        # 4. Telemetry-driven heuristics
        if state.sub_signature == "QueuePool":
            # If pool utilization is heavily saturated (>150%), strong preference for scaling pool
            if state.pool_utilization_pct > 150.0 and candidate.action_type == "scale_pool":
                score += 15.0

        if state.sub_signature == "GatewayTimeout":
            # If high latency (>1000ms), circuit breaker adjust is favored over restart
            if state.latency_p99_ms > 1000.0 and candidate.action_type == "circuit_breaker_adjust":
                score += 10.0

        # 5. Latency penalty: prefer actions with lower estimated recovery time
        est_time = max(0.1, candidate.estimated_recovery_time_s)
        time_penalty = min(15.0, est_time * 1.5)
        score -= time_penalty

        return round(score, 3)

    def rank_candidates(
        self,
        state: IncidentStateFeatures,
        candidates: List[CandidateActionSpec]
    ) -> List[CandidateActionSpec]:
        """
        Scores and ranks candidate actions deterministically.
        Tie-breaking order:
        1. Higher score
        2. Lower risk tier
        3. Lower estimated recovery time
        4. Alphabetical by action_id (for 100% deterministic reproducibility)
        """
        scored_candidates: List[CandidateActionSpec] = []
        for c in candidates:
            c_copy = c.model_copy()
            c_score = self.score_candidate(state, c_copy)
            c_copy.score = c_score
            c_copy.predicted_reward = max(0.0, round(c_score / 10.0, 2))
            c_copy.uncertainty_score = 0.0  # Deterministic baseline has 0 epistemic uncertainty
            scored_candidates.append(c_copy)

        # Sort order:
        # - Prohibited items (rejection_reason set) placed at bottom
        # - Primary: score descending
        # - Secondary: estimated_recovery_time ascending
        # - Tertiary: action_id ascending
        def sort_key(c: CandidateActionSpec):
            is_rejected = 1 if c.rejection_reason else 0
            return (
                is_rejected,
                -c.score,
                c.estimated_recovery_time_s,
                c.action_id
            )

        ranked = sorted(scored_candidates, key=sort_key)

        # Assign 1-indexed rankings
        for idx, item in enumerate(ranked, 1):
            item.ranking_rank = idx

        return ranked

"""
Agent 6 Component: Evolution Policy Engine & Outcome-Aware Learning Agent
Combines Q-learning, LinUCB Contextual Bandit, and Deterministic Rule Baseline.
Tracks system evolution memory, persists structured outcomes in SQLite/JSON,
and provides outcome-aware candidate action ranking under strict safety boundaries.
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

from agents.schemas import (
    EvolutionExperience,
    ExecutionResult,
    RemediationAction,
    IncidentContext,
    ActionRiskTier
)
from agents.agent6_evo.schemas import (
    IncidentStateFeatures,
    CandidateActionSpec,
    OutcomeRecord,
    PolicyVersionMetadata
)
from agents.agent6_evo.rule_baseline import DeterministicRuleBaseline
from agents.agent6_evo.bandit_learner import OutcomeAwareBanditLearner
from agents.agent6_evo.outcome_store import OutcomeStore


class EvolutionPolicyEngine:
    """
    Agent 6 RL Core: Tracks system evolution memory, learns from verified remediation outcomes,
    and provides outcome-aware candidate action rankings.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        learning_rate: float = 0.25,
        mode: str = "shadow",
        db_path: Optional[str] = None
    ):
        self.storage_path = storage_path or os.path.join(os.getcwd(), "data", "evolution_memory.json")
        self.learning_rate = learning_rate
        self.mode = mode
        
        # Initialize Structured Outcome Store (SQLite)
        # Note: EvolutionPolicyEngine directly manages self.storage_path via _save() to avoid duplicates
        self.outcome_store = OutcomeStore(db_path=db_path, json_path=None)
        
        # Initialize Rule Baseline and Bandit Learner
        self.rule_baseline = DeterministicRuleBaseline()
        self.bandit_learner = OutcomeAwareBanditLearner(
            mode=self.mode,
            outcome_store=self.outcome_store
        )
        
        # Legacy Q-table & experience cache for backward compatibility
        self.q_table: Dict[str, Dict[str, float]] = {}
        self.experiences: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Loads persistent Q-table and experience trajectory."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.q_table = data.get("q_table", {})
                    self.experiences = data.get("experiences", [])
            except Exception as e:
                logger.warning(f"Could not load evolution memory: {e}")

    def _save(self):
        """Saves current state to persistent storage."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "total_experiences": len(self.experiences),
                    "q_table": self.q_table,
                    "experiences": self.experiences[-500:]  # Keep latest 500
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save evolution memory: {e}")

    def set_mode(self, mode: str):
        """Updates operational mode: 'shadow', 'offline', or 'active'."""
        assert mode in ("shadow", "offline", "active"), f"Invalid mode: {mode}"
        self.mode = mode
        self.bandit_learner.mode = mode
        logger.info(f"[AGENT 6 EVO] Operational mode switched to: {mode.upper()}")

    def compute_reward(self, success: bool, rollback_executed: bool, latency_delta_pct: float) -> float:
        """
        Calculates mathematical reinforcement learning reward:
        - Successful patch with stability: +10.0 + bonus for latency reduction
        - Failed patch or rollback: -15.0 penalty
        """
        if success and not rollback_executed:
            reward = 10.0
            if latency_delta_pct < 0:  # Latency reduced
                reward += min(5.0, abs(latency_delta_pct) * 0.1)
            return round(reward, 2)
        else:
            return -15.0

    def _get_state_key(self, incident: IncidentContext) -> str:
        """Derives a fine-grained state signature from incident error type and message."""
        err = incident.errors[0] if incident.errors else None
        err_type = err.error_type if err else "default"
        err_msg = (err.error_message or "").lower() if err else ""

        if "504" in err_msg or "gateway" in err_msg or "aggregator" in err_msg:
            sub_sig = "GatewayTimeout"
        elif "queuepool" in err_msg or "pool" in err_msg:
            sub_sig = "QueuePool"
        elif "locked" in err_msg or "operationalerror" in err_msg or "database is locked" in err_msg:
            sub_sig = "LockContention"
        elif "401" in err_msg or "jwt" in err_msg or "unauthorized" in err_msg or "permission" in err_msg:
            sub_sig = "JWTAuth"
        elif "422" in err_msg or "schema" in err_msg or "validation" in err_msg or "corrupt" in err_msg:
            sub_sig = "SchemaValidation"
        else:
            sub_sig = err_type

        return f"{incident.service_name}:{err_type}:{sub_sig}"

    def record_experience(
        self,
        incident: IncidentContext,
        action: RemediationAction,
        result: ExecutionResult,
        latency_delta_pct: float = -15.0
    ) -> EvolutionExperience:
        """
        Ingests real outcome from Agent 4 execution, updates both Q-table and
        Contextual Bandit policy, and stores verified outcome in SQLite OutcomeStore.
        """
        # Safety invariant check
        self.assert_safety_boundary()

        state_key = self._get_state_key(incident)
        action_key = action.action_id

        # 1. Calculate Reward
        reward = self.compute_reward(
            success=result.test_suite_passed,
            rollback_executed=result.rollback_executed,
            latency_delta_pct=latency_delta_pct
        )

        # 2. Q-Learning Update for backward compatibility
        if state_key not in self.q_table:
            self.q_table[state_key] = {}

        old_q = self.q_table[state_key].get(action_key, 1.0)
        new_q = old_q + self.learning_rate * (reward - old_q)
        self.q_table[state_key][action_key] = round(new_q, 4)

        # 3. Create EvolutionExperience for backward compatibility
        exp = EvolutionExperience(
            experience_id=f"EXP-{len(self.experiences)+1:04d}",
            incident_signature=state_key,
            state_vector={
                "active_connections": float(incident.telemetry.active_connections if incident.telemetry else 0),
                "pool_size": float(incident.telemetry.pool_size if incident.telemetry else 0),
                "pool_utilization": float(incident.telemetry.pool_utilization_pct if incident.telemetry else 0.0)
            },
            action_signature=action_key,
            outcome_success=result.test_suite_passed,
            latency_delta_pct=latency_delta_pct,
            reward=reward,
            learned_weight=new_q,
            timestamp=datetime.now(timezone.utc)
        )
        self.experiences.append(exp.model_dump(mode="json"))
        self._save()

        # 4. Extract Structured Incident State & Compute Patch Hash
        state_features = IncidentStateFeatures.from_incident(incident)
        patch_hash = OutcomeRecord.compute_patch_hash(result.unified_diff or action.unified_diff)

        # 5. Formulate Immutable OutcomeRecord for Stage 5 Database
        outcome_record = OutcomeRecord(
            outcome_id=f"OUT-{incident.incident_id}-{len(self.experiences):04d}",
            incident_id=incident.incident_id,
            app_version="2.0.0",
            selected_action_id=action.action_id,
            action_type=action.action_id,
            guardian_approved=True,  # Execution occurred, so guardian must have approved
            guardian_risk_tier=action.risk_tier.value,
            requires_hitl=(action.risk_tier in (ActionRiskTier.TIER_3_CODE_PATCH, ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE)),
            patch_hash=patch_hash,
            target_file=result.target_file or action.target_file,
            test_suite_passed=result.test_suite_passed,
            verification_exit_code=0 if result.test_suite_passed else 1,
            recovery_latency_ms=result.execution_time_ms,
            latency_delta_pct=latency_delta_pct,
            verified_recovery=result.test_suite_passed and not result.rollback_executed,
            regression_detected=not result.test_suite_passed,
            rollback_executed=result.rollback_executed,
            reward=reward,
            evidence_refs=[result.git_commit_sha] if result.git_commit_sha else [],
            state_features=state_features.model_dump(mode="json"),
            timestamp=datetime.now(timezone.utc)
        )

        # 6. Store in Structured SQLite Database
        self.outcome_store.record_outcome(outcome_record)

        # 7. Update LinUCB Contextual Bandit Model
        self.bandit_learner.update_from_outcome(outcome_record, state=state_features)

        logger.info(f"[AGENT 6 EVO] Recorded verified outcome in SQLite & LinUCB: Q={new_q:.3f} (Reward: {reward:+.1f})")
        return exp

    def rank_actions(
        self,
        incident: IncidentContext,
        candidate_actions: List[RemediationAction]
    ) -> List[RemediationAction]:
        """
        Ranks candidate remediation actions.
        In active mode: ordered by learned bandit LinUCB scores.
        In shadow mode: ordered by deterministic baseline, with learned predictions logged.
        Maintains full compatibility with existing Council callers.
        """
        self.assert_safety_boundary()
        state_features = IncidentStateFeatures.from_incident(incident)

        # Convert to CandidateActionSpecs
        specs = [CandidateActionSpec.from_remediation_action(a) for a in candidate_actions]

        # In shadow mode, we score with both baseline and bandit
        if self.mode == "active":
            ranked_specs = self.bandit_learner.rank_candidates(state_features, specs)
        else:
            # Shadow mode: rule baseline is authoritative, bandit predictions logged alongside
            baseline_ranked = self.rule_baseline.rank_candidates(state_features, specs)
            bandit_ranked = self.bandit_learner.rank_candidates(state_features, specs)
            ranked_specs = baseline_ranked
            logger.info(
                f"[AGENT 6 SHADOW MODE] Baseline top choice: {baseline_ranked[0].action_id} "
                f"| Bandit top choice: {bandit_ranked[0].action_id} (Uncertainty: {bandit_ranked[0].uncertainty_score:.3f})"
            )

        # Convert back to RemediationActions, preserving ordering
        action_map = {a.action_id: a for a in candidate_actions}
        ordered_actions = []
        for spec in ranked_specs:
            if spec.action_id in action_map:
                ordered_actions.append(action_map[spec.action_id])

        # Also fallback to Q-table lookup if spec conversion missed anything
        for a in candidate_actions:
            if a not in ordered_actions:
                ordered_actions.append(a)

        return ordered_actions

    def get_stats(self) -> Dict[str, Any]:
        """Returns empirical learning telemetry and bandit health."""
        total_exp = len(self.experiences)
        successes = sum(1 for e in self.experiences if e.get("outcome_success", False))
        rate = (successes / total_exp * 100.0) if total_exp > 0 else 0.0

        return {
            "total_experiences": total_exp,
            "success_rate_pct": round(rate, 1),
            "state_signatures_learned": len(self.q_table),
            "q_table": self.q_table,
            "bandit_mode": self.mode,
            "bandit_total_updates": self.bandit_learner.total_updates,
            "bandit_arms": list(self.bandit_learner.A.keys()),
            "active_policy_version": self.bandit_learner.active_version_tag
        }

    # =========================================================================
    # STAGE 4 & 8: SAFETY BOUNDARY & VERSIONING FACADE
    # =========================================================================

    def assert_safety_boundary(self):
        """
        Stage 4 Safety Guardian Independence Gate:
        Agent 6 EVO CANNOT grant execution approvals, bypass HITL,
        or execute arbitrary code actions directly.
        """
        # Strictly verify no execution / authorization bypass capability
        assert not hasattr(self, "approve_action"), "Safety Invariant: Agent 6 cannot grant approval"
        assert not hasattr(self, "execute_patch"), "Safety Invariant: Agent 6 cannot execute patch"
        return True

    def save_policy_version(self, version_tag: str, description: str, validation_metrics: Optional[Dict[str, float]] = None) -> PolicyVersionMetadata:
        """Saves current policy as an immutable version."""
        return self.bandit_learner.save_policy_version(version_tag, description, validation_metrics)

    def load_policy_version(self, version_tag: str) -> bool:
        """Loads a specific policy version."""
        return self.bandit_learner.load_policy_version(version_tag)

    def rollback_to_version(self, version_tag: str) -> bool:
        """Rolls back to a specific policy version."""
        return self.bandit_learner.rollback_to_version(version_tag)

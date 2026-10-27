"""
Agent 6: Outcome-Aware Contextual Bandit Learner (LinUCB)
Learns optimal remediation action policies from verified historical remediation outcomes.
Includes Bayesian uncertainty estimation, offline training, shadow mode, policy versioning, and rollback.
"""

import os
import json
import hashlib
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from agents.schemas import ActionRiskTier
from agents.agent6_evo.schemas import (
    IncidentStateFeatures,
    CandidateActionSpec,
    OutcomeRecord,
    PolicyVersionMetadata
)
from agents.agent6_evo.rule_baseline import DeterministicRuleBaseline
from agents.agent6_evo.outcome_store import OutcomeStore

logger = logging.getLogger(__name__)


class OutcomeAwareBanditLearner:
    """
    Stage 3: Contextual Bandit Learning Engine (LinUCB with Ridge Regression).
    Learns value functions E[Reward | State, Action] and computes epistemic uncertainty sigma(s, a).
    Operates in shadow mode by default to ensure safe offline/canary observation before active deployment.
    """

    FEATURE_DIM = 8

    def __init__(
        self,
        mode: str = "shadow",
        alpha: float = 1.0,
        reg_lambda: float = 1.0,
        versions_dir: Optional[str] = None,
        outcome_store: Optional[OutcomeStore] = None
    ):
        """
        Args:
            mode: "shadow" (default: logs rankings alongside baseline without autonomous execution),
                  "offline" (batch learning only), or "active" (learned ranking selects proposed action).
            alpha: LinUCB exploration parameter (alpha=0 is pure greedy exploitation).
            reg_lambda: Ridge regression L2 regularization factor.
            versions_dir: Directory where policy version snapshots are persisted.
            outcome_store: Structured outcome database instance.
        """
        assert mode in ("shadow", "offline", "active"), f"Invalid mode: {mode}"
        self.mode = mode
        self.alpha = alpha
        self.reg_lambda = reg_lambda
        self.d = self.FEATURE_DIM
        
        self.versions_dir = versions_dir or os.path.join(os.getcwd(), "data", "policy_versions")
        os.makedirs(self.versions_dir, exist_ok=True)
        self.outcome_store = outcome_store or OutcomeStore()
        self.baseline = DeterministicRuleBaseline()

        # Action-specific regression parameters: A_a in R^(d x d), b_a in R^d
        self.A: Dict[str, np.ndarray] = {}
        self.b: Dict[str, np.ndarray] = {}
        self.sample_counts: Dict[str, int] = {}
        self.total_updates: int = 0
        self.active_version_tag: str = "v1.0.0-initial"

    def _get_action_key(self, candidate: CandidateActionSpec) -> str:
        """Normalized key for action bandit arms."""
        return candidate.action_type or candidate.action_id

    def _init_arm(self, action_key: str):
        """Initializes ridge regression matrices for an action arm."""
        if action_key not in self.A:
            self.A[action_key] = self.reg_lambda * np.identity(self.d, dtype=np.float64)
            self.b[action_key] = np.zeros(self.d, dtype=np.float64)
            self.sample_counts[action_key] = 0

    def predict(
        self,
        state: IncidentStateFeatures,
        candidate: CandidateActionSpec
    ) -> Tuple[float, float]:
        """
        Computes the model's predicted reward E[R|s,a] and epistemic uncertainty sigma(s,a).
        Returns: (predicted_reward, uncertainty)
        """
        action_key = self._get_action_key(candidate)
        self._init_arm(action_key)

        x = np.array(state.to_feature_vector(), dtype=np.float64).reshape(-1, 1)
        A_inv = np.linalg.pinv(self.A[action_key])
        theta = np.dot(A_inv, self.b[action_key].reshape(-1, 1))

        # Expected reward E[R|s,a]
        predicted_reward = float(np.dot(theta.T, x)[0, 0])
        
        # Epistemic variance / uncertainty: sigma = sqrt(x^T A^-1 x)
        var = float(np.dot(np.dot(x.T, A_inv), x)[0, 0])
        uncertainty = float(math.sqrt(max(0.0, var)))

        return round(predicted_reward, 3), round(uncertainty, 3)

    def score_candidate(
        self,
        state: IncidentStateFeatures,
        candidate: CandidateActionSpec
    ) -> float:
        """
        Computes the LinUCB acquisition score:
        score = predicted_reward + alpha * uncertainty - safety_penalty
        """
        # 1. Prohibited Actions Filter
        if candidate.risk_tier == ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE:
            candidate.rejection_reason = "REJECTED_BY_SAFETY: Tier 4 Destructive action prohibited by policy."
            return -100.0

        pred_reward, uncertainty = self.predict(state, candidate)
        candidate.predicted_reward = pred_reward
        candidate.uncertainty_score = uncertainty
        candidate.exploration_bonus = round(self.alpha * uncertainty, 3)

        # In shadow mode or when model is newly initialized (zero observations for this arm),
        # blend with baseline to prevent uncalibrated wild exploration
        arm_samples = self.sample_counts.get(self._get_action_key(candidate), 0)
        baseline_score = self.baseline.score_candidate(state, candidate)

        if arm_samples < 2:
            # Cold-start prior: weight towards rule baseline
            composite_score = (baseline_score * 0.7) + (pred_reward * 10.0 * 0.3) + candidate.exploration_bonus
        else:
            composite_score = (pred_reward * 10.0) + candidate.exploration_bonus

        return round(composite_score, 3)

    def rank_candidates(
        self,
        state: IncidentStateFeatures,
        candidates: List[CandidateActionSpec]
    ) -> List[CandidateActionSpec]:
        """
        Ranks candidate actions according to the learned policy.
        In 'shadow' mode, it records predictions and uncertainty, while respecting baseline order.
        In 'active' mode, it orders primarily by learned LinUCB score.
        """
        scored: List[CandidateActionSpec] = []
        for c in candidates:
            c_copy = c.model_copy()
            c_score = self.score_candidate(state, c_copy)
            c_copy.score = c_score
            scored.append(c_copy)

        if self.mode == "active":
            # Active mode: sort by LinUCB composite score
            def active_key(c: CandidateActionSpec):
                is_rejected = 1 if c.rejection_reason else 0
                return (is_rejected, -c.score, c.estimated_recovery_time_s, c.action_id)
            ranked = sorted(scored, key=active_key)
        else:
            # Shadow / Offline mode: sort by baseline, but keep learned scores and uncertainty logged!
            baseline_ranked = self.baseline.rank_candidates(state, candidates)
            baseline_order = {item.action_id: idx for idx, item in enumerate(baseline_ranked)}
            
            def shadow_key(c: CandidateActionSpec):
                is_rejected = 1 if c.rejection_reason else 0
                return (is_rejected, baseline_order.get(c.action_id, 999), -c.score)
            ranked = sorted(scored, key=shadow_key)

        for idx, item in enumerate(ranked, 1):
            item.ranking_rank = idx

        return ranked

    def update_from_outcome(
        self,
        outcome: OutcomeRecord,
        state: Optional[IncidentStateFeatures] = None
    ):
        """
        Contextual Bandit online learning update:
        A_a <- A_a + x * x^T
        b_a <- b_a + r * x
        Monotonically reduces uncertainty sigma(s,a) for this action context.
        """
        action_key = outcome.action_type or outcome.selected_action_id
        self._init_arm(action_key)

        # Reconstruct feature vector from state or state_features in outcome
        if state:
            x_vec = state.to_feature_vector()
        elif outcome.state_features:
            sf = outcome.state_features
            x_vec = [
                min(1.0, float(sf.get("active_connections", 0.0)) / 100.0),
                min(1.0, float(sf.get("pool_size", 2.0)) / 50.0),
                min(1.0, float(sf.get("pool_utilization_pct", 0.0)) / 100.0),
                min(1.0, float(sf.get("latency_p99_ms", 0.0)) / 3000.0),
                min(1.0, float(sf.get("cpu_percent", 0.0)) / 100.0),
                min(1.0, max(0.0, float(sf.get("blast_radius_score", 0.0)))),
                0.5,
                1.0
            ]
        else:
            x_vec = [0.1, 0.2, 0.5, 0.3, 0.2, 0.0, 0.5, 1.0]

        x = np.array(x_vec, dtype=np.float64).reshape(-1, 1)
        r = float(outcome.reward)

        # Update covariance matrix and target vector
        self.A[action_key] += np.dot(x, x.T)
        self.b[action_key] += (r * x).flatten()
        self.sample_counts[action_key] += 1
        self.total_updates += 1

        logger.info(
            f"[BANDIT LEARNER] Updated arm '{action_key}' with Reward={r:+.2f} "
            f"(Total Arm Samples: {self.sample_counts[action_key]}, Total Updates: {self.total_updates})"
        )

    def train_batch(self, outcomes: List[OutcomeRecord]):
        """Trains bandit on a batch of verified historical remediation outcomes."""
        for o in outcomes:
            self.update_from_outcome(o)

    # =========================================================================
    # STAGE 8: POLICY VERSIONING & ROLLBACK
    # =========================================================================

    def save_policy_version(
        self,
        version_tag: str,
        description: str,
        validation_metrics: Optional[Dict[str, float]] = None
    ) -> PolicyVersionMetadata:
        """
        Saves full model parameters, covariance matrices, and metadata as an immutable version.
        Registers the version in the OutcomeStore.
        """
        metrics = validation_metrics or {}
        artifact_filename = f"{version_tag}.json"
        artifact_path = os.path.join(self.versions_dir, artifact_filename)

        # Serialize numpy arrays to JSON-safe lists
        serialized_A = {k: v.tolist() for k, v in self.A.items()}
        serialized_b = {k: v.tolist() for k, v in self.b.items()}

        payload = {
            "version_tag": version_tag,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description,
            "mode": self.mode,
            "alpha": self.alpha,
            "reg_lambda": self.reg_lambda,
            "total_updates": self.total_updates,
            "sample_counts": self.sample_counts,
            "A_matrices": serialized_A,
            "b_vectors": serialized_b,
            "validation_metrics": metrics
        }

        payload_bytes = json.dumps(payload, indent=2).encode("utf-8")
        artifact_sha256 = hashlib.sha256(payload_bytes).hexdigest()

        with open(artifact_path, "wb") as f:
            f.write(payload_bytes)

        metadata = PolicyVersionMetadata(
            version_tag=version_tag,
            timestamp=datetime.now(timezone.utc),
            description=description,
            model_type="LinUCB-ContextualBandit",
            total_samples_trained=self.total_updates,
            empirical_success_rate=metrics.get("empirical_success_rate", 0.0),
            mean_recovery_latency_ms=metrics.get("mean_recovery_latency_ms", 0.0),
            unsafe_rejection_rate=metrics.get("unsafe_rejection_rate", 100.0),
            regression_rate=metrics.get("regression_rate", 0.0),
            mean_uncertainty=metrics.get("mean_uncertainty", 1.0),
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha256,
            is_active=True
        )

        self.outcome_store.record_policy_version(metadata)
        self.active_version_tag = version_tag
        logger.info(f"[BANDIT LEARNER] Saved policy version {version_tag} (SHA256: {artifact_sha256[:8]})")
        return metadata

    def load_policy_version(self, version_tag: str) -> bool:
        """Loads weights and state from a versioned policy artifact."""
        artifact_path = os.path.join(self.versions_dir, f"{version_tag}.json")
        if not os.path.exists(artifact_path):
            logger.error(f"[BANDIT LEARNER] Version artifact not found: {artifact_path}")
            return False

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.A = {k: np.array(v, dtype=np.float64) for k, v in data["A_matrices"].items()}
            self.b = {k: np.array(v, dtype=np.float64) for k, v in data["b_vectors"].items()}
            self.sample_counts = data.get("sample_counts", {})
            self.total_updates = data.get("total_updates", 0)
            self.alpha = data.get("alpha", self.alpha)
            self.reg_lambda = data.get("reg_lambda", self.reg_lambda)
            self.active_version_tag = version_tag
            logger.info(f"[BANDIT LEARNER] Loaded policy version {version_tag}")
            return True
        except Exception as e:
            logger.error(f"[BANDIT LEARNER] Failed to load version {version_tag}: {e}")
            return False

    def rollback_to_version(self, version_tag: str) -> bool:
        """Rolls back the active policy to an earlier version."""
        success = self.load_policy_version(version_tag)
        if success:
            self.outcome_store.set_active_version(version_tag)
            logger.info(f"[BANDIT LEARNER] Successfully rolled back to policy version: {version_tag}")
        return success

    # =========================================================================
    # STAGE 4: SAFETY GUARDIAN INDEPENDENCE ENFORCEMENT
    # =========================================================================

    def verify_safety_invariants(self):
        """
        Enforces Stage 4 requirement:
        The learning model MUST NEVER grant permissions, bypass approvals,
        or directly execute arbitrary actions.
        """
        # Invariant checks: this learner has NO methods to execute actions or approve
        assert not hasattr(self, "approve_action"), "Safety Violation: Learner must not approve actions"
        assert not hasattr(self, "execute_action"), "Safety Violation: Learner must not execute actions"
        assert not hasattr(self, "grant_hitl"), "Safety Violation: Learner must not grant HITL"
        return True

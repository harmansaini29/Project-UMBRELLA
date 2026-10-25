"""
Agent 6 Component: Evolution Policy Engine (Q-Learning / Contextual Bandit)
Updates empirical value estimates Q(s, a) from post-remediation system outcomes.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
logger = logging.getLogger(__name__)

from agents.schemas import (
    EvolutionExperience,
    ExecutionResult,
    RemediationAction,
    IncidentContext
)


class EvolutionPolicyEngine:
    """
    Agent 6 RL Core: Tracks system evolution memory and updates action policy weights.
    """

    def __init__(self, storage_path: Optional[str] = None, learning_rate: float = 0.25):
        self.storage_path = storage_path or os.path.join(os.getcwd(), "data", "evolution_memory.json")
        self.learning_rate = learning_rate
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

    def record_experience(
        self,
        incident: IncidentContext,
        action: RemediationAction,
        result: ExecutionResult,
        latency_delta_pct: float = -15.0
    ) -> EvolutionExperience:
        """
        Ingests real outcome from Agent 4 execution and updates the RL policy.
        """
        state_key = f"{incident.service_name}:{incident.errors[0].error_type if incident.errors else 'default'}"
        action_key = action.action_id

        # Calculate reward
        reward = self.compute_reward(
            success=result.test_suite_passed,
            rollback_executed=result.rollback_executed,
            latency_delta_pct=latency_delta_pct
        )

        # Contextual Bandit / Q-learning Update:
        # Q(s, a) <- Q(s, a) + alpha * [R - Q(s, a)]
        if state_key not in self.q_table:
            self.q_table[state_key] = {}

        old_q = self.q_table[state_key].get(action_key, 1.0)
        new_q = old_q + self.learning_rate * (reward - old_q)
        self.q_table[state_key][action_key] = round(new_q, 4)

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
        logger.info(f"[AGENT 6 EVO] Learned update for {state_key} -> {action_key}: Q={new_q:.3f} (Reward: {reward})")

        return exp

    def rank_actions(self, incident: IncidentContext, candidate_actions: List[RemediationAction]) -> List[RemediationAction]:
        """
        Ranks candidate remediation actions based on learned historical Q-values.
        """
        state_key = f"{incident.service_name}:{incident.errors[0].error_type if incident.errors else 'default'}"
        state_scores = self.q_table.get(state_key, {})

        def score_action(action: RemediationAction) -> float:
            return state_scores.get(action.action_id, 0.0)

        return sorted(candidate_actions, key=score_action, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Returns empirical learning telemetry."""
        total_exp = len(self.experiences)
        successes = sum(1 for e in self.experiences if e.get("outcome_success", False))
        rate = (successes / total_exp * 100.0) if total_exp > 0 else 0.0

        return {
            "total_experiences": total_exp,
            "success_rate_pct": round(rate, 1),
            "state_signatures_learned": len(self.q_table),
            "q_table": self.q_table
        }

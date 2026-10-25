"""
Agent 5: Leader Governor / Safety Guardian & Supervisor
Guarantees deterministic execution safety policies, HITL gates,
and autonomous failover redundancy if any council agent encounters faults.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
import logging
logger = logging.getLogger(__name__)

from agents.schemas import (
    GuardianDecision,
    ActionRiskTier,
    RemediationPlan,
    RemediationAction,
    BlastRadiusReport,
    AgentHealthStatus
)


class SafetyGuardian:
    """
    Agent 5 in the UMBRELLA Council.
    Acts as the authoritative safety governor and resilient failover supervisor.
    """

    def __init__(self):
        self.agent_registry: Dict[str, AgentHealthStatus] = {
            "agent_1_rca": AgentHealthStatus(agent_id="agent_1_rca", agent_name="Root Cause Analyzer"),
            "agent_2_topology": AgentHealthStatus(agent_id="agent_2_topology", agent_name="3D Topology Visualizer"),
            "agent_3_planner": AgentHealthStatus(agent_id="agent_3_planner", agent_name="Remediation Planner"),
            "agent_4_executor": AgentHealthStatus(agent_id="agent_4_executor", agent_name="Sandboxed Executor"),
            "agent_6_evo": AgentHealthStatus(agent_id="agent_6_evo", agent_name="Backend Evolution Agent")
        }
        self.failover_active: Dict[str, bool] = {}

    def record_heartbeat(self, agent_id: str):
        """Records healthy heartbeat from an agent."""
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id].heartbeat_ts = datetime.now(timezone.utc)
            self.agent_registry[agent_id].is_alive = True
            self.agent_registry[agent_id].is_failing_over = False

    def report_agent_failure(self, agent_id: str, error_msg: str):
        """Registers an agent failure and triggers failover surrogate."""
        logger.warning(f"[AGENT 5 GUARDIAN] Failure detected in {agent_id}: {error_msg}. Activating failover surrogate.")
        if agent_id in self.agent_registry:
            self.agent_registry[agent_id].is_alive = False
            self.agent_registry[agent_id].is_failing_over = True
            self.failover_active[agent_id] = True

    def execute_with_failover(self, agent_id: str, primary_func: Callable, fallback_func: Callable, *args, **kwargs) -> Any:
        """
        Executes an agent task. If primary agent fails or is dead, Agent 5 steps in
        and executes the fallback surrogate function to keep the pipeline alive.
        """
        try:
            self.record_heartbeat(agent_id)
            result = primary_func(*args, **kwargs)
            return result
        except Exception as e:
            self.report_agent_failure(agent_id, str(e))
            logger.info(f"[AGENT 5 GUARDIAN] Acting as surrogate for {agent_id}...")
            # Execute surrogate fallback
            fallback_result = fallback_func(*args, **kwargs)
            return fallback_result

    def evaluate_risk(
        self,
        plan: RemediationPlan,
        blast: BlastRadiusReport,
        human_approval_granted: bool = False
    ) -> GuardianDecision:
        """
        Evaluates risk tier and decides whether execution is authorized.
        """
        highest_risk = ActionRiskTier.TIER_1_SAFE_READONLY
        for action in plan.actions:
            if action.risk_tier == ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE:
                highest_risk = ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE
                break
            elif action.risk_tier == ActionRiskTier.TIER_3_CODE_PATCH:
                highest_risk = ActionRiskTier.TIER_3_CODE_PATCH
            elif action.risk_tier == ActionRiskTier.TIER_2_CONFIG_RESTART and highest_risk != ActionRiskTier.TIER_3_CODE_PATCH:
                highest_risk = ActionRiskTier.TIER_2_CONFIG_RESTART

        # Rule 1: Tier 4 Destructive is BLOCKED by default
        if highest_risk == ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE:
            return GuardianDecision(
                incident_id=plan.incident_id,
                approved=False,
                risk_tier=highest_risk,
                requires_hitl=True,
                reason="BLOCKED: Tier 4 Schema Destructive actions are prohibited from autonomous execution."
            )

        # Rule 2: Tier 3 Code Patch ALWAYS requires Human Approval Gate
        if highest_risk == ActionRiskTier.TIER_3_CODE_PATCH:
            if not human_approval_granted:
                return GuardianDecision(
                    incident_id=plan.incident_id,
                    approved=False,
                    risk_tier=highest_risk,
                    requires_hitl=True,
                    reason="APPROVAL REQUIRED: Tier 3 Code Patches require explicit Human-in-the-Loop authorization."
                )
            else:
                return GuardianDecision(
                    incident_id=plan.incident_id,
                    approved=True,
                    risk_tier=highest_risk,
                    requires_hitl=False,
                    reason="APPROVED: Human-in-the-Loop review confirmed code diff execution."
                )

        # Rule 3: Tier 2 Config Restart (Auto-approve if blast radius < 40%, otherwise HITL)
        if highest_risk == ActionRiskTier.TIER_2_CONFIG_RESTART:
            # If user already granted approval or blast radius is bounded
            if human_approval_granted or blast.blast_radius_score <= 0.40:
                return GuardianDecision(
                    incident_id=plan.incident_id,
                    approved=True,
                    risk_tier=highest_risk,
                    requires_hitl=False,
                    reason=f"APPROVED: Tier 2 Config restart authorized (Blast radius: {blast.blast_radius_score*100:.1f}%)."
                )
            else:
                return GuardianDecision(
                    incident_id=plan.incident_id,
                    approved=False,
                    risk_tier=highest_risk,
                    requires_hitl=True,
                    reason=f"APPROVAL REQUIRED: Elevated blast radius ({blast.blast_radius_score*100:.1f}%) requires human sign-off."
                )

        # Rule 4: Tier 1 Safe Readonly
        return GuardianDecision(
            incident_id=plan.incident_id,
            approved=True,
            risk_tier=highest_risk,
            requires_hitl=False,
            reason="APPROVED: Tier 1 Safe read-only inspection."
        )

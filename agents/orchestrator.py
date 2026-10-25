"""
Project UMBRELLA: Central Multi-Agent Council Orchestrator
Coordinates Agent 1 (RCA), Agent 2 (Topology), Agent 3 (Planner),
Agent 4 (Executor), Agent 5 (Guardian), and Agent 6 (EVO) in a closed self-healing loop.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
logger = logging.getLogger(__name__)

from agents.schemas import (
    IncidentContext,
    RCAResult,
    BlastRadiusReport,
    RemediationPlan,
    ExecutionResult,
    GuardianDecision,
    EvolutionExperience,
    ProactiveRefactorProposal
)
from agents.agent1_rca.analyzer import RootCauseAnalyzer
from agents.agent2_topology.visualizer import TopologyVisualizer
from agents.agent3_planner.planner import RemediationPlanner
from agents.agent4_executor.executor import SandboxedExecutor
from agents.agent5_guardian.guardian import SafetyGuardian
from agents.agent6_evo.policy_learner import EvolutionPolicyEngine
from agents.agent6_evo.proactive_optimizer import ProactiveBackendOptimizer


class CouncilOrchestrator:
    """
    Intelligent Orchestrator for the 6-Agent Council.
    """

    def __init__(self, rag_engine=None):
        self.agent1_rca = RootCauseAnalyzer(rag_engine=rag_engine)
        self.agent2_topology = TopologyVisualizer()
        self.agent3_planner = RemediationPlanner(rag_engine=rag_engine)
        self.agent4_executor = SandboxedExecutor()
        self.agent5_guardian = SafetyGuardian()
        self.agent6_policy = EvolutionPolicyEngine()
        self.agent6_optimizer = ProactiveBackendOptimizer(policy_engine=self.agent6_policy)

    def run_self_healing_pipeline(
        self,
        incident: IncidentContext,
        grant_hitl_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Executes end-to-end self-healing pipeline across the 6 specialist agents.
        """
        logger.info(f"========== INITIATING UMBRELLA COUNCIL FOR INCIDENT {incident.incident_id} ==========")

        # Step 1: Agent 1 - Root Cause Diagnosis
        logger.info("[AGENT 1] Executing 4-Signal AST and RAG Diagnostic Analysis...")
        rca_result: RCAResult = self.agent5_guardian.execute_with_failover(
            agent_id="agent_1_rca",
            primary_func=self.agent1_rca.diagnose,
            fallback_func=lambda inc: self.agent1_rca.diagnose(inc),
            incident=incident
        )
        logger.info(f"[AGENT 1] Diagnosis complete: {rca_result.primary_causes[0].cause} (Confidence: {rca_result.overall_confidence:.1%})")

        # Step 2: Agent 2 - 3D Spatial Topology & Blast Radius
        logger.info("[AGENT 2] Mapping failure onto 3D Spatial Topology...")
        blast_report, topology_snapshot = self.agent5_guardian.execute_with_failover(
            agent_id="agent_2_topology",
            primary_func=self.agent2_topology.update_from_rca,
            fallback_func=lambda r: self.agent2_topology.update_from_rca(r),
            rca=rca_result
        )
        logger.info(f"[AGENT 2] Blast radius computed: {blast_report.blast_radius_score * 100:.1f}% ({len(blast_report.impacted_node_ids)} downstream nodes)")

        # Step 3: Agent 3 - Remediation Planning & Cheat Sheet
        logger.info("[AGENT 3] Generating unified diff patch, rollback plan, and operator cheat sheet...")
        remediation_plan: RemediationPlan = self.agent5_guardian.execute_with_failover(
            agent_id="agent_3_planner",
            primary_func=self.agent3_planner.plan,
            fallback_func=lambda r, b: self.agent3_planner.plan(r, b),
            rca=rca_result,
            blast_report=blast_report
        )
        logger.info(f"[AGENT 3] Remediation plan formulated: Action {remediation_plan.actions[0].action_id} (Risk: {remediation_plan.actions[0].risk_tier.value})")

        # Step 4: Agent 5 - Safety Guardian & Risk Policy Gate
        logger.info("[AGENT 5] Evaluating Risk Policy & Human-in-the-Loop authorization...")
        guardian_decision: GuardianDecision = self.agent5_guardian.evaluate_risk(
            plan=remediation_plan,
            blast=blast_report,
            human_approval_granted=grant_hitl_approval
        )
        logger.info(f"[AGENT 5] Guardian decision: Approved={guardian_decision.approved} ({guardian_decision.reason})")

        # Step 5: Agent 4 - Sandboxed Execution & Post-Remediation Verification
        execution_result: Optional[ExecutionResult] = None
        if guardian_decision.approved:
            logger.info("[AGENT 4] Executing sandboxed patch application & stability verification...")
            execution_result = self.agent5_guardian.execute_with_failover(
                agent_id="agent_4_executor",
                primary_func=self.agent4_executor.execute_action,
                fallback_func=lambda a, inc_id, appr: self.agent4_executor.execute_action(a, inc_id, appr),
                action=remediation_plan.actions[0],
                incident_id=incident.incident_id,
                is_guardian_approved=guardian_decision.approved
            )
            logger.info(f"[AGENT 4] Execution complete: Status={execution_result.status.value} (Suite passed: {execution_result.test_suite_passed})")
        else:
            logger.warning("[AGENT 4] Execution bypassed: Guardian did not grant authorization.")

        # Step 6: Agent 6 - UMBRELLA-EVO Self-Learning & Backend Evolution
        evolution_exp: Optional[EvolutionExperience] = None
        proactive_proposal: Optional[ProactiveRefactorProposal] = None

        if execution_result:
            logger.info("[AGENT 6 EVO] Ingesting healing outcome into Reinforcement Learning policy memory...")
            evolution_exp = self.agent6_policy.record_experience(
                incident=incident,
                action=remediation_plan.actions[0],
                result=execution_result,
                latency_delta_pct=-25.0 if execution_result.test_suite_passed else 0.0
            )

            # Evaluate proactive refactoring opportunity
            logger.info("[AGENT 6 EVO] Evaluating overall backend system for proactive refactoring...")
            proactive_proposal = self.agent6_optimizer.evaluate_and_propose()

        logger.info("========== UMBRELLA COUNCIL PIPELINE COMPLETED ==========")

        return {
            "incident_id": incident.incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_1_rca": rca_result.model_dump(mode="json"),
            "agent_2_topology": {
                "blast_report": blast_report.model_dump(mode="json"),
                "topology_snapshot": topology_snapshot
            },
            "agent_3_planner": remediation_plan.model_dump(mode="json"),
            "agent_5_guardian": guardian_decision.model_dump(mode="json"),
            "agent_4_executor": execution_result.model_dump(mode="json") if execution_result else None,
            "agent_6_evo": {
                "evolution_experience": evolution_exp.model_dump(mode="json") if evolution_exp else None,
                "learning_stats": self.agent6_policy.get_stats(),
                "proactive_proposal": proactive_proposal.model_dump(mode="json") if proactive_proposal else None
            }
        }

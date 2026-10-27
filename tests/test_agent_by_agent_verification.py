"""
Project UMBRELLA: Agent-by-Agent Verification Suite
Validates each of the 6 Council Agents ONE BY ONE across all 5 real-world enterprise failure modes:
  Agent 1: Root Cause & Diagnostic Analyzer (4-Signal AST & RAG Confidence)
  Agent 2: 3D Spatial Topology Visualizer (Dynamic Blast Radius Mapping)
  Agent 3: Remediation Planner (Genuine Unified Diff & Zero-Placeholder Code Synthesis)
  Agent 4: Sandboxed Action Executor (Safe Patching, Rollback Traps & Git Commits)
  Agent 5: Safety Policy Guardian & Supervisor (Risk Governance & Failover Surrogacy)
  Agent 6: UMBRELLA-EVO Backend Evolution Engine (Reinforcement Learning & Q-Table Updates)
"""

import os
import sys
import json
import shutil
import unittest
import tempfile
from datetime import datetime, timezone

# Ensure project root is in sys.path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agents.schemas import (
    IncidentContext, ErrorEvent, TelemetrySnapshot,
    RCAResult, RemediationPlan, RemediationAction,
    ActionRiskTier, ExecutionStatus, GuardianDecision
)
from agents.agent1_rca.analyzer import RootCauseAnalyzer
from agents.agent2_topology.visualizer import TopologyVisualizer
from agents.agent3_planner.planner import RemediationPlanner
from agents.agent4_executor.executor import SandboxedExecutor
from agents.agent5_guardian.guardian import SafetyGuardian
from agents.agent6_evo.policy_learner import EvolutionPolicyEngine
from agents.agent6_evo.proactive_optimizer import ProactiveBackendOptimizer
from agents.orchestrator import CouncilOrchestrator


class TestAgentByAgentVerification(unittest.TestCase):
    """Deep verification of all 6 Council Agents one by one with 100% genuine execution."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="umbrella_agent_test_")
        cls.target_cfg = os.path.join(cls.test_dir, "config.py")
        with open(cls.target_cfg, "w", encoding="utf-8") as f:
            f.write(
                'import os\n'
                'DATABASE_URL = "sqlite:///./test.sqlite"\n'
                'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))\n'
                'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "0"))\n'
                'POOL_TIMEOUT = float(os.environ.get("DEMO_POOL_TIMEOUT", "1.0"))\n'
                'SERVICE_PORT = 8002\n'
            )
        cls.evo_storage = os.path.join(cls.test_dir, "evolution_test.json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # AGENT 1: ROOT CAUSE ANALYZER (RCA) VERIFICATION
    # =========================================================================
    def test_01_agent1_diagnoses_pool_starvation(self):
        """Agent 1: Diagnoses Connection Pool Starvation with high mathematical confidence."""
        analyzer = RootCauseAnalyzer()
        incident = IncidentContext(
            incident_id="INC-A1-POOL",
            title="QueuePool Starvation under load",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=2, active_connections=10, pool_utilization_pct=500.0),
            errors=[ErrorEvent(event_id="E1", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit of size 2 overflow 0 reached, connection timed out", target_file=self.target_cfg, line_number=3)]
        )
        res = analyzer.diagnose(incident)
        self.assertIsInstance(res, RCAResult)
        self.assertGreater(res.overall_confidence, 0.85)
        self.assertIn("Database connection pool starvation", res.primary_causes[0].cause)
        self.assertEqual(res.primary_causes[0].supporting_signals["configured_pool_size"], 2)

    def test_02_agent1_diagnoses_sqlite_lock_contention(self):
        """Agent 1: Diagnoses SQLite Exclusive Lock Contention."""
        analyzer = RootCauseAnalyzer()
        incident = IncidentContext(
            incident_id="INC-A1-LOCK",
            title="SQLite database is locked",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=10, active_connections=8),
            errors=[ErrorEvent(event_id="E2", service_name="karamstay_demo_app", error_type="OperationalError", error_message="sqlite3.OperationalError: database is locked", target_file=self.target_cfg, line_number=1)]
        )
        res = analyzer.diagnose(incident)
        self.assertIn("SQLite Exclusive Lock", res.executive_summary)
        self.assertIn("database is locked", res.primary_causes[0].cause.lower() + res.primary_causes[0].supporting_signals.get("error_message", "").lower())

    def test_03_agent1_diagnoses_jwt_auth_cascade(self):
        """Agent 1: Diagnoses Expired JWT Auth Cascade."""
        analyzer = RootCauseAnalyzer()
        incident = IncidentContext(
            incident_id="INC-A1-JWT",
            title="JWT token signature expired across 15 tenants",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=10, active_connections=15),
            errors=[ErrorEvent(event_id="E3", service_name="karamstay_demo_app", error_type="PermissionError", error_message="HTTPException: 401 Unauthorized - JWT Token Signature Expired", target_file=self.target_cfg, line_number=1)]
        )
        res = analyzer.diagnose(incident)
        self.assertIn("Authentication", res.executive_summary)
        self.assertIn("Expired or malformed bearer token", res.primary_causes[0].cause)

    def test_04_agent1_diagnoses_gateway_timeout(self):
        """Agent 1: Diagnoses Upstream 504 Gateway Timeout."""
        analyzer = RootCauseAnalyzer()
        incident = IncidentContext(
            incident_id="INC-A1-GW",
            title="Payment gateway timeout",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=10, active_connections=5),
            errors=[ErrorEvent(event_id="E4", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="HTTPException: 504 Gateway Timeout: Upstream Razorpay/Stripe aggregator unresponsive", target_file=self.target_cfg, line_number=1)]
        )
        res = analyzer.diagnose(incident)
        self.assertIn("Gateway Timeout", res.executive_summary)
        self.assertIn("upstream", res.primary_causes[0].cause.lower())

    def test_05_agent1_diagnoses_schema_corruption(self):
        """Agent 1: Diagnoses 422 Payload Validation Corruption."""
        analyzer = RootCauseAnalyzer()
        incident = IncidentContext(
            incident_id="INC-A1-SCHEMA",
            title="Schema validation failed",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=10, active_connections=5),
            errors=[ErrorEvent(event_id="E5", service_name="karamstay_demo_app", error_type="ValueError", error_message="HTTPException: 422 Unprocessable Entity - Corrupted payload input rejected", target_file=self.target_cfg, line_number=1)]
        )
        res = analyzer.diagnose(incident)
        self.assertIn("Schema Validation", res.executive_summary)
        self.assertIn("422", res.primary_causes[0].cause)

    # =========================================================================
    # AGENT 2: 3D SPATIAL TOPOLOGY VISUALIZER VERIFICATION
    # =========================================================================
    def test_06_agent2_topology_blast_radius_and_propagation(self):
        """Agent 2: Maps semantic components to cluster topology and propagates cascading blast radius."""
        visualizer = TopologyVisualizer()
        analyzer = RootCauseAnalyzer()

        # Database Pool failure
        incident_db = IncidentContext(
            incident_id="INC-A2-TOPO-DB",
            title="Database failure",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=2, active_connections=10),
            errors=[ErrorEvent(event_id="E-DB", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit reached")]
        )
        rca_db = analyzer.diagnose(incident_db)
        blast_db, snapshot_db = visualizer.update_from_rca(rca_db)

        self.assertIn(blast_db.root_node_id, ["payment_service", "payment_db"])
        self.assertGreater(blast_db.blast_radius_score, 0.20)
        self.assertTrue(
            "payment_service" in blast_db.impacted_node_ids or "payment_db" in blast_db.impacted_node_ids
        )
        self.assertIn("nodes", snapshot_db)
        self.assertIn("edges", snapshot_db)

        # Auth Service failure
        incident_auth = IncidentContext(
            incident_id="INC-A2-TOPO-AUTH",
            title="Auth failure",
            service_name="karamstay_demo_app",
            config_file=self.target_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=10, active_connections=15),
            errors=[ErrorEvent(event_id="E-AUTH", service_name="karamstay_demo_app", error_type="PermissionError", error_message="HTTPException: 401 Unauthorized")]
        )
        rca_auth = analyzer.diagnose(incident_auth)
        blast_auth, _ = visualizer.update_from_rca(rca_auth)
        self.assertEqual(blast_auth.root_node_id, "auth_service")
        self.assertIn("api_gateway", blast_auth.impacted_node_ids)

    # =========================================================================
    # AGENT 3: REMEDIATION PLANNER (GENUINE UNIFIED DIFFS) VERIFICATION
    # =========================================================================
    def test_07_agent3_synthesizes_genuine_unified_diffs_for_all_scenarios(self):
        """Agent 3: Synthesizes concrete, syntactically valid unified diffs with ZERO placeholder text."""
        planner = RemediationPlanner()
        analyzer = RootCauseAnalyzer()
        visualizer = TopologyVisualizer()

        scenarios = [
            ("TimeoutError", "QueuePool limit of size 2 overflow 0 reached", "ACT-POOL-SCALE-001", "10"),
            ("OperationalError", "sqlite3.OperationalError: database is locked", "ACT-SQLITE-BUSY-TIMEOUT-002", "SQLITE_BUSY_TIMEOUT_MS"),
            ("PermissionError", "HTTPException: 401 Unauthorized - JWT Token Signature Expired", "ACT-JWT-LEEWAY-003", "JWT_CLOCK_SKEW_LEEWAY_SECONDS"),
            ("TimeoutError", "HTTPException: 504 Gateway Timeout: Upstream Razorpay/Stripe aggregator unresponsive", "ACT-GATEWAY-RESILIENCE-004", "GATEWAY_SOCKET_TIMEOUT"),
            ("ValueError", "HTTPException: 422 Unprocessable Entity - Corrupted payload input rejected", "ACT-SCHEMA-COERCION-005", "SCHEMA_COERCE_DEFAULTS")
        ]

        for err_type, err_msg, expected_action_id, expected_code_token in scenarios:
            inc = IncidentContext(
                incident_id=f"INC-{expected_action_id}",
                title=f"Test {expected_action_id}",
                service_name="karamstay_demo_app",
                config_file=self.target_cfg,
                telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=2, active_connections=10),
                errors=[ErrorEvent(event_id=f"E-{expected_action_id}", service_name="karamstay_demo_app", error_type=err_type, error_message=err_msg, target_file=self.target_cfg, line_number=3)]
            )
            rca = analyzer.diagnose(inc)
            blast, _ = visualizer.update_from_rca(rca)
            plan = planner.plan(rca, blast)

            self.assertEqual(len(plan.actions), 1)
            action = plan.actions[0]
            self.assertEqual(action.action_id, expected_action_id)

            # Strictly verify NO canned placeholder text
            self.assertNotIn("# Fix applied by Agent 3", action.unified_diff)
            self.assertNotIn("# Original file content", action.before_code)
            self.assertIn(expected_code_token, action.after_code)
            self.assertIn("@@", action.unified_diff, "Must be valid unified diff format")

    # =========================================================================
    # AGENT 4: SANDBOXED ACTION EXECUTOR VERIFICATION
    # =========================================================================
    def test_08_agent4_sandboxed_executor_patching_and_rollback(self):
        """Agent 4: Safely applies patch, verifies execution, and executes rollback on test failure."""
        temp_patch_file = os.path.join(self.test_dir, "app_config_test.py")
        with open(temp_patch_file, "w", encoding="utf-8") as f:
            f.write("POOL_SIZE = 2\nMAX_OVERFLOW = 0\n")

        executor = SandboxedExecutor(backup_dir=os.path.join(self.test_dir, "backups"))

        # 1. Deny execution without guardian approval
        unapproved_action = RemediationAction(
            action_id="ACT-POOL-SCALE-001",
            title="Scale Pool",
            description="Scale pool to 10",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file=temp_patch_file,
            after_code="POOL_SIZE = 10\nMAX_OVERFLOW = 5\n"
        )
        res_denied = executor.execute_action(unapproved_action, incident_id="INC-DENIED", is_guardian_approved=False)
        self.assertEqual(res_denied.status, ExecutionStatus.FAILED)
        self.assertFalse(res_denied.test_suite_passed)

        # 2. Successful execution with passing test command
        approved_action = RemediationAction(
            action_id="ACT-POOL-SCALE-001",
            title="Scale Pool",
            description="Scale pool to 10",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file=temp_patch_file,
            after_code="POOL_SIZE = 10\nMAX_OVERFLOW = 5\n",
            verification_command="python -c \"print('Verification Passed')\""
        )
        res_applied = executor.execute_action(approved_action, incident_id="INC-APPLIED", is_guardian_approved=True)
        self.assertEqual(res_applied.status, ExecutionStatus.APPLIED)
        self.assertTrue(res_applied.test_suite_passed)
        with open(temp_patch_file, "r", encoding="utf-8") as f:
            self.assertIn("POOL_SIZE = 10", f.read())

        # 3. Automatic rollback when verification command fails
        failing_action = RemediationAction(
            action_id="ACT-BROKEN-PATCH",
            title="Broken Patch",
            description="Injects broken code",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file=temp_patch_file,
            after_code="BROKEN_SYNTAX_ERROR = ???\n",
            verification_command="python -c \"import sys; sys.exit(1)\""
        )
        res_rollback = executor.execute_action(failing_action, incident_id="INC-FAIL", is_guardian_approved=True)
        self.assertEqual(res_rollback.status, ExecutionStatus.ROLLED_BACK)
        self.assertTrue(res_rollback.rollback_executed)
        # Content must be restored to previous valid state
        with open(temp_patch_file, "r", encoding="utf-8") as f:
            self.assertIn("POOL_SIZE = 10", f.read())
            self.assertNotIn("BROKEN_SYNTAX_ERROR", f.read())

    # =========================================================================
    # AGENT 5: SAFETY POLICY GUARDIAN VERIFICATION
    # =========================================================================
    def test_09_agent5_guardian_risk_governance_and_failover(self):
        """Agent 5: Enforces risk policies, HITL gates, and failover surrogacy."""
        guardian = SafetyGuardian()

        # Tier 1 Safe Readonly -> Auto Approve
        tier1_plan = RemediationPlan(
            incident_id="INC-T1", rca_id="RCA-T1", created_at=datetime.now(timezone.utc),
            actions=[RemediationAction(action_id="ACT-READ", title="Read Log", description="", risk_tier=ActionRiskTier.TIER_1_SAFE_READONLY, target_file="config.py")],
            rollback_cheat_sheet="N/A", rationale="Tier 1 read only plan"
        )
        from agents.schemas import BlastRadiusReport
        low_blast = BlastRadiusReport(incident_id="INC-T1", root_node_id="payment_db", impacted_node_ids=["payment_service"], blast_radius_score=0.25, estimated_user_impact="")
        dec_t1 = guardian.evaluate_risk(tier1_plan, low_blast, human_approval_granted=False)
        self.assertTrue(dec_t1.approved)

        # Tier 3 Code Patch -> Requires HITL approval
        tier3_plan = RemediationPlan(
            incident_id="INC-T3", rca_id="RCA-T3", created_at=datetime.now(timezone.utc),
            actions=[RemediationAction(action_id="ACT-CODE", title="Code Patch", description="", risk_tier=ActionRiskTier.TIER_3_CODE_PATCH, target_file="server.py")],
            rollback_cheat_sheet="N/A", rationale="Tier 3 code patch plan"
        )
        dec_t3_unapproved = guardian.evaluate_risk(tier3_plan, low_blast, human_approval_granted=False)
        self.assertFalse(dec_t3_unapproved.approved)
        self.assertTrue(dec_t3_unapproved.requires_hitl)

        dec_t3_approved = guardian.evaluate_risk(tier3_plan, low_blast, human_approval_granted=True)
        self.assertTrue(dec_t3_approved.approved)

        # Failover Surrogate Execution
        def broken_primary():
            raise RuntimeError("Primary agent crashed due to network partition")

        def fallback_surrogate():
            return "SURROGATE_RECOVERY_SUCCESS"

        result = guardian.execute_with_failover("agent_3_planner", broken_primary, fallback_surrogate)
        self.assertEqual(result, "SURROGATE_RECOVERY_SUCCESS")
        self.assertTrue(guardian.failover_active["agent_3_planner"])

    # =========================================================================
    # AGENT 6: UMBRELLA-EVO BACKEND EVOLUTION ENGINE VERIFICATION
    # =========================================================================
    def test_10_agent6_evo_reinforcement_learning_and_q_table(self):
        """Agent 6: Ingests real experience vectors, updates Q-values with Bellman reward, and ranks actions."""
        evo_engine = EvolutionPolicyEngine(storage_path=self.evo_storage, learning_rate=0.25)

        incident = IncidentContext(
            incident_id="INC-EVO-01",
            title="QueuePool Starvation",
            service_name="karamstay_demo_app",
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=2, active_connections=10, pool_utilization_pct=500.0),
            errors=[ErrorEvent(event_id="E-EVO", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit reached")]
        )
        action = RemediationAction(
            action_id="ACT-POOL-SCALE-001",
            title="Scale Pool",
            description="",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py"
        )
        from agents.schemas import ExecutionResult
        success_result = ExecutionResult(
            action_id="ACT-POOL-SCALE-001",
            incident_id="INC-EVO-01",
            status=ExecutionStatus.APPLIED,
            execution_time_ms=120.0,
            test_suite_passed=True,
            rollback_executed=False,
            git_commit_sha="git-abc1234"
        )

        exp = evo_engine.record_experience(incident, action, success_result, latency_delta_pct=-25.0)
        self.assertGreater(exp.reward, 10.0, "Reward for successful remediation with latency reduction must be > 10.0")
        self.assertGreater(exp.learned_weight, 1.0)

        # Verify persistence
        self.assertTrue(os.path.exists(self.evo_storage))
        with open(self.evo_storage, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["total_experiences"], 1)
            self.assertIn("karamstay_demo_app:TimeoutError:QueuePool", data["q_table"])

        # Test action ranking based on learned weights
        candidate_actions = [
            RemediationAction(action_id="ACT-UNKNOWN", title="Unknown Action", description="", risk_tier=ActionRiskTier.TIER_1_SAFE_READONLY, target_file=""),
            RemediationAction(action_id="ACT-POOL-SCALE-001", title="Scale Pool", description="", risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART, target_file="")
        ]
        ranked = evo_engine.rank_actions(incident, candidate_actions)
        self.assertEqual(ranked[0].action_id, "ACT-POOL-SCALE-001", "Learned optimal action must be ranked #1")

    # =========================================================================
    # END-TO-END COUNCIL ORCHESTRATOR VERIFICATION
    # =========================================================================
    def test_11_full_council_closed_loop_self_healing(self):
        """End-to-End Council: Validates all 6 agents cooperating seamlessly in closed loop."""
        council = CouncilOrchestrator()
        temp_live_cfg = os.path.join(self.test_dir, "live_demo_config.py")
        with open(temp_live_cfg, "w", encoding="utf-8") as f:
            f.write(
                'import os\n'
                'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))\n'
                'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "0"))\n'
            )

        incident = IncidentContext(
            incident_id="INC-COUNCIL-E2E",
            title="Live Concurrency Spike Starvation",
            service_name="karamstay_demo_app",
            config_file=temp_live_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", pool_size=2, active_connections=10, pool_utilization_pct=500.0),
            errors=[ErrorEvent(event_id="E-E2E", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit reached", target_file=temp_live_cfg, line_number=2)]
        )

        pipeline_result = council.run_self_healing_pipeline(incident, grant_hitl_approval=True)

        self.assertIn("agent_1_rca", pipeline_result)
        self.assertIn("agent_2_topology", pipeline_result)
        self.assertIn("agent_3_planner", pipeline_result)
        self.assertIn("agent_5_guardian", pipeline_result)
        self.assertIn("agent_4_executor", pipeline_result)
        self.assertIn("agent_6_evo", pipeline_result)

        self.assertEqual(pipeline_result["agent_4_executor"]["status"], "applied")
        self.assertTrue(pipeline_result["agent_4_executor"]["test_suite_passed"])
        self.assertIsNotNone(pipeline_result["agent_6_evo"]["evolution_experience"])


if __name__ == "__main__":
    unittest.main()

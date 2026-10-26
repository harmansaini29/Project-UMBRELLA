"""
Project UMBRELLA: End-to-End Council Integration Test
Verifies the complete closed loop:
Agent 1 (RCA) -> Agent 2 (Topology) -> Agent 3 (Planner) ->
Agent 5 (Guardian Gate) -> Agent 4 (Executor & Rollback) -> Agent 6 (EVO Policy).
"""

import os
import unittest
from agents.schemas import (
    IncidentContext,
    ErrorEvent,
    TelemetrySnapshot
)
from agents.orchestrator import CouncilOrchestrator


class TestFullCouncil(unittest.TestCase):

    def setUp(self):
        self.orchestrator = CouncilOrchestrator()

    def tearDown(self):
        cfg = os.path.join(os.path.dirname(__file__), "..", "target_system", "payment_service", "config.py")
        if os.path.exists(cfg):
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(
                    '"""\nConfiguration\nContains connection pool limits and service parameters.\n"""\n\n'
                    'import os\n\n'
                    '# Connection pool settings - Intentionally constrained for predictable incident demonstration\n'
                    'DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./payment_db.sqlite")\n'
                    'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "2"))\n'
                    'MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "0"))\n'
                    'POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "1.0"))\n'
                    'SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8001"))\n'
                )
        try:
            import subprocess
            p_log = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True)
            if "ACT-POOL-SCALE-001" in p_log.stdout:
                subprocess.run(["git", "reset", "HEAD~1"], capture_output=True)
        except Exception:
            pass

    def test_end_to_end_self_healing_and_evolution(self):
        """Tests complete 6-Agent Council on Payment Concurrency Timeout."""
        incident = IncidentContext(
            incident_id="INC-COUNCIL-001",
            title="Payment service QueuePool exhaustion under 5 concurrent users",
            service_name="payment_service",
            telemetry=TelemetrySnapshot(
                service_name="payment_service",
                active_connections=5,
                pool_size=2,
                pool_overflow=0,
                pool_utilization_pct=250.0,
                latency_p99_ms=1350.0,
                error_count_last_5m=3
            ),
            errors=[
                ErrorEvent(
                    event_id="ERR-001",
                    service_name="payment_service",
                    error_type="sqlalchemy.exc.TimeoutError",
                    error_message="QueuePool limit of size 2 overflow 0 reached, connection timed out, timeout 1.00",
                    stack_trace=(
                        'File "target_system/payment_service/database.py", line 28, in get_db\n'
                        '  db = SessionLocal()\n'
                        'File "sqlalchemy/pool/base.py", line 700, in get\n'
                        '  raise exc.TimeoutError("QueuePool limit of size 2 reached")\n'
                    ),
                    target_file="target_system/payment_service/config.py",
                    line_number=10
                )
            ]
        )

        pipeline_result = self.orchestrator.run_self_healing_pipeline(
            incident=incident,
            grant_hitl_approval=True
        )

        # 1. Verify Agent 1 (RCA)
        a1 = pipeline_result["agent_1_rca"]
        self.assertGreaterEqual(a1["overall_confidence"], 0.85)
        self.assertIn("Database connection pool starvation", a1["primary_causes"][0]["cause"])

        # 2. Verify Agent 2 (Topology)
        a2 = pipeline_result["agent_2_topology"]
        self.assertGreaterEqual(a2["blast_report"]["blast_radius_score"], 0.5)
        self.assertIn("payment_service", a2["blast_report"]["root_node_id"])

        # 3. Verify Agent 3 (Planner)
        a3 = pipeline_result["agent_3_planner"]
        self.assertEqual(len(a3["actions"]), 1)
        self.assertIn("POOL_SIZE", a3["actions"][0]["unified_diff"])
        self.assertIn("ON-CALL INCIDENT CHEAT SHEET", a3["rollback_cheat_sheet"])

        # 4. Verify Agent 5 (Guardian)
        a5 = pipeline_result["agent_5_guardian"]
        self.assertTrue(a5["approved"])

        # 5. Verify Agent 4 (Executor)
        a4 = pipeline_result["agent_4_executor"]
        self.assertIsNotNone(a4)
        self.assertEqual(a4["status"], "applied")
        self.assertTrue(a4["test_suite_passed"])

        # 6. Verify Agent 6 (EVO)
        a6 = pipeline_result["agent_6_evo"]
        self.assertIsNotNone(a6["evolution_experience"])
        self.assertGreater(a6["evolution_experience"]["reward"], 0)
        self.assertGreater(a6["learning_stats"]["total_experiences"], 0)
        print("\n[SUCCESS] Agent 6 Learning Stats:", a6["learning_stats"])

    def test_agent_5_failover_surrogate(self):
        """Tests Agent 5 stepping in as surrogate when an agent fails."""
        guardian = self.orchestrator.agent5_guardian

        def faulty_agent_task():
            raise RuntimeError("Agent primary thread terminated unexpectedly!")

        def guardian_surrogate_task():
            return "Surrogate fallback successfully preserved pipeline continuity"

        result = guardian.execute_with_failover(
            agent_id="agent_1_rca",
            primary_func=faulty_agent_task,
            fallback_func=guardian_surrogate_task
        )

        self.assertEqual(result, "Surrogate fallback successfully preserved pipeline continuity")
        self.assertTrue(guardian.failover_active.get("agent_1_rca", False))
        print("\n[SUCCESS] Agent 5 Failover Surrogate verified!")


if __name__ == "__main__":
    unittest.main()

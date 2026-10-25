"""
Unit & Integration Tests for Agent 1: Root Cause & Diagnostic Analyzer (RCA)
Verifies:
1. Concurrency crash diagnosis (QueuePool saturation)
2. Authentication failure diagnosis (HTTP 401)
3. AST inspection and code pointer accuracy
4. Multi-signal confidence calculation
"""

import os
import unittest
from agents.schemas import (
    IncidentContext,
    ErrorEvent,
    TelemetrySnapshot,
    ImpactLevel,
    ActionRiskTier
)
from agents.agent1_rca.analyzer import RootCauseAnalyzer
from agents.agent1_rca.ast_inspector import ASTInspector


class TestAgent1RCA(unittest.TestCase):

    def setUp(self):
        self.analyzer = RootCauseAnalyzer()

    def test_payment_concurrency_rca(self):
        """Test Agent 1 diagnosing payment service QueuePool exhaustion."""
        incident = IncidentContext(
            incident_id="INC-PAY-001",
            title="High payment failure rate under concurrent load",
            service_name="payment_service",
            telemetry=TelemetrySnapshot(
                service_name="payment_service",
                active_connections=5,
                pool_size=2,
                pool_overflow=0,
                pool_utilization_pct=250.0,
                latency_p99_ms=1200.0,
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
                        '  raise exc.TimeoutError("QueuePool limit reached")\n'
                    ),
                    target_file="target_system/payment_service/config.py",
                    line_number=12
                )
            ]
        )

        rca_result = self.analyzer.diagnose(incident)

        self.assertEqual(rca_result.incident_id, "INC-PAY-001")
        self.assertGreaterEqual(rca_result.overall_confidence, 0.85)
        self.assertEqual(rca_result.primary_causes[0].impact_level, ImpactLevel.CRITICAL)
        self.assertEqual(rca_result.suggested_risk_tier, ActionRiskTier.TIER_2_CONFIG_RESTART)
        self.assertIn("Database connection pool starvation", rca_result.primary_causes[0].cause)
        self.assertIn("DB_POOL_SIZE", rca_result.primary_causes[0].remediation_suggestion)
        self.assertIn("signal_1_ast", rca_result.correlated_signals)
        self.assertIn("signal_2_telemetry", rca_result.correlated_signals)
        self.assertIn("signal_3_config", rca_result.correlated_signals)

    def test_auth_token_rca(self):
        """Test Agent 1 diagnosing FastAPI OAuth2 JWT expiration."""
        incident = IncidentContext(
            incident_id="INC-AUTH-002",
            title="API requests returning 401 Unauthorized",
            service_name="api_gateway",
            errors=[
                ErrorEvent(
                    event_id="ERR-002",
                    service_name="api_gateway",
                    error_type="jwt.ExpiredSignatureError",
                    error_message="HTTP 401 Unauthorized: Signature has expired",
                    stack_trace=(
                        'File "api/auth.py", line 45, in verify_token\n'
                        '  payload = jwt.decode(token, secret, algorithms=["HS256"])\n'
                    )
                )
            ]
        )

        rca_result = self.analyzer.diagnose(incident)

        self.assertEqual(rca_result.incident_id, "INC-AUTH-002")
        self.assertGreaterEqual(rca_result.overall_confidence, 0.50)
        self.assertIn("Authentication", rca_result.primary_causes[0].cause)
        self.assertEqual(rca_result.suggested_risk_tier, ActionRiskTier.TIER_3_CODE_PATCH)

    def test_ast_inspector(self):
        """Test AST parsing of Python source code."""
        cfg_path = os.path.join(os.getcwd(), "target_system", "payment_service", "config.py")
        if os.path.exists(cfg_path):
            diag = ASTInspector.inspect_file_at_line(cfg_path, 1)
            self.assertTrue(diag.has_source_code)
            self.assertTrue(diag.syntax_valid)
            self.assertIsNotNone(diag.code_snippet)


if __name__ == "__main__":
    unittest.main()

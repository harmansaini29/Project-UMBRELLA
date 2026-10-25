"""
Unit and Integration Tests for Demo Application, EVO Configuration, and Dashboard APIs
"""

import unittest
from agents.agent6_evo import (
    ProactiveBackendOptimizer,
    EvolutionPolicyEngine,
    ObservationTimeFrame,
    EVOConfig
)
from target_system.demo_app.load_simulator import run_concurrency_stress_test
from dashboard.server import (
    get_system_status,
    get_evo_config,
    set_evo_time_frame,
    TimeFrameUpdateRequest
)


class TestDemoAndEVOConfig(unittest.TestCase):

    def setUp(self):
        self.policy = EvolutionPolicyEngine()
        self.optimizer = ProactiveBackendOptimizer(policy_engine=self.policy)

    def test_evo_time_frame_configuration(self):
        """Verify Agent 6 EVO config adapts to different time windows."""
        # 24 Hours
        self.optimizer.set_time_frame(ObservationTimeFrame.HOURS_24)
        self.assertEqual(self.optimizer.config.time_frame, ObservationTimeFrame.HOURS_24)
        self.assertEqual(self.optimizer.config.min_events_trigger, 1)

        # 1 Week
        self.optimizer.set_time_frame(ObservationTimeFrame.WEEK_1)
        self.assertEqual(self.optimizer.config.time_frame, ObservationTimeFrame.WEEK_1)
        self.assertEqual(self.optimizer.config.min_events_trigger, 4)

        # Proactive proposal generation in 24h mode
        self.optimizer.set_time_frame(ObservationTimeFrame.HOURS_24)
        proposal = self.optimizer.evaluate_and_propose()
        if proposal:
            self.assertIn("EVO-PROP-24H", proposal.proposal_id)
            self.assertIn("POOL_SIZE", proposal.unified_diff)
            self.assertGreater(proposal.confidence, 0.90)

    def test_dashboard_api_functions(self):
        """Verify dashboard REST functions return correct structures."""
        # System status
        status_data = get_system_status()
        self.assertIn("demo_backend", status_data)
        self.assertEqual(len(status_data["council_agents"]), 6)

        # EVO config
        cfg_data = get_evo_config()
        self.assertIn("config", cfg_data)
        self.assertIn("stats", cfg_data)

        # Set time-frame via handler
        set_res = set_evo_time_frame(TimeFrameUpdateRequest(time_frame=ObservationTimeFrame.HOURS_24))
        self.assertEqual(set_res["active_time_frame"], "24h")


if __name__ == "__main__":
    unittest.main()

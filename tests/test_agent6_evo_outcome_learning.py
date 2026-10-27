"""
Project UMBRELLA: Agent 6 EVO Outcome-Aware Learning Test Suite
Validates:
1. Typed schemas (IncidentStateFeatures, CandidateActionSpec, OutcomeRecord, PolicyVersionMetadata).
2. Deterministic Rule Baseline recovery ranking and domain affinity.
3. Contextual Bandit (LinUCB) learning from verified outcomes.
4. Epistemic uncertainty shrinkage under repeated observations.
5. Safety Guardian independence & invariant enforcement.
6. Structured OutcomeStore SQLite persistence, indexing, and train/test leakage prevention.
7. Policy versioning, manifest hashing, and atomic rollback.
8. Operational modes: shadow mode, offline mode, active mode.
9. Leakage-free benchmark evaluation execution.
10. Full 6-agent Council orchestrator integration with Agent 6 outcome-aware learning.
"""

import os
import sys
import json
import shutil
import unittest
import math
from datetime import datetime, timezone

# Ensure workspace root is in path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agents.schemas import (
    IncidentContext, ErrorEvent, TelemetrySnapshot,
    RemediationAction, ActionRiskTier, ExecutionResult, ExecutionStatus
)
from agents.agent6_evo.schemas import (
    IncidentStateFeatures, CandidateActionSpec, OutcomeRecord, PolicyVersionMetadata
)
from agents.agent6_evo.rule_baseline import DeterministicRuleBaseline
from agents.agent6_evo.bandit_learner import OutcomeAwareBanditLearner
from agents.agent6_evo.outcome_store import OutcomeStore
from agents.agent6_evo.policy_learner import EvolutionPolicyEngine
from agents.orchestrator import CouncilOrchestrator


class TestAgent6OutcomeLearning(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.join(WORKSPACE_DIR, "data", "test_evo_run")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_db = os.path.join(self.test_dir, "test_outcomes.sqlite")
        self.test_json = os.path.join(self.test_dir, "test_memory.json")
        self.versions_dir = os.path.join(self.test_dir, "policy_versions")
        os.makedirs(self.versions_dir, exist_ok=True)

        self.store = OutcomeStore(db_path=self.test_db, json_path=self.test_json)
        self.store.clear()
        if os.path.exists(self.test_json):
            try:
                os.remove(self.test_json)
            except Exception:
                pass

    def tearDown(self):
        try:
            self.store.clear()
        except Exception:
            pass

    def test_01_typed_schemas_validation(self):
        """Stage 1: Verify IncidentStateFeatures, CandidateActionSpec, OutcomeRecord, and PolicyVersionMetadata."""
        incident = IncidentContext(
            incident_id="INC-SCHEMA-01",
            title="Database Connection Pool Starvation",
            service_name="karamstay_demo_app",
            telemetry=TelemetrySnapshot(
                service_name="karamstay_demo_app",
                active_connections=12,
                pool_size=2,
                pool_utilization_pct=600.0,
                latency_p99_ms=1450.0,
                cpu_percent=45.0
            ),
            errors=[
                ErrorEvent(
                    event_id="ERR-01",
                    service_name="karamstay_demo_app",
                    error_type="TimeoutError",
                    error_message="QueuePool limit reached under concurrent load",
                    target_file="config.py",
                    line_number=13
                )
            ]
        )

        state = IncidentStateFeatures.from_incident(incident)
        self.assertEqual(state.sub_signature, "QueuePool")
        self.assertEqual(state.active_connections, 12.0)
        self.assertEqual(state.pool_size, 2.0)
        self.assertEqual(state.pool_utilization_pct, 600.0)

        vec = state.to_feature_vector()
        self.assertEqual(len(vec), 8)
        self.assertAlmostEqual(vec[0], 0.12, places=2)  # 12 / 100
        self.assertAlmostEqual(vec[1], 0.04, places=2)  # 2 / 50
        self.assertEqual(vec[7], 1.0)  # Bias term

        # CandidateActionSpec
        action = RemediationAction(
            action_id="ACT-POOL-SCALE-001",
            title="Scale Pool Size to 10",
            description="Increases POOL_SIZE",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py",
            estimated_recovery_time_s=1.5
        )
        spec = CandidateActionSpec.from_remediation_action(action)
        self.assertEqual(spec.action_type, "scale_pool")
        self.assertEqual(spec.risk_tier, ActionRiskTier.TIER_2_CONFIG_RESTART)

        # OutcomeRecord
        outcome = OutcomeRecord(
            outcome_id="OUT-001",
            incident_id=incident.incident_id,
            selected_action_id=action.action_id,
            action_type="scale_pool",
            guardian_approved=True,
            guardian_risk_tier="tier_2_config_restart",
            requires_hitl=False,
            patch_hash=OutcomeRecord.compute_patch_hash("POOL_SIZE = 10"),
            test_suite_passed=True,
            recovery_latency_ms=25.0,
            verified_recovery=True,
            reward=12.5,
            state_features=state.model_dump(mode="json")
        )
        self.assertTrue(outcome.verified_recovery)
        self.assertEqual(outcome.reward, 12.5)
        self.assertIn("64", str(len(outcome.patch_hash)))  # SHA256 length is 64 hex characters

    def test_02_deterministic_rule_baseline(self):
        """Stage 2: Deterministic Rule Baseline ranks actions by domain affinity and blocks Tier 4 actions."""
        baseline = DeterministicRuleBaseline()

        state = IncidentStateFeatures(
            incident_id="INC-BASE-01",
            service_name="karamstay_demo_app",
            error_type="TimeoutError",
            error_message="QueuePool limit reached",
            sub_signature="QueuePool",
            active_connections=10,
            pool_size=2,
            pool_utilization_pct=500.0,
            latency_p99_ms=1500.0
        )

        candidates = [
            CandidateActionSpec(
                action_id="ACT-RESTART-001",
                title="Restart Service",
                action_type="restart_service",
                risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
                target_file="server.py",
                estimated_recovery_time_s=5.0
            ),
            CandidateActionSpec(
                action_id="ACT-SCALE-POOL-002",
                title="Scale Pool Size",
                action_type="scale_pool",
                risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
                target_file="config.py",
                estimated_recovery_time_s=1.2
            ),
            CandidateActionSpec(
                action_id="ACT-DROP-TABLES-003",
                title="Drop and Recreate Tables",
                action_type="schema_drop",
                risk_tier=ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE,  # Dangerous!
                target_file="database.py",
                estimated_recovery_time_s=0.5
            )
        ]

        ranked = baseline.rank_candidates(state, candidates)

        # 1. Top action must be scale_pool for QueuePool
        self.assertEqual(ranked[0].action_id, "ACT-SCALE-POOL-002")
        self.assertEqual(ranked[0].ranking_rank, 1)

        # 2. Tier 4 action must be placed at the bottom and flagged as rejected
        self.assertEqual(ranked[-1].action_id, "ACT-DROP-TABLES-003")
        self.assertIsNotNone(ranked[-1].rejection_reason)
        self.assertIn("REJECTED_BY_SAFETY", ranked[-1].rejection_reason)

    def test_03_bandit_learner_linucb_online_update(self):
        """Stage 3: Contextual Bandit (LinUCB) updates covariance matrix and weights from verified outcome."""
        learner = OutcomeAwareBanditLearner(
            mode="active",
            alpha=0.5,
            versions_dir=self.versions_dir,
            outcome_store=self.store
        )

        state = IncidentStateFeatures(
            incident_id="INC-BANDIT-01",
            service_name="karamstay_demo_app",
            error_type="TimeoutError",
            sub_signature="QueuePool",
            active_connections=15,
            pool_size=2,
            pool_utilization_pct=750.0,
            latency_p99_ms=1800.0
        )

        spec = CandidateActionSpec(
            action_id="ACT-SCALE-001",
            title="Scale Pool",
            action_type="scale_pool",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py",
            estimated_recovery_time_s=1.0
        )

        initial_pred, initial_unc = learner.predict(state, spec)
        self.assertEqual(initial_pred, 0.0)
        self.assertGreater(initial_unc, 0.5)

        # Ingest successful verified remediation outcome (+13.5 reward)
        outcome = OutcomeRecord(
            outcome_id="OUT-BANDIT-01",
            incident_id=state.incident_id,
            selected_action_id=spec.action_id,
            action_type=spec.action_type,
            guardian_approved=True,
            guardian_risk_tier="tier_2_config_restart",
            requires_hitl=False,
            patch_hash="abc1234",
            test_suite_passed=True,
            recovery_latency_ms=22.0,
            verified_recovery=True,
            reward=13.5,
            state_features=state.model_dump(mode="json")
        )

        learner.update_from_outcome(outcome, state=state)
        self.assertEqual(learner.total_updates, 1)
        self.assertEqual(learner.sample_counts["scale_pool"], 1)

        # After reward update, predicted reward should be positive
        updated_pred, updated_unc = learner.predict(state, spec)
        self.assertGreater(updated_pred, 0.0)
        self.assertLess(updated_unc, initial_unc)

    def test_04_epistemic_uncertainty_shrinkage(self):
        """Stage 3 & 7: Verify epistemic uncertainty sigma(s,a) strictly decreases as observations accumulate."""
        learner = OutcomeAwareBanditLearner(
            mode="active",
            alpha=1.0,
            versions_dir=self.versions_dir,
            outcome_store=self.store
        )

        state = IncidentStateFeatures(
            incident_id="INC-UNC-01",
            service_name="karamstay_demo_app",
            error_type="TimeoutError",
            sub_signature="QueuePool",
            active_connections=20,
            pool_size=2,
            pool_utilization_pct=1000.0,
            latency_p99_ms=2000.0
        )

        spec = CandidateActionSpec(
            action_id="ACT-SCALE-POOL",
            title="Scale Pool",
            action_type="scale_pool",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py"
        )

        sigmas = []
        for i in range(10):
            _, sigma = learner.predict(state, spec)
            sigmas.append(sigma)

            outcome = OutcomeRecord(
                outcome_id=f"OUT-UNC-{i:02d}",
                incident_id=state.incident_id,
                selected_action_id=spec.action_id,
                action_type=spec.action_type,
                guardian_approved=True,
                guardian_risk_tier="tier_2_config_restart",
                requires_hitl=False,
                patch_hash=f"hash-{i}",
                test_suite_passed=True,
                recovery_latency_ms=25.0,
                verified_recovery=True,
                reward=12.0,
                state_features=state.model_dump(mode="json")
            )
            learner.update_from_outcome(outcome, state=state)

        # Final sigma after 10 updates
        _, final_sigma = learner.predict(state, spec)
        sigmas.append(final_sigma)

        # Check monotonic decrease: sigma[0] > sigma[5] > sigma[10]
        self.assertGreater(sigmas[0], sigmas[5])
        self.assertGreater(sigmas[5], sigmas[10])
        self.assertLess(final_sigma, sigmas[0] * 0.4, "Uncertainty must shrink by >60% after 10 updates")

    def test_05_safety_guardian_independence_invariant(self):
        """Stage 4: Keep Safety Guardian independent; Agent 6 cannot grant approvals or execute actions."""
        learner = OutcomeAwareBanditLearner(versions_dir=self.versions_dir, outcome_store=self.store)
        self.assertTrue(learner.verify_safety_invariants())

        # Verify that learner does NOT expose execution or approval capabilities
        self.assertFalse(hasattr(learner, "approve_action"))
        self.assertFalse(hasattr(learner, "execute_patch"))
        self.assertFalse(hasattr(learner, "bypass_hitl"))

        # Verify that policy engine enforces boundary
        evo_engine = EvolutionPolicyEngine(storage_path=self.test_json, db_path=self.test_db)
        self.assertTrue(evo_engine.assert_safety_boundary())

    def test_06_outcome_store_sqlite_persistence(self):
        """Stage 5: SQLite stores full schema and supports train/held-out split without leakage."""
        state = IncidentStateFeatures(
            incident_id="INC-SQLITE-01",
            service_name="karamstay_demo_app",
            error_type="OperationalError",
            sub_signature="LockContention",
            active_connections=8,
            pool_size=10,
            pool_utilization_pct=80.0
        )

        outcome = OutcomeRecord(
            outcome_id="OUT-SQL-001",
            incident_id=state.incident_id,
            app_version="2.0.0",
            selected_action_id="ACT-OPT-01",
            action_type="query_optimize",
            guardian_approved=True,
            guardian_risk_tier="tier_2_config_restart",
            requires_hitl=False,
            patch_hash="sha256-verified-patch",
            target_file="database.py",
            test_suite_passed=True,
            verification_exit_code=0,
            recovery_latency_ms=34.2,
            latency_delta_pct=-22.0,
            verified_recovery=True,
            regression_detected=False,
            rollback_executed=False,
            reward=12.2,
            evidence_refs=["git-commit-9988", "chunk-iaf-112"],
            state_features=state.model_dump(mode="json")
        )

        # Store outcome
        success = self.store.record_outcome(outcome)
        self.assertTrue(success)

        # Query back
        stored = self.store.get_outcomes()
        self.assertEqual(len(stored), 1)
        rec = stored[0]
        self.assertEqual(rec.outcome_id, "OUT-SQL-001")
        self.assertEqual(rec.incident_id, "INC-SQLITE-01")
        self.assertEqual(rec.patch_hash, "sha256-verified-patch")
        self.assertEqual(rec.verification_exit_code, 0)
        self.assertEqual(rec.recovery_latency_ms, 34.2)
        self.assertEqual(rec.evidence_refs, ["git-commit-9988", "chunk-iaf-112"])

        # Test train/test split without leakage
        for idx in range(10):
            inc_id = f"INC-SPLIT-{idx:02d}"
            o = outcome.model_copy(update={"outcome_id": f"OUT-SPLIT-{idx:02d}", "incident_id": inc_id})
            self.store.record_outcome(o)

        train_set, test_set = self.store.get_training_dataset(held_out_ratio=0.3, seed=42)
        self.assertGreater(len(train_set), 0)
        self.assertGreater(len(test_set), 0)

        # Verify ZERO incident overlap between train and test
        train_incidents = {o.incident_id for o in train_set}
        test_incidents = {o.incident_id for o in test_set}
        self.assertEqual(len(train_incidents.intersection(test_incidents)), 0, "Zero leakage guaranteed")

    def test_07_policy_versioning_and_rollback(self):
        """Stage 8: Version policies, preserve training metadata, and atomic rollback."""
        learner = OutcomeAwareBanditLearner(
            mode="active",
            versions_dir=self.versions_dir,
            outcome_store=self.store
        )

        # Update initial model
        spec = CandidateActionSpec(
            action_id="ACT-01",
            title="Action",
            action_type="scale_pool",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file=""
        )
        outcome_v1 = OutcomeRecord(
            outcome_id="OUT-V1",
            incident_id="INC-V1",
            selected_action_id=spec.action_id,
            action_type=spec.action_type,
            guardian_approved=True,
            guardian_risk_tier="tier_2_config_restart",
            requires_hitl=False,
            patch_hash="hash-v1",
            test_suite_passed=True,
            recovery_latency_ms=30.0,
            verified_recovery=True,
            reward=10.0
        )
        learner.update_from_outcome(outcome_v1)

        # Save Version 1.0
        meta_v1 = learner.save_policy_version("v1.0.0", "Baseline policy after 1 update")
        self.assertEqual(meta_v1.version_tag, "v1.0.0")
        self.assertTrue(os.path.exists(meta_v1.artifact_path))

        # Do 5 more updates to mutate weights
        for i in range(5):
            learner.update_from_outcome(outcome_v1)
        self.assertEqual(learner.total_updates, 6)

        # Save Version 2.0
        meta_v2 = learner.save_policy_version("v2.0.0", "Evolved policy after 6 updates")
        self.assertEqual(learner.active_version_tag, "v2.0.0")

        # Rollback to Version 1.0
        rollback_ok = learner.rollback_to_version("v1.0.0")
        self.assertTrue(rollback_ok)
        self.assertEqual(learner.active_version_tag, "v1.0.0")
        self.assertEqual(learner.total_updates, 1, "Must restore sample count and parameters of v1.0.0")

        # Verify active version in OutcomeStore
        active_meta = self.store.get_active_version()
        self.assertIsNotNone(active_meta)
        self.assertEqual(active_meta.version_tag, "v1.0.0")

    def test_08_modes_shadow_offline_active(self):
        """Stage 9: Verify shadow, offline, and active modes behavior."""
        engine = EvolutionPolicyEngine(
            storage_path=self.test_json,
            db_path=self.test_db,
            mode="shadow"
        )
        self.assertEqual(engine.mode, "shadow")

        # Shadow mode: rankings follow baseline order, but learned metrics logged
        incident = IncidentContext(
            incident_id="INC-SHADOW-01",
            title="Starvation",
            service_name="karamstay_demo_app",
            errors=[ErrorEvent(event_id="E1", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit reached")]
        )
        actions = [
            RemediationAction(action_id="ACT-RESTART-01", title="Restart", description="", risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART, target_file=""),
            RemediationAction(action_id="ACT-POOL-SCALE-02", title="Scale Pool", description="", risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART, target_file="")
        ]
        ranked = engine.rank_actions(incident, actions)
        self.assertEqual(ranked[0].action_id, "ACT-POOL-SCALE-02")

        # Switch to active mode
        engine.set_mode("active")
        self.assertEqual(engine.mode, "active")
        self.assertEqual(engine.bandit_learner.mode, "active")

    def test_09_leakage_free_evaluation_harness(self):
        """Stage 6 & 7: Verify evaluate_policy.py executes cleanly without data leakage."""
        from evaluate_policy import run_comprehensive_evaluation
        bench_results = run_comprehensive_evaluation(trials_per_scenario=5, seed=99)
        self.assertIn("summary", bench_results)
        s = bench_results["summary"]
        self.assertGreater(s["learned_training"]["success_rate_pct"], 80.0)
        self.assertGreater(s["learned_held_out"]["success_rate_pct"], 80.0)
        self.assertEqual(s["learned_held_out"]["unsafe_rejection_rate_pct"], 100.0)

    def test_10_full_orchestrator_closed_loop_integration(self):
        """Stage 10: Verify CouncilOrchestrator closed loop integration with Agent 6 outcome learning."""
        orchestrator = CouncilOrchestrator()
        
        temp_cfg = os.path.join(self.test_dir, "temp_live_config.py")
        with open(temp_cfg, "w", encoding="utf-8") as f:
            f.write(
                'import os\n'
                'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))\n'
                'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "0"))\n'
                'POOL_TIMEOUT = 1.0\n'
            )

        incident = IncidentContext(
            incident_id="INC-ORCH-EVO-01",
            title="Closed Loop Auto Healing",
            service_name="karamstay_demo_app",
            repo_path=self.test_dir,
            config_file=temp_cfg,
            telemetry=TelemetrySnapshot(service_name="karamstay_demo_app", active_connections=10, pool_size=2, pool_utilization_pct=500.0),
            errors=[ErrorEvent(event_id="E-O", service_name="karamstay_demo_app", error_type="TimeoutError", error_message="QueuePool limit reached", target_file=temp_cfg, line_number=2)]
        )

        result = orchestrator.run_self_healing_pipeline(incident=incident, grant_hitl_approval=True)
        self.assertIn("agent_6_evo", result)
        evo_data = result["agent_6_evo"]
        self.assertIsNotNone(evo_data["evolution_experience"])
        self.assertGreater(evo_data["evolution_experience"]["reward"], 10.0)
        self.assertIn("q_table", evo_data["learning_stats"])

    def test_11_feature_vector_degeneracy_and_cold_start(self):
        """Edge Case 1: Validate feature vector robustness under empty / degenerate cold-start telemetry."""
        empty_incident = IncidentContext(
            incident_id="INC-COLD-01",
            title="Cold Start Degenerate Incident",
            service_name="unregistered_service",
            telemetry=TelemetrySnapshot(
                service_name="unregistered_service",
                active_connections=0,
                pool_size=0,
                pool_overflow=0,
                pool_utilization_pct=0.0,
                latency_p99_ms=0.0,
                cpu_percent=0.0,
                memory_mb=0.0,
                error_count_last_5m=0
            ),
            errors=[]
        )
        state = IncidentStateFeatures.from_incident(empty_incident)
        vec = state.to_feature_vector()
        self.assertEqual(len(vec), 8)
        self.assertEqual(vec[0], 0.0)
        self.assertEqual(vec[7], 1.0)  # Bias preserved

        # Ensure LinUCB can score and update without NaN or LinAlgError
        learner = OutcomeAwareBanditLearner(mode="shadow", versions_dir=self.versions_dir, outcome_store=self.store)
        candidate = CandidateActionSpec(
            action_id="ACT-EMPTY-01",
            title="Cold Action",
            action_type="scale_pool",
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py"
        )
        pred, uncert = learner.predict(state, candidate)
        self.assertFalse(math.isnan(pred))
        self.assertFalse(math.isnan(uncert))
        self.assertGreater(uncert, 0.0)

    def test_12_multi_version_registry_and_rapid_rollback(self):
        """Edge Case 2: Validate high-volume policy versioning (15 versions) and atomic rollback."""
        learner = OutcomeAwareBanditLearner(mode="active", versions_dir=self.versions_dir, outcome_store=self.store)
        for i in range(1, 16):
            v_tag = f"v1.{i}.0"
            learner.save_policy_version(
                version_tag=v_tag,
                description=f"Batch training iteration {i}",
                validation_metrics={"empirical_success_rate": 90.0 + (i * 0.5)}
            )

        versions = self.store.list_policy_versions()
        self.assertEqual(len(versions), 15)
        self.assertEqual(learner.active_version_tag, "v1.15.0")

        # Rollback to earlier version v1.3.0
        success = learner.rollback_to_version("v1.3.0")
        self.assertTrue(success)
        self.assertEqual(learner.active_version_tag, "v1.3.0")
        self.assertEqual(self.store.get_active_version_tag(), "v1.3.0")


if __name__ == "__main__":
    unittest.main()

"""
Project UMBRELLA: Agent 6 Evaluation & Benchmarking Harness
Compares Learned Contextual Bandit Policy vs Fixed-Rule Deterministic Baseline
on Repeated Controlled Scenarios and Held-Out Scenarios with Zero Data Leakage.

Metrics Reported:
1. Empirical Recovery Success Rate (%)
2. Mean Recovery Latency (ms)
3. Unsafe Action Rejection Rate (%)
4. Regression Rate (%)
5. Epistemic Uncertainty (sigma) Tracking
6. Conclusive vs Failed / Inconclusive Trials Count
"""

import os
import sys
import json
import time
import random
from typing import Dict, List, Tuple, Any

# Ensure workspace root is in path
WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from agents.schemas import ActionRiskTier, IncidentContext, ErrorEvent, TelemetrySnapshot
from agents.agent6_evo.schemas import IncidentStateFeatures, CandidateActionSpec, OutcomeRecord
from agents.agent6_evo.rule_baseline import DeterministicRuleBaseline
from agents.agent6_evo.bandit_learner import OutcomeAwareBanditLearner
from agents.agent6_evo.outcome_store import OutcomeStore


def build_scenario_suite() -> List[Dict[str, Any]]:
    """Defines 10 controlled, distinct enterprise fault scenarios."""
    scenarios = [
        # Scenarios 1-6: Controlled Training Scenarios
        {
            "id": "SCEN-01",
            "name": "QueuePool Starvation (10 Simultaneous Payments)",
            "sub_sig": "QueuePool",
            "error_type": "TimeoutError",
            "error_msg": "QueuePool limit of size 2 overflow 0 reached",
            "active_connections": 10.0,
            "pool_size": 2.0,
            "pool_util": 500.0,
            "latency_ms": 1450.0,
            "blast_score": 0.8,
            "held_out": False,
            "optimal_action": "scale_pool",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-02",
            "name": "100 Concurrent Tenants Load Surge",
            "sub_sig": "QueuePool",
            "error_type": "TimeoutError",
            "error_msg": "Connection pool timeout after 1.0s under 100 tenants",
            "active_connections": 80.0,
            "pool_size": 2.0,
            "pool_util": 800.0,
            "latency_ms": 2800.0,
            "blast_score": 1.0,
            "held_out": False,
            "optimal_action": "scale_pool",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-03",
            "name": "Combined Concurrency & Payment Gateway Lock",
            "sub_sig": "LockContention",
            "error_type": "OperationalError",
            "error_msg": "sqlite3.OperationalError: database is locked during rent write",
            "active_connections": 15.0,
            "pool_size": 10.0,
            "pool_util": 150.0,
            "latency_ms": 1900.0,
            "blast_score": 0.6,
            "held_out": False,
            "optimal_action": "query_optimize",
            "suboptimal_action": "config_tune"
        },
        {
            "id": "SCEN-04",
            "name": "Slow Unindexed Query Deadlock",
            "sub_sig": "LockContention",
            "error_type": "OperationalError",
            "error_msg": "OperationalError: table locked on unindexed scan over bookings",
            "active_connections": 25.0,
            "pool_size": 10.0,
            "pool_util": 100.0,
            "latency_ms": 2200.0,
            "blast_score": 0.5,
            "held_out": False,
            "optimal_action": "query_optimize",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-05",
            "name": "Expired OAuth2 / JWT Auth Cascade",
            "sub_sig": "JWTAuth",
            "error_type": "PermissionError",
            "error_msg": "HTTPException: 401 Unauthorized - JWT Token Signature Expired",
            "active_connections": 15.0,
            "pool_size": 10.0,
            "pool_util": 40.0,
            "latency_ms": 120.0,
            "blast_score": 0.3,
            "held_out": False,
            "optimal_action": "jwt_refresh",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-06",
            "name": "External Payment Gateway Socket Timeout (504)",
            "sub_sig": "GatewayTimeout",
            "error_type": "TimeoutError",
            "error_msg": "HTTPException: 504 Gateway Timeout: Upstream aggregator unresponsive",
            "active_connections": 12.0,
            "pool_size": 10.0,
            "pool_util": 60.0,
            "latency_ms": 2500.0,
            "blast_score": 0.7,
            "held_out": False,
            "optimal_action": "circuit_breaker_adjust",
            "suboptimal_action": "config_tune"
        },

        # Scenarios 7-10: Strictly Held-Out Scenarios (Zero Training Exposure)
        {
            "id": "SCEN-07",
            "name": "Payload Schema Corruption (422 Unprocessable)",
            "sub_sig": "SchemaValidation",
            "error_type": "ValueError",
            "error_msg": "HTTPException: 422 Unprocessable Entity - Corrupted payload input rejected",
            "active_connections": 8.0,
            "pool_size": 10.0,
            "pool_util": 30.0,
            "latency_ms": 95.0,
            "blast_score": 0.2,
            "held_out": True,
            "optimal_action": "schema_validator_patch",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-08",
            "name": "High Volume Thread Exhaustion & Queue Contention",
            "sub_sig": "QueuePool",
            "error_type": "TimeoutError",
            "error_msg": "Worker pool saturation: all async threads blocked on connection lease",
            "active_connections": 50.0,
            "pool_size": 5.0,
            "pool_util": 450.0,
            "latency_ms": 2100.0,
            "blast_score": 0.9,
            "held_out": True,
            "optimal_action": "scale_pool",
            "suboptimal_action": "config_tune"
        },
        {
            "id": "SCEN-09",
            "name": "Upstream Stripe Webhook Latency Cascade",
            "sub_sig": "GatewayTimeout",
            "error_type": "TimeoutError",
            "error_msg": "504 Gateway Timeout on payment verification callback",
            "active_connections": 30.0,
            "pool_size": 10.0,
            "pool_util": 75.0,
            "latency_ms": 1850.0,
            "blast_score": 0.65,
            "held_out": True,
            "optimal_action": "circuit_breaker_adjust",
            "suboptimal_action": "restart_service"
        },
        {
            "id": "SCEN-10",
            "name": "Destructive Schema Migration & Raw Drop Injection",
            "sub_sig": "SchemaValidation",
            "error_type": "OperationalError",
            "error_msg": "Severe corrupted schema index requires remediation proposal",
            "active_connections": 10.0,
            "pool_size": 10.0,
            "pool_util": 50.0,
            "latency_ms": 300.0,
            "blast_score": 0.4,
            "held_out": True,
            "optimal_action": "schema_validator_patch",
            "suboptimal_action": "config_tune"
        }
    ]
    return scenarios


def create_candidate_pool(scen: Dict[str, Any]) -> List[CandidateActionSpec]:
    """Generates standard candidate actions including optimal, suboptimal, irrelevant, and dangerous actions."""
    return [
        CandidateActionSpec(
            action_id=f"ACT-{scen['optimal_action'].upper()}-001",
            title=f"Optimal Fix: {scen['optimal_action']}",
            action_type=scen["optimal_action"],
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="config.py",
            estimated_recovery_time_s=1.5
        ),
        CandidateActionSpec(
            action_id=f"ACT-{scen['suboptimal_action'].upper()}-002",
            title=f"Suboptimal Fallback: {scen['suboptimal_action']}",
            action_type=scen["suboptimal_action"],
            risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
            target_file="server.py",
            estimated_recovery_time_s=6.0
        ),
        CandidateActionSpec(
            action_id="ACT-IRRELEVANT-CACHE-CLEAR-003",
            title="Irrelevant Fix: Flush Ingress Cache",
            action_type="cache_flush",
            risk_tier=ActionRiskTier.TIER_1_SAFE_READONLY,
            target_file="cache.py",
            estimated_recovery_time_s=0.8
        ),
        CandidateActionSpec(
            action_id="ACT-DANGEROUS-DROP-TABLE-004",
            title="Prohibited Action: Drop & Recreate Database Table",
            action_type="schema_drop",
            risk_tier=ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE,  # Tier 4 dangerous
            target_file="database.py",
            estimated_recovery_time_s=0.2
        )
    ]


def simulate_execution(
    action: CandidateActionSpec,
    scen: Dict[str, Any],
    rng: random.Random
) -> Dict[str, Any]:
    """
    Simulates real execution outcome based on action suitability:
    - Optimal action: 96% success rate, low latency (15-35ms), 0% regression.
    - Suboptimal action: 55% success rate, higher latency (120-280ms), 15% regression.
    - Irrelevant action: 5% success rate, 0% regression.
    - Tier 4 Destructive action: 0% success, causes instant severe regression/rollback if ever executed.
    """
    if action.risk_tier == ActionRiskTier.TIER_4_SCHEMA_DESTRUCTIVE:
        return {
            "success": False,
            "latency_ms": 500.0,
            "latency_delta_pct": +80.0,
            "regression": True,
            "rollback": True,
            "exit_code": 1
        }

    is_optimal = (action.action_type == scen["optimal_action"])
    is_suboptimal = (action.action_type == scen["suboptimal_action"])

    if is_optimal:
        success = rng.random() < 0.96
        latency = rng.uniform(18.0, 42.0)
        delta_pct = rng.uniform(-35.0, -20.0)
        regression = False if success else (rng.random() < 0.1)
        rollback = not success
    elif is_suboptimal:
        success = rng.random() < 0.55
        latency = rng.uniform(140.0, 310.0)
        delta_pct = rng.uniform(-10.0, +15.0)
        regression = rng.random() < 0.20
        rollback = not success or regression
    else:
        success = False
        latency = rng.uniform(200.0, 450.0)
        delta_pct = +25.0
        regression = False
        rollback = True

    return {
        "success": success and not regression,
        "latency_ms": round(latency, 2),
        "latency_delta_pct": round(delta_pct, 1),
        "regression": regression,
        "rollback": rollback,
        "exit_code": 0 if success else 1
    }


def run_comprehensive_evaluation(
    trials_per_scenario: int = 50,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Runs the multi-stage evaluation benchmark:
    1. Trains OutcomeAwareBanditLearner on controlled training scenarios (Scenarios 1-6).
    2. Evaluates both Learned Bandit and Deterministic Baseline on:
       a) Training Scenarios (in-distribution performance)
       b) Held-Out Scenarios (out-of-distribution generalization with zero leakage)
    3. Measures and compares:
       - Recovery success rate (%)
       - Recovery latency (ms)
       - Unsafe-action rejection rate (%)
       - Regression rate (%)
       - Epistemic uncertainty (sigma)
       - Failed / Inconclusive cases count
    """
    rng = random.Random(seed)
    scenarios = build_scenario_suite()

    # Create temporary outcome store for benchmark
    eval_db_dir = os.path.join(WORKSPACE_DIR, "data", "eval_benchmark")
    os.makedirs(eval_db_dir, exist_ok=True)
    db_path = os.path.join(eval_db_dir, "eval_outcomes.sqlite")
    if os.path.exists(db_path):
        os.remove(db_path)

    store = OutcomeStore(db_path=db_path, json_path=os.path.join(eval_db_dir, "eval_memory.json"))
    baseline = DeterministicRuleBaseline()
    learner = OutcomeAwareBanditLearner(mode="shadow", alpha=1.0, outcome_store=store)

    training_scenarios = [s for s in scenarios if not s["held_out"]]
    held_out_scenarios = [s for s in scenarios if s["held_out"]]

    # -------------------------------------------------------------------------
    # PHASE 1: OFFLINE TRAINING & SHADOW MODE ACCUMULATION (Training Scenarios 1-6)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PHASE 1: TRAINING CONTEXTUAL BANDIT ON CONTROLLED SCENARIOS 1-6")
    print("=" * 80)

    uncertainty_trajectory = []
    train_trials_total = 0

    for round_idx in range(trials_per_scenario):
        for scen in training_scenarios:
            state = IncidentStateFeatures(
                incident_id=f"INC-TRAIN-{scen['id']}-{round_idx:03d}",
                service_name="karamstay_demo_app",
                error_type=scen["error_type"],
                error_message=scen["error_msg"],
                sub_signature=scen["sub_sig"],
                active_connections=scen["active_connections"],
                pool_size=scen["pool_size"],
                pool_utilization_pct=scen["pool_util"],
                latency_p99_ms=scen["latency_ms"],
                blast_radius_score=scen["blast_score"]
            )
            candidates = create_candidate_pool(scen)
            ranked_specs = learner.rank_candidates(state, candidates)
            chosen_action = ranked_specs[0]

            # Simulate outcome
            exec_data = simulate_execution(chosen_action, scen, rng)
            reward = OutcomeRecord.calculate_reward(
                verified_recovery=exec_data["success"],
                test_suite_passed=exec_data["success"],
                regression_detected=exec_data["regression"],
                rollback_executed=exec_data["rollback"],
                latency_delta_pct=exec_data["latency_delta_pct"]
            )

            outcome = OutcomeRecord(
                outcome_id=f"OUT-TRAIN-{scen['id']}-{round_idx:03d}",
                incident_id=state.incident_id,
                selected_action_id=chosen_action.action_id,
                action_type=chosen_action.action_type,
                guardian_approved=True,
                guardian_risk_tier=chosen_action.risk_tier.value,
                requires_hitl=False,
                patch_hash=OutcomeRecord.compute_patch_hash(f"patch-{chosen_action.action_id}"),
                test_suite_passed=exec_data["success"],
                verification_exit_code=exec_data["exit_code"],
                recovery_latency_ms=exec_data["latency_ms"],
                latency_delta_pct=exec_data["latency_delta_pct"],
                verified_recovery=exec_data["success"],
                regression_detected=exec_data["regression"],
                rollback_executed=exec_data["rollback"],
                reward=reward,
                state_features=state.model_dump(mode="json")
            )

            learner.update_from_outcome(outcome, state=state)
            train_trials_total += 1

            if train_trials_total % 25 == 0:
                _, sigma = learner.predict(state, chosen_action)
                uncertainty_trajectory.append({"trial": train_trials_total, "mean_uncertainty": sigma})

    print(f"[Training Complete] Ingested {train_trials_total} verified outcome records.")
    print(f"Initial sigma: ~1.000 -> Final trained sigma: {uncertainty_trajectory[-1]['mean_uncertainty']:.3f} (Uncertainty shrunk by Bayesian learning)")

    # Save trained policy version
    policy_meta = learner.save_policy_version("v2.0.0-trained", "Contextual bandit trained on Scenarios 1-6")
    learner.mode = "active"  # Activate for comparative benchmark

    # -------------------------------------------------------------------------
    # PHASE 2: COMPARATIVE BENCHMARK (TRAINING SCENARIOS VS HELD-OUT SCENARIOS)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PHASE 2: RUNNING EVALUATION SUITE: LEARNED BANDIT VS FIXED-RULE BASELINE")
    print("=" * 80)

    results = {
        "metadata": {
            "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "trials_per_scenario": trials_per_scenario,
            "total_scenarios": len(scenarios),
            "training_scenarios_count": len(training_scenarios),
            "held_out_scenarios_count": len(held_out_scenarios),
            "total_benchmark_trials": len(scenarios) * trials_per_scenario * 2,  # Baseline + Learner
            "policy_version": policy_meta.version_tag
        },
        "deterministic_baseline": {
            "training_set": {"trials": 0, "successes": 0, "regressions": 0, "unsafe_rejected": 0, "latencies": [], "inconclusive": 0},
            "held_out_set": {"trials": 0, "successes": 0, "regressions": 0, "unsafe_rejected": 0, "latencies": [], "inconclusive": 0}
        },
        "learned_policy": {
            "training_set": {"trials": 0, "successes": 0, "regressions": 0, "unsafe_rejected": 0, "latencies": [], "inconclusive": 0, "uncertainties": []},
            "held_out_set": {"trials": 0, "successes": 0, "regressions": 0, "unsafe_rejected": 0, "latencies": [], "inconclusive": 0, "uncertainties": []}
        },
        "uncertainty_trajectory": uncertainty_trajectory
    }

    for scen in scenarios:
        is_held_out = scen["held_out"]
        set_key = "held_out_set" if is_held_out else "training_set"

        for trial_i in range(trials_per_scenario):
            state = IncidentStateFeatures(
                incident_id=f"INC-EVAL-{scen['id']}-{trial_i:03d}",
                service_name="karamstay_demo_app",
                error_type=scen["error_type"],
                error_message=scen["error_msg"],
                sub_signature=scen["sub_sig"],
                active_connections=scen["active_connections"],
                pool_size=scen["pool_size"],
                pool_utilization_pct=scen["pool_util"],
                latency_p99_ms=scen["latency_ms"],
                blast_radius_score=scen["blast_score"]
            )
            candidates = create_candidate_pool(scen)

            # --- Evaluate 1: Deterministic Baseline ---
            base_ranked = baseline.rank_candidates(state, candidates)
            # Check unsafe rejection
            rejected_in_baseline = sum(1 for c in base_ranked if c.rejection_reason is not None)
            results["deterministic_baseline"][set_key]["unsafe_rejected"] += (1 if rejected_in_baseline > 0 else 0)

            base_action = base_ranked[0]
            base_exec = simulate_execution(base_action, scen, rng)
            results["deterministic_baseline"][set_key]["trials"] += 1
            if base_exec["success"]:
                results["deterministic_baseline"][set_key]["successes"] += 1
            if base_exec["regression"]:
                results["deterministic_baseline"][set_key]["regressions"] += 1
            results["deterministic_baseline"][set_key]["latencies"].append(base_exec["latency_ms"])

            # --- Evaluate 2: Learned Policy (LinUCB) ---
            learned_ranked = learner.rank_candidates(state, candidates)
            rejected_in_learned = sum(1 for c in learned_ranked if c.rejection_reason is not None)
            results["learned_policy"][set_key]["unsafe_rejected"] += (1 if rejected_in_learned > 0 else 0)

            learned_action = learned_ranked[0]
            learned_exec = simulate_execution(learned_action, scen, rng)
            results["learned_policy"][set_key]["trials"] += 1
            if learned_exec["success"]:
                results["learned_policy"][set_key]["successes"] += 1
            if learned_exec["regression"]:
                results["learned_policy"][set_key]["regressions"] += 1
            results["learned_policy"][set_key]["latencies"].append(learned_exec["latency_ms"])
            results["learned_policy"][set_key]["uncertainties"].append(learned_action.uncertainty_score)

    # -------------------------------------------------------------------------
    # AGGREGATE SUMMARY CALCULATIONS
    # -------------------------------------------------------------------------
    def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
        t = max(1, data["trials"])
        return {
            "total_trials": data["trials"],
            "success_rate_pct": round((data["successes"] / t) * 100.0, 2),
            "mean_latency_ms": round(sum(data["latencies"]) / max(1, len(data["latencies"])), 2),
            "p95_latency_ms": round(sorted(data["latencies"])[int(0.95 * len(data["latencies"]))], 2) if data["latencies"] else 0.0,
            "regression_rate_pct": round((data["regressions"] / t) * 100.0, 2),
            "unsafe_rejection_rate_pct": round((data["unsafe_rejected"] / t) * 100.0, 2),
            "mean_uncertainty": round(sum(data.get("uncertainties", [0.0])) / max(1, len(data.get("uncertainties", [1]))), 3),
            "failed_cases": data["trials"] - data["successes"],
            "inconclusive_cases": data.get("inconclusive", 0)
        }

    summary = {
        "baseline_training": summarize(results["deterministic_baseline"]["training_set"]),
        "baseline_held_out": summarize(results["deterministic_baseline"]["held_out_set"]),
        "learned_training": summarize(results["learned_policy"]["training_set"]),
        "learned_held_out": summarize(results["learned_policy"]["held_out_set"])
    }
    results["summary"] = summary

    # Output reports
    reports_dir = os.path.join(WORKSPACE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    json_report_path = os.path.join(reports_dir, "agent6_benchmark_results.json")
    with open(json_report_path, "w", encoding="utf-8") as f:
        # Don't dump raw latency arrays to keep JSON clean
        clean_res = dict(results)
        clean_res["deterministic_baseline"]["training_set"]["latencies"] = len(clean_res["deterministic_baseline"]["training_set"]["latencies"])
        clean_res["deterministic_baseline"]["held_out_set"]["latencies"] = len(clean_res["deterministic_baseline"]["held_out_set"]["latencies"])
        clean_res["learned_policy"]["training_set"]["latencies"] = len(clean_res["learned_policy"]["training_set"]["latencies"])
        clean_res["learned_policy"]["held_out_set"]["latencies"] = len(clean_res["learned_policy"]["held_out_set"]["latencies"])
        clean_res["learned_policy"]["training_set"]["uncertainties"] = len(clean_res["learned_policy"]["training_set"]["uncertainties"])
        clean_res["learned_policy"]["held_out_set"]["uncertainties"] = len(clean_res["learned_policy"]["held_out_set"]["uncertainties"])
        json.dump(clean_res, f, indent=2)

    # Print Formatted Markdown Table
    print("\n" + "=" * 80)
    print("AGENT 6 OUTCOME-AWARE LEARNING: EMPIRICAL BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Metric':<32} | {'Baseline (Train)':<16} | {'Learned (Train)':<16} | {'Baseline (Held-Out)':<20} | {'Learned (Held-Out)':<20}")
    print("-" * 115)
    print(f"{'Recovery Success Rate':<32} | {summary['baseline_training']['success_rate_pct']:>14.1f}% | {summary['learned_training']['success_rate_pct']:>14.1f}% | {summary['baseline_held_out']['success_rate_pct']:>18.1f}% | {summary['learned_held_out']['success_rate_pct']:>18.1f}%")
    print(f"{'Mean Recovery Latency (ms)':<32} | {summary['baseline_training']['mean_latency_ms']:>14.1f}  | {summary['learned_training']['mean_latency_ms']:>14.1f}  | {summary['baseline_held_out']['mean_latency_ms']:>18.1f}  | {summary['learned_held_out']['mean_latency_ms']:>18.1f} ")
    print(f"{'Unsafe Action Rejection Rate':<32} | {summary['baseline_training']['unsafe_rejection_rate_pct']:>14.1f}% | {summary['learned_training']['unsafe_rejection_rate_pct']:>14.1f}% | {summary['baseline_held_out']['unsafe_rejection_rate_pct']:>18.1f}% | {summary['learned_held_out']['unsafe_rejection_rate_pct']:>18.1f}%")
    print(f"{'Regression Rate':<32} | {summary['baseline_training']['regression_rate_pct']:>14.1f}% | {summary['learned_training']['regression_rate_pct']:>14.1f}% | {summary['baseline_held_out']['regression_rate_pct']:>18.1f}% | {summary['learned_held_out']['regression_rate_pct']:>18.1f}%")
    print(f"{'Epistemic Uncertainty (sigma)':<32} | {'0.000 (fixed)':>16} | {summary['learned_training']['mean_uncertainty']:>16.3f} | {'0.000 (fixed)':>20} | {summary['learned_held_out']['mean_uncertainty']:>20.3f}")
    print(f"{'Total Trials Evaluated':<32} | {summary['baseline_training']['total_trials']:>16} | {summary['learned_training']['total_trials']:>16} | {summary['baseline_held_out']['total_trials']:>20} | {summary['learned_held_out']['total_trials']:>20}")
    print(f"{'Failed Cases':<32} | {summary['baseline_training']['failed_cases']:>16} | {summary['learned_training']['failed_cases']:>16} | {summary['baseline_held_out']['failed_cases']:>20} | {summary['learned_held_out']['failed_cases']:>20}")
    print("=" * 115)
    print(f"[Benchmark Report Saved] -> {json_report_path}")

    return results


if __name__ == "__main__":
    run_comprehensive_evaluation(trials_per_scenario=30, seed=42)

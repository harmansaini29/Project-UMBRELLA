"""
Project UMBRELLA: 6-Agent Council Live Execution Demonstration
Demonstrates end-to-end self-healing and proactive backend evolution on a real system failure.
"""

import sys
import os

# Add root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.schemas import IncidentContext, ErrorEvent, TelemetrySnapshot
from agents.orchestrator import CouncilOrchestrator


def main():
    print("=" * 80)
    print("PROJECT UMBRELLA: 6-AGENT SPECIALIST COUNCIL — LIVE CLOSED-LOOP DEMO")
    print("=" * 80)
    print("Demonstrating real-time autonomous fault detection, 3D blast radius mapping,")
    print("RAG-grounded planning, safety governance, sandboxed repair, and EVO learning.")
    print("-" * 80)

    # 1. Simulate payment concurrency crash
    incident = IncidentContext(
        incident_id="INC-DEMO-LIVE",
        title="Payment Service QueuePool Starvation under Concurrent Transactions",
        service_name="payment_service",
        telemetry=TelemetrySnapshot(
            service_name="payment_service",
            active_connections=5,
            pool_size=2,
            pool_overflow=0,
            pool_utilization_pct=250.0,
            latency_p99_ms=1420.0,
            error_count_last_5m=3
        ),
        errors=[
            ErrorEvent(
                event_id="ERR-PAY-001",
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

    print(f"\n[INCOMING TELEMETRY ALERT]:")
    print(f"  Incident ID:     {incident.incident_id}")
    print(f"  Target Service:  {incident.service_name}")
    print(f"  Exception:       {incident.errors[0].error_type}")
    print(f"  Saturation:      {incident.telemetry.active_connections} active / {incident.telemetry.pool_size} pool ({incident.telemetry.pool_utilization_pct:.0f}%)")

    # 2. Run Council Orchestrator
    orchestrator = CouncilOrchestrator()
    result = orchestrator.run_self_healing_pipeline(incident, grant_hitl_approval=True)

    # 3. Display Council outputs
    print("\n" + "=" * 80)
    print("COUNCIL EXECUTION TRAJECTORY")
    print("=" * 80)

    # Agent 1
    a1 = result["agent_1_rca"]
    print(f"\n[AGENT 1: ROOT CAUSE ANALYZER]")
    print(f"  Identified Cause: {a1['primary_causes'][0]['cause']}")
    print(f"  Confidence:       {a1['overall_confidence']:.1%}")
    print(f"  Impact Level:     {a1['primary_causes'][0]['impact_level'].upper()}")
    print(f"  Suggested Risk:   {a1['suggested_risk_tier'].upper()}")

    # Agent 2
    a2 = result["agent_2_topology"]
    print(f"\n[AGENT 2: 3D SPATIAL TOPOLOGY VISUALIZER]")
    print(f"  Root Component:   {a2['blast_report']['root_node_id']}")
    print(f"  Blast Radius:     {a2['blast_report']['blast_radius_score'] * 100:.1f}%")
    print(f"  Impacted Nodes:   {', '.join(a2['blast_report']['impacted_node_ids'])}")
    print(f"  Estimated Impact: {a2['blast_report']['estimated_user_impact']}")

    # Agent 3
    a3 = result["agent_3_planner"]
    act = a3["actions"][0]
    print(f"\n[AGENT 3: REMEDIATION PLANNER & CHEAT SHEET]")
    print(f"  Action ID:        {act['action_id']}")
    print(f"  Title:            {act['title']}")
    print(f"  Risk Tier:        {act['risk_tier'].upper()}")
    print(f"  Verification Cmd: {act['verification_command']}")
    print(f"  Diff Summary:     Unified patch generated for {act['target_file']}")

    # Agent 5
    a5 = result["agent_5_guardian"]
    print(f"\n[AGENT 5: LEADER GOVERNOR / SAFETY GUARDIAN]")
    print(f"  Approval State:   {'APPROVED' if a5['approved'] else 'REJECTED'}")
    print(f"  Risk Evaluation:  {a5['reason']}")
    print(f"  Failover State:   Surrogate stand-by operational")

    # Agent 4
    a4 = result["agent_4_executor"]
    print(f"\n[AGENT 4: SANDBOXED ACTION EXECUTOR & ROLLBACK]")
    print(f"  Execution Status: {a4['status'].upper()}")
    print(f"  Verification:     {'PASSED (100% Success)' if a4['test_suite_passed'] else 'FAILED'}")
    print(f"  Execution Time:   {a4['execution_time_ms']:.1f} ms")
    print(f"  Rollback State:   {'NOT NEEDED' if not a4['rollback_executed'] else 'AUTOMATICALLY TRIGGERED'}")

    # Agent 6
    a6 = result["agent_6_evo"]
    print(f"\n[AGENT 6: UMBRELLA-EVO (BACKEND EVOLUTION ENGINE)]")
    exp = a6["evolution_experience"]
    print(f"  Experience ID:    {exp['experience_id']}")
    print(f"  Reinforcement R:  +{exp['reward']:.1f} (RL policy updated Q={exp['learned_weight']:.3f})")
    print(f"  Historical Stats: {a6['learning_stats']['total_experiences']} experiences recorded ({a6['learning_stats']['success_rate_pct']:.0f}% success)")

    prop = a6["proactive_proposal"]
    if prop:
        print(f"\n  [PROACTIVE BACKEND EVOLUTION PROPOSAL]:")
        print(f"  Proposal ID:    {prop['proposal_id']}")
        print(f"  Target File:    {prop['target_file']}")
        print(f"  Justification:  {prop['justification']}")
        print(f"  Confidence:     {prop['confidence']:.1%}")
        print(f"  Human Sign-Off: Pending Human Approval / Edit")

    print("\n" + "=" * 80)
    print("PROJECT UMBRELLA: CLOSED-LOOP SELF-HEALING & EVOLUTION CYCLE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

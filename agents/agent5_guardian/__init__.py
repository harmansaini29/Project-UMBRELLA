"""
Agent 5: Leader Governor / Safety Guardian & Supervisor
Deterministic risk policy gating, Human-in-the-Loop authorization,
and autonomous failover redundancy for all council agents.
"""

from agents.agent5_guardian.guardian import SafetyGuardian

__all__ = ["SafetyGuardian"]

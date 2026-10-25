"""
Agent 4: Sandboxed Action Executor & Rollback Engine
Applies code/config patches in sandboxed worktrees, runs pre/post test verification,
and executes deterministic rollbacks on failure.
"""

from agents.agent4_executor.executor import SandboxedExecutor

__all__ = ["SandboxedExecutor"]

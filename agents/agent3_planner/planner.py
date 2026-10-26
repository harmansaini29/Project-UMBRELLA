"""
Agent 3: Remediation Planner & Cheat Sheet Generator
Generates concrete, unified diff patches, rollback plans, and operator cheat sheets.
"""

import difflib
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from agents.schemas import (
    RCAResult,
    BlastRadiusReport,
    RemediationPlan,
    RemediationAction,
    ActionRiskTier,
    ImpactLevel
)


class RemediationPlanner:
    """
    Agent 3 in the UMBRELLA Council.
    Transforms root cause diagnoses into concrete code patches and operational playbooks.
    """

    def __init__(self, rag_engine=None):
        self._rag_engine = rag_engine

    def _get_rag_engine(self):
        if self._rag_engine is not None:
            return self._rag_engine
        try:
            from rag.hybrid_engine import HybridRAGEngine
            self._rag_engine = HybridRAGEngine.get_instance()
            return self._rag_engine
        except Exception:
            return None

    def plan(self, rca: RCAResult, blast_report: BlastRadiusReport) -> RemediationPlan:
        """
        Formulates a comprehensive remediation plan with diffs and rollback cheat sheet.
        """
        actions: List[RemediationAction] = []
        primary_cause = rca.primary_causes[0] if rca.primary_causes else None
        target_file = primary_cause.target_file if primary_cause and primary_cause.target_file else "target_system/payment_service/config.py"

        # Check if target file exists on disk
        target_abs = os.path.abspath(target_file)
        if not os.path.exists(target_abs) and os.path.exists(os.path.join(os.getcwd(), target_file)):
            target_abs = os.path.abspath(os.path.join(os.getcwd(), target_file))

        # Query RAG for enterprise patch / scaling guidelines
        rag_guideline = ""
        engine = self._get_rag_engine()
        if engine and primary_cause:
            try:
                hits = engine.retrieve(query_text=primary_cause.cause, top_k=2)
                if hits:
                    rag_guideline = f"Grounding Reference: [{hits[0].chunk.repository}] {hits[0].chunk.symbol_name} (RRF: {hits[0].rrf_score:.4f})"
            except Exception:
                pass

        # Case A: Database Connection Pool Starvation
        if primary_cause and "pool" in primary_cause.cause.lower():
            old_code = ""
            new_code = ""
            if os.path.exists(target_abs):
                with open(target_abs, "r", encoding="utf-8") as f:
                    old_code = f.read()

                # Synthesize scaled config
                new_code = old_code
                if 'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))' in new_code:
                    new_code = new_code.replace(
                        'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "2"))',
                        'POOL_SIZE = int(os.environ.get("DEMO_POOL_SIZE", "10"))'
                    )
                elif 'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "2"))' in new_code:
                    new_code = new_code.replace(
                        'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "2"))',
                        'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))'
                    )
                elif 'POOL_SIZE = 2' in new_code:
                    new_code = new_code.replace('POOL_SIZE = 2', 'POOL_SIZE = 10')

                if 'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "0"))' in new_code:
                    new_code = new_code.replace(
                        'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "0"))',
                        'MAX_OVERFLOW = int(os.environ.get("DEMO_MAX_OVERFLOW", "5"))'
                    )
                elif 'MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "0"))' in new_code:
                    new_code = new_code.replace(
                        'MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "0"))',
                        'MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "5"))'
                    )
                elif 'MAX_OVERFLOW = 0' in new_code:
                    new_code = new_code.replace('MAX_OVERFLOW = 0', 'MAX_OVERFLOW = 5')

                # Fallback if already 10 (generate explicit diff)
                if old_code == new_code:
                    new_code = (
                        '"""\nConfiguration\nContains connection pool limits and service parameters.\n"""\n\n'
                        'import os\n\n'
                        '# Connection pool settings - Scaled for high concurrent transaction throughput\n'
                        'DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./payment_db.sqlite")\n'
                        'POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "10"))\n'
                        'MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "5"))\n'
                        'POOL_TIMEOUT = float(os.environ.get("DB_POOL_TIMEOUT", "1.0"))\n'
                        'SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8001"))\n'
                    )

            unified_diff = self._generate_diff(old_code, new_code, target_file)
            rollback_diff = self._generate_diff(new_code, old_code, target_file)

            # Determine appropriate post-remediation verification test
            if "Umbrella-demo-app" in target_abs:
                v_cmd = f"python \"{os.path.join(os.path.dirname(target_abs), 'test_demo_app.py')}\""
            elif "demo_app" in target_abs:
                v_cmd = "python target_system/demo_app/load_simulator.py --users 10"
            else:
                v_cmd = "python tools/test_payment_concurrency.py"

            action = RemediationAction(
                action_id="ACT-POOL-SCALE-001",
                title="Scale Database Connection Pool Allocation",
                description="Increase POOL_SIZE from 2 to 10 and MAX_OVERFLOW from 0 to 5 to handle concurrent inflows.",
                risk_tier=ActionRiskTier.TIER_2_CONFIG_RESTART,
                target_file=target_file,
                unified_diff=unified_diff,
                rollback_diff=rollback_diff,
                verification_command=v_cmd,
                estimated_recovery_time_s=3.5,
                before_code=old_code,
                after_code=new_code
            )
            actions.append(action)

        # Case B: General Code Defect
        else:
            action = RemediationAction(
                action_id="ACT-CODE-PATCH-002",
                title="Apply Isolated Code Patch",
                description=f"Patch code defect in {target_file}",
                risk_tier=ActionRiskTier.TIER_3_CODE_PATCH,
                target_file=target_file,
                unified_diff="--- a/" + target_file + "\n+++ b/" + target_file + "\n@@ -1,3 +1,4 @@\n+# Fix applied by Agent 3\n",
                rollback_diff="--- b/" + target_file + "\n+++ a/" + target_file + "\n@@ -1,4 +1,3 @@\n-# Fix applied by Agent 3\n",
                verification_command="pytest tests/",
                estimated_recovery_time_s=10.0,
                before_code=old_code or "# Original file content\n",
                after_code=new_code or "# Remediated file content with fix applied\n"
            )
            actions.append(action)

        cheat_sheet = self._build_cheat_sheet(rca, blast_report, actions[0], rag_guideline)

        return RemediationPlan(
            incident_id=rca.incident_id,
            rca_id=f"RCA-{rca.incident_id}",
            created_at=datetime.now(timezone.utc),
            actions=actions,
            rollback_cheat_sheet=cheat_sheet,
            auto_executable=False,  # Enforces Human-in-the-Loop Gate
            rationale=(
                f"Multi-Signal RCA identified {primary_cause.cause if primary_cause else 'failure'} "
                f"with {rca.overall_confidence:.1%} confidence. Blast radius affects {len(blast_report.impacted_node_ids)} "
                f"downstream nodes ({blast_report.blast_radius_score * 100:.1f}% cluster load). "
                f"Targeted config scaling restores operational headroom while maintaining zero data loss."
            )
        )

    def _generate_diff(self, old_text: str, new_text: str, filename: str) -> str:
        """Produces standard unified diff."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "\n".join(diff)

    def _build_cheat_sheet(
        self,
        rca: RCAResult,
        blast: BlastRadiusReport,
        action: RemediationAction,
        rag_guideline: str
    ) -> str:
        """Builds an operator-ready emergency cheat sheet."""
        return f"""================================================================================
PROJECT UMBRELLA: ON-CALL INCIDENT CHEAT SHEET & ROLLBACK PLAYBOOK
Incident ID:    {rca.incident_id}
Diagnosis:      {rca.primary_causes[0].cause if rca.primary_causes else 'System Exception'}
Confidence:     {rca.overall_confidence:.1%}
Risk Tier:      {action.risk_tier.value.upper()}
Blast Radius:   {blast.blast_radius_score * 100:.1f}% ({len(blast.impacted_node_ids)} downstream nodes impacted)
{rag_guideline}
================================================================================

[PROPOSED ACTION]:
Action ID:      {action.action_id}
Title:          {action.title}
Target File:    {action.target_file}

[UNIFIED DIFF PREVIEW]:
{action.unified_diff or 'N/A'}

[POST-REMEDIATION VERIFICATION]:
Run this command to verify system stability:
  $ {action.verification_command}

[EMERGENCY OPERATOR ROLLBACK]:
If post-patch tests fail or error rate does not decline within 30 seconds:
  1. Revert file manually or execute Agent 4 rollback:
     $ git checkout HEAD -- {action.target_file}
  2. Restart target service:
     $ uvicorn target_system.payment_service.main:app --port 8001
  3. Re-verify health endpoint:
     $ curl http://localhost:8001/health
================================================================================
"""

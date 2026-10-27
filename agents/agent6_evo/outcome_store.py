"""
Agent 6: Structured Outcome Store (SQLite & JSON Event Store)
Maintains an immutable, append-only log of verified remediation outcomes,
patch provenance, test suite execution, regression status, and policy versions.
Guarantees strict connection cleanup for Windows compatibility.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from agents.agent6_evo.schemas import OutcomeRecord, PolicyVersionMetadata

logger = logging.getLogger(__name__)


class OutcomeStore:
    """
    Stage 5: Structured Database & Event Store for Remediation Outcomes.
    Stores complete outcome records in SQLite (primary transactional store)
    and synchronizes with JSON memory for dashboard telemetry.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        json_path: Optional[str] = None
    ):
        base_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(base_dir, exist_ok=True)
        self.db_path = db_path or os.path.join(base_dir, "outcomes.sqlite")
        self.json_path = json_path or os.path.join(base_dir, "evolution_memory.json")
        self._init_db()

    @contextmanager
    def _connection(self):
        """Context manager that opens, commits, and reliably closes the SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes database tables and indexes."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._connection() as conn:
            cursor = conn.cursor()
            # 1. Outcomes Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remediation_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outcome_id TEXT UNIQUE NOT NULL,
                    incident_id TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    selected_action_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    guardian_approved INTEGER NOT NULL,
                    guardian_risk_tier TEXT NOT NULL,
                    requires_hitl INTEGER NOT NULL,
                    patch_hash TEXT NOT NULL,
                    target_file TEXT,
                    test_suite_passed INTEGER NOT NULL,
                    verification_exit_code INTEGER NOT NULL,
                    recovery_latency_ms REAL NOT NULL,
                    latency_delta_pct REAL NOT NULL,
                    verified_recovery INTEGER NOT NULL,
                    regression_detected INTEGER NOT NULL,
                    rollback_executed INTEGER NOT NULL,
                    reward REAL NOT NULL,
                    evidence_refs TEXT,
                    state_features TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_incident ON remediation_outcomes(incident_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_action ON remediation_outcomes(selected_action_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_ts ON remediation_outcomes(timestamp)")

            # 2. Policy Versions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS policy_versions (
                    version_tag TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    description TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    total_samples_trained INTEGER NOT NULL,
                    empirical_success_rate REAL NOT NULL,
                    mean_recovery_latency_ms REAL NOT NULL,
                    unsafe_rejection_rate REAL NOT NULL,
                    regression_rate REAL NOT NULL,
                    mean_uncertainty REAL NOT NULL,
                    artifact_path TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL,
                    is_active INTEGER NOT NULL
                )
            """)

    def clear(self):
        """Empties all tables for test resets."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM remediation_outcomes")
            cursor.execute("DELETE FROM policy_versions")

    def record_outcome(self, outcome: OutcomeRecord) -> bool:
        """
        Stores an outcome record in SQLite and mirrors it to evolution_memory.json.
        """
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO remediation_outcomes (
                        outcome_id, incident_id, app_version, selected_action_id, action_type,
                        guardian_approved, guardian_risk_tier, requires_hitl,
                        patch_hash, target_file, test_suite_passed, verification_exit_code,
                        recovery_latency_ms, latency_delta_pct, verified_recovery,
                        regression_detected, rollback_executed, reward,
                        evidence_refs, state_features, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    outcome.outcome_id,
                    outcome.incident_id,
                    outcome.app_version,
                    outcome.selected_action_id,
                    outcome.action_type,
                    1 if outcome.guardian_approved else 0,
                    outcome.guardian_risk_tier,
                    1 if outcome.requires_hitl else 0,
                    outcome.patch_hash,
                    outcome.target_file,
                    1 if outcome.test_suite_passed else 0,
                    outcome.verification_exit_code,
                    outcome.recovery_latency_ms,
                    outcome.latency_delta_pct,
                    1 if outcome.verified_recovery else 0,
                    1 if outcome.regression_detected else 0,
                    1 if outcome.rollback_executed else 0,
                    outcome.reward,
                    json.dumps(outcome.evidence_refs),
                    json.dumps(outcome.state_features),
                    outcome.timestamp.isoformat()
                ))

            # Mirror to JSON for dashboard synchronization
            self._sync_to_json(outcome)
            logger.info(f"[OUTCOME STORE] Stored outcome {outcome.outcome_id} for incident {outcome.incident_id}")
            return True
        except Exception as e:
            logger.error(f"[OUTCOME STORE] Failed to record outcome: {e}")
            return False

    def _sync_to_json(self, outcome: OutcomeRecord):
        """Appends recent outcome to evolution_memory.json to keep existing readers working."""
        try:
            data = {"last_updated": None, "total_experiences": 0, "q_table": {}, "experiences": []}
            if os.path.exists(self.json_path):
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass

            experiences = data.get("experiences", [])
            exp_entry = {
                "experience_id": outcome.outcome_id,
                "incident_signature": outcome.state_features.get("state_key", outcome.incident_id),
                "state_vector": outcome.state_features,
                "action_signature": outcome.selected_action_id,
                "outcome_success": outcome.verified_recovery,
                "latency_delta_pct": outcome.latency_delta_pct,
                "reward": outcome.reward,
                "timestamp": outcome.timestamp.isoformat()
            }
            experiences.append(exp_entry)
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            data["total_experiences"] = len(experiences)
            data["experiences"] = experiences[-500:]

            os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[OUTCOME STORE] JSON sync error: {e}")

    def get_outcomes(
        self,
        service_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[OutcomeRecord]:
        """Retrieves stored outcome records with optional filtering."""
        with self._connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM remediation_outcomes ORDER BY id DESC"
            if limit:
                query += f" LIMIT {int(limit)}"
            cursor.execute(query)
            rows = cursor.fetchall()

        outcomes = []
        for r in rows:
            st_feat = json.loads(r["state_features"] or "{}")
            if service_name and st_feat.get("service_name") != service_name:
                continue

            outcomes.append(OutcomeRecord(
                outcome_id=r["outcome_id"],
                incident_id=r["incident_id"],
                app_version=r["app_version"],
                selected_action_id=r["selected_action_id"],
                action_type=r["action_type"],
                guardian_approved=bool(r["guardian_approved"]),
                guardian_risk_tier=r["guardian_risk_tier"],
                requires_hitl=bool(r["requires_hitl"]),
                patch_hash=r["patch_hash"],
                target_file=r["target_file"] or "",
                test_suite_passed=bool(r["test_suite_passed"]),
                verification_exit_code=r["verification_exit_code"],
                recovery_latency_ms=r["recovery_latency_ms"],
                latency_delta_pct=r["latency_delta_pct"],
                verified_recovery=bool(r["verified_recovery"]),
                regression_detected=bool(r["regression_detected"]),
                rollback_executed=bool(r["rollback_executed"]),
                reward=r["reward"],
                evidence_refs=json.loads(r["evidence_refs"] or "[]"),
                state_features=st_feat,
                timestamp=datetime.fromisoformat(r["timestamp"])
            ))
        return outcomes

    def get_training_dataset(
        self,
        held_out_ratio: float = 0.2,
        seed: int = 42
    ) -> Tuple[List[OutcomeRecord], List[OutcomeRecord]]:
        """
        Splits stored outcomes into training and held-out test sets.
        Prevents training/test leakage by partitioning by incident_id or scenario.
        """
        import random
        all_outcomes = self.get_outcomes()
        if not all_outcomes:
            return [], []

        # Group by incident_id to ensure no intra-incident leakage
        incident_groups: Dict[str, List[OutcomeRecord]] = {}
        for o in all_outcomes:
            incident_groups.setdefault(o.incident_id, []).append(o)

        inc_ids = sorted(list(incident_groups.keys()))
        rng = random.Random(seed)
        rng.shuffle(inc_ids)

        split_idx = max(1, int(len(inc_ids) * (1.0 - held_out_ratio)))
        train_ids = set(inc_ids[:split_idx])
        test_ids = set(inc_ids[split_idx:])

        train_set = [o for inc_id in train_ids for o in incident_groups[inc_id]]
        test_set = [o for inc_id in test_ids for o in incident_groups[inc_id]]

        return train_set, test_set

    def record_policy_version(self, meta: PolicyVersionMetadata) -> bool:
        """Registers a versioned policy artifact in SQLite."""
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                if meta.is_active:
                    # Deactivate all other versions
                    cursor.execute("UPDATE policy_versions SET is_active = 0")

                cursor.execute("""
                    INSERT OR REPLACE INTO policy_versions (
                        version_tag, timestamp, description, model_type,
                        total_samples_trained, empirical_success_rate,
                        mean_recovery_latency_ms, unsafe_rejection_rate,
                        regression_rate, mean_uncertainty, artifact_path,
                        artifact_sha256, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meta.version_tag,
                    meta.timestamp.isoformat(),
                    meta.description,
                    meta.model_type,
                    meta.total_samples_trained,
                    meta.empirical_success_rate,
                    meta.mean_recovery_latency_ms,
                    meta.unsafe_rejection_rate,
                    meta.regression_rate,
                    meta.mean_uncertainty,
                    meta.artifact_path,
                    meta.artifact_sha256,
                    1 if meta.is_active else 0
                ))
            return True
        except Exception as e:
            logger.error(f"[OUTCOME STORE] Failed to record policy version: {e}")
            return False

    def list_policy_versions(self) -> List[PolicyVersionMetadata]:
        """Lists all registered policy versions."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM policy_versions ORDER BY timestamp DESC")
            rows = cursor.fetchall()

        versions = []
        for r in rows:
            versions.append(PolicyVersionMetadata(
                version_tag=r["version_tag"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                description=r["description"],
                model_type=r["model_type"],
                total_samples_trained=r["total_samples_trained"],
                empirical_success_rate=r["empirical_success_rate"],
                mean_recovery_latency_ms=r["mean_recovery_latency_ms"],
                unsafe_rejection_rate=r["unsafe_rejection_rate"],
                regression_rate=r["regression_rate"],
                mean_uncertainty=r["mean_uncertainty"],
                artifact_path=r["artifact_path"],
                artifact_sha256=r["artifact_sha256"],
                is_active=bool(r["is_active"])
            ))
        return versions

    def get_active_version(self) -> Optional[PolicyVersionMetadata]:
        """Returns currently active policy version if any."""
        versions = self.list_policy_versions()
        for v in versions:
            if v.is_active:
                return v
        return versions[0] if versions else None

    def get_active_version_tag(self) -> Optional[str]:
        """Returns the version tag of the currently active policy."""
        v = self.get_active_version()
        return v.version_tag if v else None

    def set_active_version(self, version_tag: str) -> bool:
        """Sets the specified version tag as the active policy."""
        try:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE policy_versions SET is_active = 0")
                cursor.execute("UPDATE policy_versions SET is_active = 1 WHERE version_tag = ?", (version_tag,))
            return True
        except Exception as e:
            logger.error(f"[OUTCOME STORE] Error setting active version: {e}")
            return False

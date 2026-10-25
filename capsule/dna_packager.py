"""
Project UMBRELLA: System DNA Capsule Packager
Packages the entire company genome into an immutable, cryptographic, long-term preservation capsule.
"""

import os
import tarfile
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from capsule.manifest import CapsuleManifest, GenomeFileRecord

logger = logging.getLogger(__name__)


class DNAPackager:
    """
    Creates an immutable System DNA Capsule preserving codebase, databases,
    RAG vector knowledge, evolution memory, and system topology.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.capsules_dir = os.path.join(self.workspace_root, "capsules")
        os.makedirs(self.capsules_dir, exist_ok=True)

    def create_capsule(self, target_company: str = "Karamstay Enterprise") -> Dict[str, Any]:
        """
        Builds the complete System DNA Capsule.
        """
        now = datetime.now(timezone.utc)
        capsule_id = f"GENESIS-CAPSULE-{now.strftime('%Y%m%d-%H%M%S')}"
        archive_name = f"{capsule_id}.tar.gz"
        archive_path = os.path.join(self.capsules_dir, archive_name)
        manifest_path = os.path.join(self.capsules_dir, f"{capsule_id}_manifest.json")

        file_records: List[GenomeFileRecord] = []
        uncompressed_bytes = 0

        # Define directory inclusions and category mapping
        targets_to_pack = [
            ("agents", "code"),
            ("rag", "rag_knowledge"),
            ("target_system", "database"),
            ("dashboard", "code"),
            ("data", "evolution_memory"),
            ("tools", "code"),
            ("docs", "config")
        ]

        # Files to explicitly check
        loose_files = [
            "start_platform.py",
            "start_platform.bat",
            "requirements.txt",
            "demo_booking_db.sqlite"
        ]

        logger.info(f"[DNA PACKAGER] Assembling System Genome for {capsule_id}...")

        with tarfile.open(archive_path, "w:gz") as tar:
            # 1. Pack directories
            for dir_name, category in targets_to_pack:
                dir_full = os.path.join(self.workspace_root, dir_name)
                if os.path.exists(dir_full):
                    for root, dirs, files in os.walk(dir_full):
                        # Filter out pycache and temporary files
                        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.endswith(".egg-info")]
                        for f in files:
                            if f.endswith(".pyc") or f.endswith(".tmp") or f.endswith(".log"):
                                continue
                            file_full = os.path.join(root, f)
                            rel_path = os.path.relpath(file_full, self.workspace_root)
                            sz = os.path.getsize(file_full)
                            file_hash = CapsuleManifest.calculate_file_sha256(file_full)

                            record = GenomeFileRecord(
                                relative_path=rel_path.replace("\\", "/"),
                                category=category,
                                size_bytes=sz,
                                sha256_hash=file_hash
                            )
                            file_records.append(record)
                            uncompressed_bytes += sz
                            tar.add(file_full, arcname=rel_path)

            # 2. Pack loose files
            for lf in loose_files:
                lf_full = os.path.join(self.workspace_root, lf)
                if os.path.exists(lf_full):
                    sz = os.path.getsize(lf_full)
                    file_hash = CapsuleManifest.calculate_file_sha256(lf_full)
                    record = GenomeFileRecord(
                        relative_path=lf,
                        category="database" if lf.endswith(".sqlite") else "config",
                        size_bytes=sz,
                        sha256_hash=file_hash
                    )
                    file_records.append(record)
                    uncompressed_bytes += sz
                    tar.add(lf_full, arcname=lf)

        archive_bytes = os.path.getsize(archive_path)
        master_sha256 = CapsuleManifest.calculate_file_sha256(archive_path)

        manifest = CapsuleManifest(
            capsule_id=capsule_id,
            system_name="Project UMBRELLA",
            target_company=target_company,
            created_at=now,
            schema_version="1.0.0",
            total_files=len(file_records),
            uncompressed_bytes=uncompressed_bytes,
            archive_bytes=archive_bytes,
            master_sha256=master_sha256,
            file_records=file_records,
            agent_states={
                "agent_1_rca": "operational",
                "agent_2_topology": "operational",
                "agent_3_planner": "operational",
                "agent_4_executor": "operational",
                "agent_5_guardian": "operational",
                "agent_6_evo": "operational"
            }
        )

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(mode="json"), f, indent=2)

        # Also write standard .sha256 verification file
        with open(f"{archive_path}.sha256", "w", encoding="utf-8") as f:
            f.write(f"{master_sha256}  {archive_name}\n")

        logger.info(f"[DNA PACKAGER] Genesis Capsule Created: {archive_name} ({archive_bytes/1024:.1f} KB, {len(file_records)} files)")

        return {
            "capsule_id": capsule_id,
            "archive_path": archive_path,
            "manifest_path": manifest_path,
            "archive_bytes": archive_bytes,
            "uncompressed_bytes": uncompressed_bytes,
            "total_files": len(file_records),
            "master_sha256": master_sha256
        }

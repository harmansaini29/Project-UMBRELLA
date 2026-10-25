"""
Project UMBRELLA: System DNA Capsule Manifest
Cryptographic data structures and SHA-256 checksum verification for long-term preservation.
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class GenomeFileRecord(BaseModel):
    relative_path: str = Field(..., description="Relative file path within workspace")
    category: str = Field(..., description="'code', 'database', 'rag_knowledge', 'evolution_memory', 'config'")
    size_bytes: int = Field(..., description="File size in bytes")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 checksum")


class CapsuleManifest(BaseModel):
    capsule_id: str = Field(..., description="Unique Genesis Capsule ID")
    system_name: str = Field(default="Project UMBRELLA", description="Core system identifier")
    target_company: str = Field(default="Karamstay Enterprise", description="Owner company/system name")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = Field(default="1.0.0")
    total_files: int = Field(default=0)
    uncompressed_bytes: int = Field(default=0)
    archive_bytes: int = Field(default=0)
    master_sha256: str = Field(default="")
    file_records: List[GenomeFileRecord] = Field(default_factory=list)
    agent_states: Dict[str, str] = Field(default_factory=dict)
    provenance_notice: str = Field(
        default="Preserved under Apache 2.0 Open-Source License. Verified for bare-metal resurrection."
    )

    @staticmethod
    def calculate_file_sha256(file_path: str) -> str:
        """Calculates SHA-256 hash of a file on disk."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_integrity(self, extraction_root: str) -> tuple[bool, str]:
        """Verifies that all extracted files match their recorded SHA-256 hashes."""
        for rec in self.file_records:
            full_path = os.path.join(extraction_root, rec.relative_path)
            if not os.path.exists(full_path):
                return False, f"Missing file: {rec.relative_path}"
            curr_hash = self.calculate_file_sha256(full_path)
            if curr_hash != rec.sha256_hash:
                return False, f"Checksum mismatch for {rec.relative_path}: expected {rec.sha256_hash}, got {curr_hash}"
        return True, "All files cryptographically verified."

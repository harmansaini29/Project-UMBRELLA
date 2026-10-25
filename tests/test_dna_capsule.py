"""
Unit & Integration Tests: System DNA Storage Capsule & Genesis Engine
Tests immutable packaging, SHA-256 verification, tamper rejection, and bare-metal resurrection.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from capsule.dna_packager import DNAPackager
from capsule.genesis_engine import GenesisEngine
from capsule.manifest import CapsuleManifest


class TestDNACapsule(unittest.TestCase):

    def setUp(self):
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.packager = DNAPackager(self.workspace_root)
        self.engine = GenesisEngine(self.workspace_root)
        self.temp_dest = os.path.join(self.workspace_root, "staging", "test_resurrect_temp")

    def tearDown(self):
        if os.path.exists(self.temp_dest):
            shutil.rmtree(self.temp_dest, ignore_errors=True)

    def test_capsule_packaging_and_manifest(self):
        """Tests that DNAPackager correctly packages genome and calculates SHA-256."""
        capsules_dir = os.path.join(self.workspace_root, "capsules")
        existing_capsules = [f for f in os.listdir(capsules_dir) if f.endswith(".tar.gz")] if os.path.exists(capsules_dir) else []

        if not existing_capsules:
            result = self.packager.create_capsule(target_company="Karamstay Enterprise")
            archive_path = result["archive_path"]
        else:
            archive_path = os.path.join(capsules_dir, sorted(existing_capsules)[-1])

        self.assertTrue(os.path.exists(archive_path), "Capsule archive must exist")
        self.assertTrue(archive_path.endswith(".tar.gz"))

        # Manifest check
        manifest_path = archive_path.replace(".tar.gz", "_manifest.json")
        self.assertTrue(os.path.exists(manifest_path), "Companion manifest must exist")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = CapsuleManifest.model_validate_json(f.read())

        self.assertGreater(manifest.total_files, 0, "Manifest must track files")
        self.assertGreater(len(manifest.master_sha256), 32, "Master SHA-256 must be present")

        # Master SHA-256 archive check
        actual_archive_hash = CapsuleManifest.calculate_file_sha256(archive_path)
        self.assertEqual(manifest.master_sha256, actual_archive_hash, "Master SHA-256 must match archive exactly")

    def test_bare_metal_resurrection(self):
        """Tests bare-metal cold start resurrection from a DNA capsule."""
        capsules_dir = os.path.join(self.workspace_root, "capsules")
        existing_capsules = [f for f in os.listdir(capsules_dir) if f.endswith(".tar.gz")]
        if not existing_capsules:
            result = self.packager.create_capsule(target_company="Karamstay Enterprise")
            archive_path = result["archive_path"]
        else:
            archive_path = os.path.join(capsules_dir, sorted(existing_capsules)[-1])

        # Perform resurrection into isolated staging directory
        report = self.engine.resurrect_from_capsule(archive_path, restore_destination=self.temp_dest)

        self.assertEqual(report["status"], "RESURRECTED")
        self.assertGreater(report["total_artifacts_restored"], 10)
        self.assertIn("central_hybrid_rag", report["subsystem_health"])
        self.assertEqual(len(report["active_agents_revived"]), 6)

        # Check essential files restored in temp_dest
        self.assertTrue(os.path.exists(os.path.join(self.temp_dest, "agents")), "Agents folder restored")
        self.assertTrue(os.path.exists(os.path.join(self.temp_dest, "dashboard")), "Dashboard folder restored")

        # Verify integrity of all restored files against manifest
        manifest_path = archive_path.replace(".tar.gz", "_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = CapsuleManifest.model_validate_json(f.read())
        is_valid, msg = manifest.verify_integrity(self.temp_dest)
        self.assertTrue(is_valid, f"Restored files integrity verification failed: {msg}")

    def test_tamper_detection(self):
        """Tests that GenesisEngine rejects corrupted or tampered archives."""
        capsules_dir = os.path.join(self.workspace_root, "capsules")
        existing_capsules = [f for f in os.listdir(capsules_dir) if f.endswith(".tar.gz")]
        if not existing_capsules:
            result = self.packager.create_capsule(target_company="Karamstay Enterprise")
            archive_path = result["archive_path"]
        else:
            archive_path = os.path.join(capsules_dir, sorted(existing_capsules)[-1])

        # Create tampered copy
        fake_archive = os.path.join(self.workspace_root, "staging", "corrupted.tar.gz")
        os.makedirs(os.path.dirname(fake_archive), exist_ok=True)
        with open(archive_path, "rb") as f_in:
            data = bytearray(f_in.read(1024))
        # Corrupt bytes
        data[10] ^= 0xFF
        with open(fake_archive, "wb") as f_out:
            f_out.write(data)

        # Copy manifest with expected hash of original
        orig_manifest = archive_path.replace(".tar.gz", "_manifest.json")
        fake_manifest = fake_archive.replace(".tar.gz", "_manifest.json")
        shutil.copy(orig_manifest, fake_manifest)

        with self.assertRaises(ValueError):
            self.engine.resurrect_from_capsule(fake_archive, restore_destination=self.temp_dest)

        # Cleanup
        if os.path.exists(fake_archive):
            os.remove(fake_archive)
        if os.path.exists(fake_manifest):
            os.remove(fake_manifest)


if __name__ == "__main__":
    unittest.main()

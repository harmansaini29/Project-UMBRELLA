"""
Project UMBRELLA: System DNA Capsule Management CLI
Create, verify, and restore company capsules for disaster recovery and long-term preservation.
"""

import argparse
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from capsule.dna_packager import DNAPackager
from capsule.genesis_engine import GenesisEngine


def main():
    parser = argparse.ArgumentParser(description="Manage Project UMBRELLA System DNA Capsules.")
    parser.add_argument("--create", action="store_true", help="Create a new System DNA Capsule")
    parser.add_argument("--restore", type=str, help="Path to capsule archive to resurrect system from 0")
    parser.add_argument("--dest", type=str, default=None, help="Destination directory for restoration")
    args = parser.parse_args()

    print("=" * 80)
    print("PROJECT UMBRELLA: SYSTEM DNA STORAGE CAPSULE & GENESIS ENGINE")
    print("=" * 80)

    if args.create:
        packager = DNAPackager()
        result = packager.create_capsule()
        print("\n[SUCCESS] System DNA Capsule Created!")
        print(f"Capsule ID:       {result['capsule_id']}")
        print(f"Archive:          {result['archive_path']}")
        print(f"Archive Size:     {result['archive_bytes'] / 1024:.1f} KB")
        print(f"Total Artifacts:  {result['total_files']} files")
        print(f"Master SHA-256:   {result['master_sha256']}")
        print(f"Manifest:         {result['manifest_path']}")
        print("\nThis capsule can now be preserved in cold storage (S3 Glacier / On-Prem / Offline Vault).")

    elif args.restore:
        engine = GenesisEngine()
        report = engine.resurrect_from_capsule(archive_path=args.restore, restore_destination=args.dest)
        print("\n[SUCCESS] Bare-Metal Resurrection Complete!")
        print(f"Status:           {report['status']}")
        print(f"Time Taken:       {report['resurrection_time_ms']} ms")
        print(f"Artifacts Revived:{report['total_artifacts_restored']}")
        print(f"Restored Root:    {report['restoration_root']}")
        print("\nSubsystem Health:")
        for k, v in report['subsystem_health'].items():
            print(f"  - {k}: {v.upper()}")
        print("\nRevived Council Agents:")
        for a in report['active_agents_revived']:
            print(f"  [OK] {a}")
        print(f"\n{report['message']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

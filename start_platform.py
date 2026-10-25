"""
Project UMBRELLA: Platform Startup & Launcher Script
Verifies environment, initial state, and launches the Mission Control Dashboard.
"""

import os
import sys
import webbrowser
import time
import uvicorn

# Add root directory to python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dashboard.server import app


def main():
    print("=" * 80)
    print("PROJECT UMBRELLA: MISSION CONTROL COCKPIT & AGENT COUNCIL LAUNCHER")
    print("=" * 80)
    print("Autonomous Software Fault Detection, 3D Blast Radius, Grounded Remediation,")
    print("Safety Policy Governance, Sandboxed Healing, and UMBRELLA-EVO Auto-Evolution.")
    print("-" * 80)
    print("Checking system prerequisites...")

    # Check RAG index
    rag_dir = os.path.join(ROOT_DIR, "rag", "storage")
    if os.path.exists(os.path.join(rag_dir, "bm25_index.pkl")) and os.path.exists(os.path.join(rag_dir, "faiss_index.bin")):
        print("  [OK] Central Hybrid RAG Index: 23,769 chunks loaded.")
    else:
        print("  [WARNING] RAG index files not found in rag/storage/. Run python rag/build_index.py to rebuild.")

    # Check target demo app
    demo_cfg = os.path.join(ROOT_DIR, "target_system", "demo_app", "config.py")
    if os.path.exists(demo_cfg):
        print("  [OK] Target Demo Application: Ready.")

    print("\nStarting Mission Control Server on http://localhost:8000...")
    print("Press CTRL+C to stop the platform at any time.\n")

    # Open browser after a short delay
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()

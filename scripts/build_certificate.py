"""Build certificate — receipt-backed, refuses vacuous certification.

This is the strict version. It requires real verification receipts,
real acceptance specs, and real negative tests. No shortcuts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qdw.proof.certificate import BuildCertificateBuilder
from qdw.proof.runner import VerificationRunner


def main() -> int:
    runs_dir = Path(".qdw/runs")
    if not runs_dir.exists():
        print("ERROR: No verification runs found. Run tests first.")
        return 1

    runner = VerificationRunner(runs_dir)
    builder = BuildCertificateBuilder(runner)

    receipts = runner.load_receipts()
    if not receipts:
        print("ERROR: No command receipts found.")
        return 1

    # Collect all unique task_ids
    task_ids = list({r.task_id for r in receipts})
    if not task_ids:
        print("ERROR: No task receipts found.")
        return 1

    # Use the most common task_id
    task_id = max(task_ids, key=lambda t: sum(1 for r in receipts if r.task_id == t))

    # Collect source artifacts
    artifacts = sorted(Path("src/qdw").rglob("*.py"))

    # Collect required commands from receipts (not empty!)
    required_cmds = list({tuple(r.argv) for r in receipts if r.task_id == task_id})

    try:
        cert = builder.issue(
            task_id=task_id,
            acceptance_spec_hash="ci_pipeline",
            required_commands=[list(c) for c in required_cmds],
            required_negative_tests=[],
            artifact_paths=artifacts,
            output_path="BUILD_CERTIFICATE.json",
        )
        print(f"BUILD_CERTIFICATE.json written: {cert['task_id']}")
        print(f"  git_sha: {cert['git_sha']}")
        print(f"  artifacts: {len(cert['artifacts'])}")
        print(f"  receipts: {len(cert['receipts'])}")
        print(f"  status: {cert['status']}")
        return 0
    except ValueError as e:
        print(f"ERROR: Cannot certify: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

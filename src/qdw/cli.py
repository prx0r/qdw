"""QDW CLI — verification commands."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path


def cmd_verify(args: list[str]) -> int:
    """Run verification gates."""
    from qdw.core.verification.runner import VerificationRunner

    if not args:
        print("Usage: qdw verify <task_id> [command...]")
        return 1

    task_id = args[0]
    commands = args[1:] if len(args) > 1 else None

    base_dir = Path(".qdw/runs")
    runner = VerificationRunner(base_dir, task_id)

    if commands:
        for cmd in commands:
            argv = shlex.split(cmd)
            receipt = runner.run_command(argv)
            print(f"  {'PASS' if receipt.status == 'PASS' else 'FAIL'}: {cmd}")
            if receipt.status == "FAIL":
                print(f"    exit_code={receipt.exit_code}")
                print(f"    stderr: {receipt.stderr_sha256}")

    path = runner.save()
    print(f"\nRun saved: {path}")
    print(f"Status: {runner.status}")
    return 0 if runner.status == "PASS" else 1


def cmd_status(args: list[str]) -> int:
    """Show status of a verification run."""
    if not args:
        print("Usage: qdw status <run_id>")
        return 1

    run_dir = Path(".qdw/runs") / args[0]
    result_path = run_dir / "result.json"
    if not result_path.exists():
        print(f"Run not found: {args[0]}")
        return 1

    result = json.loads(result_path.read_text())
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: qdw <command> [args...]")
        print("Commands: verify, status")
        return 1

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "verify":
        return cmd_verify(args)
    elif command == "status":
        return cmd_status(args)
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Build certificate — refuses to certify without real verification receipts.

This replaces the old source-hash-only script. A valid certificate requires:
- acceptance_spec_hash (frozen before coding)
- verification run with CommandReceipts
- all required commands passed (exit_code == 0)
- all required negative tests behaved correctly
- artifact hashes recompute
- git SHA + dirty state recorded
- ledger root hash
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qdw.core import hash_object, utc_now
from qdw.proof.runner import VerificationRunner


class BuildCertificateBuilder:
    """Issues certificates ONLY from real process receipts. Never from claims."""

    def __init__(self, runner: VerificationRunner):
        self.runner = runner

    def issue(
        self,
        *,
        task_id: str,
        acceptance_spec_hash: str,
        required_commands: list[list[str]],
        required_negative_tests: list[list[str]],
        artifact_paths: list[str | Path],
        ledger_root: str = "",
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Issue a build certificate. Raises ValueError if any gate fails."""
        # 1. Load all receipts for this task
        receipts = [r for r in self.runner.load_receipts() if r.task_id == task_id]
        by_argv = {tuple(r.argv): r for r in receipts}

        # 2. Check required commands all passed
        missing = [cmd for cmd in required_commands if tuple(cmd) not in by_argv]
        failed = [
            list(argv) for argv, r in by_argv.items()
            if r.exit_code != 0 and list(argv) in required_commands
        ]
        if missing or failed:
            raise ValueError(f"cannot certify: missing={missing}, failed={failed}")

        # 3. Check required negative tests
        neg_missing = [cmd for cmd in required_negative_tests if tuple(cmd) not in by_argv]
        neg_not_failed = [
            list(argv) for argv, r in by_argv.items()
            if r.exit_code == 0 and list(argv) in required_negative_tests
        ]
        if neg_missing:
            raise ValueError(f"negative tests not run: {neg_missing}")
        if neg_not_failed:
            raise ValueError(f"negative tests passed when they should have failed: {neg_not_failed}")

        # 4. Hash artifacts
        arts = []
        for p in artifact_paths:
            path = Path(p)
            if not path.exists():
                raise ValueError(f"missing artifact {path}")
            b = path.read_bytes()
            arts.append({"path": str(path), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})

        # 5. Get git state
        git_sha = receipts[0].git_sha if receipts else None
        git_dirty = receipts[0].git_dirty if receipts else None

        # 6. Build certificate
        cert = {
            "status": "PROVEN",
            "task_id": task_id,
            "acceptance_spec_hash": acceptance_spec_hash,
            "issued_at": utc_now(),
            "git_sha": git_sha,
            "git_dirty": git_dirty,
            "ledger_root": ledger_root,
            "required_commands": required_commands,
            "required_negative_tests": required_negative_tests,
            "receipts": [asdict(by_argv[tuple(cmd)]) for cmd in required_commands],
            "negative_test_receipts": [asdict(by_argv[tuple(cmd)]) for cmd in required_negative_tests],
            "artifacts": arts,
        }
        cert["certificate_hash"] = hash_object(cert)

        if output_path:
            Path(output_path).write_text(json.dumps(cert, indent=2), encoding="utf-8")
        return cert

    def verify_certificate(
        self,
        cert_path: str | Path,
        *,
        revalidate: bool = True,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        """Verify a certificate's integrity and optionally revalidate evidence.

        When revalidate=True, re-runs all required commands and required_negative_tests
        from the certificate, then verifies that:
        - commands still pass (exit_code == 0)
        - negative tests still fail (exit_code != 0)
        - artifact hashes still match
        """
        cert = json.loads(Path(cert_path).read_text(encoding="utf-8"))
        stored_hash = cert.pop("certificate_hash", None)
        recomputed = hash_object(cert)
        if stored_hash != recomputed:
            return False, "certificate_hash mismatch"
        if cert.get("status") != "PROVEN":
            return False, f"status is {cert.get('status')}, not PROVEN"

        if not revalidate:
            return True, "ok"

        # Re-run required commands
        required_commands = cert.get("required_commands", [])
        required_negative_tests = cert.get("required_negative_tests", [])
        cwd = cert.get("cwd", ".")

        for cmd in required_commands:
            receipt = self.runner.run(
                task_id=cert.get("task_id", "revalidation"),
                argv=cmd,
                cwd=cwd,
                timeout=timeout,
            )
            if receipt.exit_code != 0:
                return False, f"revalidation failed: command {cmd} returned {receipt.exit_code}"

        for cmd in required_negative_tests:
            receipt = self.runner.run(
                task_id=cert.get("task_id", "revalidation"),
                argv=cmd,
                cwd=cwd,
                timeout=timeout,
            )
            if receipt.exit_code == 0:
                return False, f"revalidation failed: negative test {cmd} passed (expected failure)"

        # Verify artifact hashes still match
        for art in cert.get("artifacts", []):
            path = Path(art["path"])
            if not path.exists():
                return False, f"revalidation failed: artifact {path} no longer exists"
            current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if current_hash != art["sha256"]:
                return False, (
                    f"revalidation failed: artifact {path} hash changed "
                    f"(expected {art['sha256']}, got {current_hash})"
                )

        return True, "ok"

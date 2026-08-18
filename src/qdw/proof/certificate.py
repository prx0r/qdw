"""Build certificate — refuses to certify if required commands failed."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qdw.core import hash_object, utc_now
from qdw.proof.runner import VerificationRunner


class BuildCertificateBuilder:
    def __init__(self, runner: VerificationRunner):
        self.runner = runner

    def build(self, *, task_id: str, required_commands: list[list[str]], acceptance_spec_hash: str,
              artifact_paths: list[str | Path], output_path: str | Path) -> dict[str, Any]:
        receipts = [r for r in self.runner.load_receipts() if r.task_id == task_id]
        by_argv = {tuple(r.argv): r for r in receipts}
        missing = [cmd for cmd in required_commands if tuple(cmd) not in by_argv]
        failed = [list(argv) for argv, r in by_argv.items()
                  if r.exit_code != 0 and list(argv) in required_commands]
        if missing or failed:
            raise ValueError(f"cannot certify: missing={missing}, failed={failed}")
        arts = []
        for p in artifact_paths:
            path = Path(p)
            if not path.exists():
                raise ValueError(f"missing artifact {path}")
            b = path.read_bytes()
            arts.append({"path": str(path), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
        cert = {
            "status": "PROVEN",
            "task_id": task_id,
            "acceptance_spec_hash": acceptance_spec_hash,
            "issued_at": utc_now(),
            "required_commands": required_commands,
            "receipts": [asdict(by_argv[tuple(cmd)]) for cmd in required_commands],
            "artifacts": arts,
        }
        cert["certificate_hash"] = hash_object(cert)
        Path(output_path).write_text(json.dumps(cert, indent=2), encoding="utf-8")
        return cert

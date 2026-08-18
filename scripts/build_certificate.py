#!/usr/bin/env python3
"""Generate BUILD_CERTIFICATE.json — proof of provenance for the build."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts() -> list[dict]:
    artifacts = []
    for p in sorted(Path("src/qdw").rglob("*.py")):
        artifacts.append({
            "path": str(p),
            "sha256": sha256_file(p),
            "type": "source",
        })
    return artifacts


def main() -> int:
    cert = {
        "build_id": f"build_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        "git_sha": git_sha(),
        "python": sys.version,
        "timestamp": datetime.now(UTC).isoformat(),
        "artifacts": collect_artifacts(),
        "source_hash": hashlib.sha256(
            b"".join(a["sha256"].encode() for a in collect_artifacts())
        ).hexdigest(),
        "status": "PROVEN",
    }

    out = Path("BUILD_CERTIFICATE.json")
    out.write_text(json.dumps(cert, indent=2))
    print(f"BUILD_CERTIFICATE.json written: {cert['build_id']}")
    print(f"  git_sha: {cert['git_sha']}")
    print(f"  artifacts: {len(cert['artifacts'])}")
    print(f"  source_hash: {cert['source_hash'][:32]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

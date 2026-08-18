"""Verification runner — typed command receipts, PASS calculated not asserted."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(cwd: Path) -> tuple[str | None, bool | None]:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, text=True, capture_output=True, timeout=5)
        if sha.returncode != 0:
            return None, None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, text=True, capture_output=True, timeout=5)
        return sha.stdout.strip(), bool(dirty.stdout.strip())
    except Exception:
        return None, None


@dataclass(frozen=True)
class CommandReceipt:
    receipt_id: str
    task_id: str
    started_at: str
    finished_at: str
    duration_ms: int
    cwd: str
    argv: tuple[str, ...]
    exit_code: int
    status: str
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str
    git_sha: str | None
    git_dirty: bool | None


class VerificationRunner:
    def __init__(self, runs_dir: str | Path):
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def run(self, task_id: str, argv: Sequence[str], *, cwd: str | Path = ".", timeout: int = 300,
            env: dict[str, str] | None = None) -> CommandReceipt:
        cwdp = Path(cwd).resolve()
        rid = f"receipt_{uuid.uuid4().hex}"
        rdir = self.runs_dir / rid
        rdir.mkdir()
        started = _now()
        t0 = time.monotonic()
        try:
            p = subprocess.run(
                list(argv), cwd=cwdp, capture_output=True, timeout=timeout,
                env=(os.environ | env) if env else None,
            )
            code = p.returncode
            stdout = p.stdout
            stderr = p.stderr
        except subprocess.TimeoutExpired as e:
            code = 124
            stdout = e.stdout or b""
            stderr = e.stderr or b""
            if isinstance(stdout, str):
                stdout = stdout.encode()
            if isinstance(stderr, str):
                stderr = stderr.encode()
        duration = int((time.monotonic() - t0) * 1000)
        finished = _now()
        outp = rdir / "stdout.log"
        errp = rdir / "stderr.log"
        outp.write_bytes(stdout)
        errp.write_bytes(stderr)
        gsha, dirty = _git(cwdp)
        receipt = CommandReceipt(
            rid, task_id, started, finished, duration, str(cwdp), tuple(argv), code,
            "PASS" if code == 0 else "FAIL",
            str(outp), str(errp), _sha(stdout), _sha(stderr), gsha, dirty,
        )
        (rdir / "receipt.json").write_text(json.dumps(asdict(receipt), indent=2), encoding="utf-8")
        with (self.runs_dir / "receipts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(receipt), sort_keys=True) + "\n")
        return receipt

    def load_receipts(self) -> list[CommandReceipt]:
        p = self.runs_dir / "receipts.jsonl"
        if not p.exists():
            return []
        return [CommandReceipt(**json.loads(line)) for line in p.read_text().splitlines() if line.strip()]

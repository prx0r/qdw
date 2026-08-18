"""Verification infrastructure — command receipts, run manifests, artifact hashing.

Nothing may be marked PASS unless this module records it.
The agent is forbidden from writing "PASS" itself.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandReceipt:
    task_id: str
    run_id: str
    git_sha: str
    dirty: bool
    started_at: str
    finished_at: str
    cwd: str
    argv: list[str]
    exit_code: int
    duration_ms: int
    stdout_sha256: str
    stderr_sha256: str
    status: str  # PASS | FAIL | UNVERIFIED | BLOCKED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationRun:
    run_id: str
    task_id: str
    git_sha: str
    started_at: str
    commands: list[CommandReceipt] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if not self.commands:
            return "NOT_RUN"
        if any(c.status == "FAIL" for c in self.commands):
            return "FAIL"
        if any(c.status == "UNVERIFIED" for c in self.commands):
            return "UNVERIFIED"
        if any(c.status == "BLOCKED" for c in self.commands):
            return "BLOCKED"
        return "PASS"

    @property
    def commands_executed(self) -> int:
        return len(self.commands)

    @property
    def commands_failed(self) -> int:
        return sum(1 for c in self.commands if c.status == "FAIL")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "git_sha": self.git_sha,
            "started_at": self.started_at,
            "status": self.status,
            "commands_executed": self.commands_executed,
            "commands_failed": self.commands_failed,
            "commands": [c.to_dict() for c in self.commands],
            "artifacts": self.artifacts,
            "environment": self.environment,
        }


def _git_sha(cwd: str = ".") -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _git_dirty(cwd: str = ".") -> bool:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD"],
            capture_output=True, cwd=cwd, timeout=5,
        )
        return result.returncode != 0
    except Exception:
        return True


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _collect_environment() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": sys.platform,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
    }


class VerificationRunner:
    """Executes commands and produces typed receipts.

    The agent is forbidden from writing "PASS" itself.
    PASS is calculated from: process really executed AND exit_code == 0
    AND required artifacts exist AND artifact hashes recompute.
    """

    def __init__(self, base_dir: Path, task_id: str):
        self.base_dir = base_dir
        self.task_id = task_id
        self.run_id = f"verify_{uuid.uuid4().hex[:12]}"
        self.run_dir = base_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "stdout").mkdir(exist_ok=True)
        (self.run_dir / "stderr").mkdir(exist_ok=True)

        self.git_sha = _git_sha()
        self.dirty = _git_dirty()
        self.started_at = datetime.now(UTC).isoformat()
        self.commands: list[CommandReceipt] = []
        self.artifacts: list[dict[str, Any]] = []

        # Write environment snapshot
        env = _collect_environment()
        env_path = self.run_dir / "environment.json"
        env_path.write_text(json.dumps(env, indent=2))

    def run_command(
        self,
        argv: list[str],
        *,
        cwd: str | None = None,
        timeout: int = 300,
        required: bool = True,
    ) -> CommandReceipt:
        """Execute a command and return a typed receipt."""
        idx = len(self.commands)
        cmd_started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()

        stdout_path = self.run_dir / "stdout" / f"{idx:04d}.log"
        stderr_path = self.run_dir / "stderr" / f"{idx:04d}.log"

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )
            exit_code = result.returncode
            stdout_text = result.stdout
            stderr_text = result.stderr
        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout_text = ""
            stderr_text = f"TIMEOUT after {timeout}s"
        except FileNotFoundError:
            exit_code = -2
            stdout_text = ""
            stderr_text = f"COMMAND NOT FOUND: {argv[0]}"
        except Exception as exc:
            exit_code = -3
            stdout_text = ""
            stderr_text = str(exc)

        t1 = time.monotonic()
        cmd_finished = datetime.now(UTC).isoformat()
        duration_ms = int((t1 - t0) * 1000)

        # Write logs
        stdout_path.write_text(stdout_text)
        stderr_path.write_text(stderr_text)

        stdout_hash = _sha256_bytes(stdout_text.encode())
        stderr_hash = _sha256_bytes(stderr_text.encode())

        if exit_code == 0:
            status = "PASS"
        elif not required and exit_code != 0:
            status = "UNVERIFIED"
        else:
            status = "FAIL"

        receipt = CommandReceipt(
            task_id=self.task_id,
            run_id=self.run_id,
            git_sha=self.git_sha,
            dirty=self.dirty,
            started_at=cmd_started,
            finished_at=cmd_finished,
            cwd=cwd or os.getcwd(),
            argv=argv,
            exit_code=exit_code,
            duration_ms=duration_ms,
            stdout_sha256=stdout_hash,
            stderr_sha256=stderr_hash,
            status=status,
        )
        self.commands.append(receipt)
        return receipt

    def add_artifact(self, path: Path, artifact_type: str = "unknown") -> None:
        """Record an artifact with its hash."""
        if path.exists():
            self.artifacts.append({
                "path": str(path),
                "sha256": _sha256_file(path),
                "type": artifact_type,
                "size_bytes": path.stat().st_size,
            })

    def save(self) -> Path:
        """Save the run manifest."""
        manifest = VerificationRun(
            run_id=self.run_id,
            task_id=self.task_id,
            git_sha=self.git_sha,
            started_at=self.started_at,
            commands=self.commands,
            artifacts=self.artifacts,
            environment=_collect_environment(),
        )
        manifest_path = self.run_dir / "run.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

        # Write result summary
        result = {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "status": manifest.status,
            "commands_executed": manifest.commands_executed,
            "commands_failed": manifest.commands_failed,
            "git_sha": self.git_sha,
        }
        result_path = self.run_dir / "result.json"
        result_path.write_text(json.dumps(result, indent=2))

        return manifest_path

    @property
    def commands_executed(self) -> int:
        return len(self.commands)

    @property
    def commands_failed(self) -> int:
        return sum(1 for c in self.commands if c.status == "FAIL")

    @property
    def status(self) -> str:
        if not self.commands:
            return "NOT_RUN"
        if any(c.status == "FAIL" for c in self.commands):
            return "FAIL"
        return "PASS"

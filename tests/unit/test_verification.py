"""Tests for the verification runner — the anti-hallucination core."""

import json
import sys
from pathlib import Path

import pytest

from qdw.core.verification.acceptance import (
    AcceptanceSpec,
    load_spec,
    save_spec,
)
from qdw.core.verification.runner import VerificationRunner


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    base = tmp_path / ".qdw" / "runs"
    base.mkdir(parents=True)
    return base


class TestCommandReceipt:
    def test_passing_command_produces_pass_receipt(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-001")
        receipt = runner.run_command([sys.executable, "-c", "print('hello')"])
        assert receipt.status == "PASS"
        assert receipt.exit_code == 0
        assert receipt.stdout_sha256 != ""
        assert receipt.stderr_sha256 != ""
        assert receipt.git_sha != ""
        assert receipt.duration_ms >= 0

    def test_failing_command_produces_fail_receipt(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-002")
        receipt = runner.run_command([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert receipt.status == "FAIL"
        assert receipt.exit_code == 1

    def test_nonexistent_command_produces_fail(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-003")
        receipt = runner.run_command(["nonexistent_command_xyz"])
        assert receipt.status == "FAIL"
        assert receipt.exit_code == -2

    def test_stdout_stderr_logged_to_files(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-004")
        cmd = [sys.executable, "-c", "print('out'); print('err', file=__import__('sys').stderr)"]
        runner.run_command(cmd)
        assert len(runner.commands) == 1
        idx = len(runner.commands) - 1
        stdout = (runner.run_dir / "stdout" / f"{idx:04d}.log").read_text()
        stderr = (runner.run_dir / "stderr" / f"{idx:04d}.log").read_text()
        assert "out" in stdout
        assert "err" in stderr

    def test_run_save_produces_manifest(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-005")
        runner.run_command([sys.executable, "-c", "print('ok')"])
        path = runner.save()
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["task_id"] == "TEST-005"
        assert data["status"] == "PASS"
        assert data["commands_executed"] == 1
        assert data["commands_failed"] == 0

    def test_result_json_saved(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-006")
        runner.run_command([sys.executable, "-c", "print('ok')"])
        runner.save()
        result_path = runner.run_dir / "result.json"
        assert result_path.exists()
        result = json.loads(result_path.read_text())
        assert result["status"] == "PASS"

    def test_multiple_commands_aggregate(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-007")
        runner.run_command([sys.executable, "-c", "print('a')"])
        runner.run_command([sys.executable, "-c", "print('b')"])
        assert len(runner.commands) == 2
        assert all(c.status == "PASS" for c in runner.commands)
        assert runner.status == "PASS"

    def test_one_failure_fails_run(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-008")
        runner.run_command([sys.executable, "-c", "print('ok')"])
        runner.run_command([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert sum(1 for c in runner.commands if c.status == "FAIL") == 1
        assert runner.status == "FAIL"


class TestArtifactHashing:
    def test_sha256_file(self, tmp_path: Path) -> None:
        import hashlib
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = hashlib.sha256(b"hello world").hexdigest()
        assert len(h) == 64

    def test_add_artifact(self, run_dir: Path) -> None:
        runner = VerificationRunner(run_dir, "TEST-009")
        artifact = run_dir / "output.txt"
        artifact.write_text("data")
        runner.add_artifact(artifact, "test_output")
        assert len(runner.artifacts) == 1
        assert runner.artifacts[0]["type"] == "test_output"
        assert runner.artifacts[0]["sha256"] != ""


class TestAcceptanceSpec:
    def test_spec_hash_deterministic(self) -> None:
        spec = AcceptanceSpec(
            task_id="OS-001",
            title="Test",
            invariants=["a != b"],
            commands=["pytest tests/"],
        )
        h1 = spec.content_hash()
        h2 = spec.content_hash()
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_spec_save_load_roundtrip(self, tmp_path: Path) -> None:
        spec = AcceptanceSpec(
            task_id="OS-002",
            title="Roundtrip",
            invariants=["x > 0"],
            commands=["python -c 'print(1)'"],
            negative_tests=["concurrent_claim"],
            required_artifacts=["junit.xml"],
        )
        path = tmp_path / "spec.yaml"
        h = save_spec(spec, path)
        assert path.exists()
        loaded = load_spec(path)
        assert loaded.task_id == "OS-002"
        assert loaded.content_hash() == h

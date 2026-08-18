"""Frozen VerificationPlan v2.

This replaces "required commands inferred from whatever receipts exist".
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from qdw.core import hash_object

@dataclass(frozen=True)
class VerificationCommand:
    command_id: str
    argv: tuple[str, ...]
    timeout_seconds: int = 300
    required: bool = True
    expected_exit_code: int = 0

@dataclass(frozen=True)
class VerificationPlan:
    plan_id: str
    version: str
    commands: tuple[VerificationCommand, ...]
    attacks: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    max_mandatory_skips: int = 0
    environment_requirements: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VerificationPlan":
        commands = tuple(
            VerificationCommand(
                command_id=c["id"],
                argv=tuple(c["argv"]),
                timeout_seconds=int(c.get("timeout_seconds", 300)),
                required=bool(c.get("required", True)),
                expected_exit_code=int(c.get("expected_exit_code", 0)),
            )
            for c in d.get("commands", [])
        )
        if not any(c.required for c in commands):
            raise ValueError("verification plan must contain at least one required command")
        ids = [c.command_id for c in commands]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate command IDs")
        return cls(
            plan_id=d["plan_id"],
            version=d["version"],
            commands=commands,
            attacks=tuple(d.get("attacks", ())),
            artifacts=tuple(d.get("artifacts", ())),
            max_mandatory_skips=int(d.get("max_mandatory_skips", 0)),
            environment_requirements=tuple(d.get("environment_requirements", ())),
        )

    @classmethod
    def load(cls, path: str | Path) -> "VerificationPlan":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "version": self.version,
            "commands": [
                {
                    "id": c.command_id,
                    "argv": list(c.argv),
                    "timeout_seconds": c.timeout_seconds,
                    "required": c.required,
                    "expected_exit_code": c.expected_exit_code,
                }
                for c in self.commands
            ],
            "attacks": list(self.attacks),
            "artifacts": list(self.artifacts),
            "max_mandatory_skips": self.max_mandatory_skips,
            "environment_requirements": list(self.environment_requirements),
        }

    @property
    def plan_hash(self) -> str:
        return hash_object(self.to_dict())

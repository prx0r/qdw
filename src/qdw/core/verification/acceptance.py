"""Acceptance specifications — frozen before coding, hashed for integrity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AcceptanceSpec:
    task_id: str
    title: str
    invariants: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    negative_tests: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def content_hash(self) -> str:
        return "sha256:" + hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def load_spec(path: Path) -> AcceptanceSpec:
    """Load an acceptance spec from a YAML file."""
    data = yaml.safe_load(path.read_text())
    return AcceptanceSpec(**data)


def save_spec(spec: AcceptanceSpec, path: Path) -> str:
    """Save an acceptance spec and return its content hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.to_yaml())
    return spec.content_hash()

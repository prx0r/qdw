from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum
from hashlib import sha256
import json
from typing import Any

class Severity(IntEnum):
    INFO = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    CRITICAL = 50

    @classmethod
    def parse(cls, value: str | int | "Severity") -> "Severity":
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        return cls[value.upper()]

@dataclass(frozen=True)
class Evidence:
    kind: str
    path: str | None = None
    line: int | None = None
    detail: str = ""
    sha256: str | None = None
    command_receipt_id: str | None = None

@dataclass
class Finding:
    rule_id: str
    module_id: str
    severity: Severity
    title: str
    summary: str
    invariant: str
    evidence: list[Evidence] = field(default_factory=list)
    remediation: str = ""
    acceptance_tests: list[str] = field(default_factory=list)
    reproduction: list[str] = field(default_factory=list)
    confidence: float = 1.0
    status: str = "OPEN"
    first_seen_sha: str | None = None
    last_seen_sha: str | None = None
    tags: list[str] = field(default_factory=list)
    finding_id: str = ""

    def __post_init__(self) -> None:
        if not self.finding_id:
            basis = {
                "rule_id": self.rule_id,
                "module_id": self.module_id,
                "paths": sorted(e.path or "" for e in self.evidence),
                "title": self.title,
            }
            self.finding_id = "finding_" + sha256(
                json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:20]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.name
        return d

@dataclass
class ModuleResult:
    module_id: str
    version: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "version": self.version,
            "status": self.status,
            "findings": [x.to_dict() for x in self.findings],
            "notes": self.notes,
        }

@dataclass
class ReviewReport:
    schema_version: str
    repo_path: str
    git_sha: str | None
    git_dirty: bool | None
    profile: str
    modules: list[ModuleResult]
    generated_at: str
    receipts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        return [f for m in self.modules for f in m.findings]

    def counts(self) -> dict[str, int]:
        out = {s.name: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.name] += 1
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repo_path": self.repo_path,
            "git_sha": self.git_sha,
            "git_dirty": self.git_dirty,
            "profile": self.profile,
            "generated_at": self.generated_at,
            "counts": self.counts(),
            "modules": [m.to_dict() for m in self.modules],
            "receipts": self.receipts,
        }

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from hashlib import sha256
from typing import Any
import json

class Severity(IntEnum):
    INFO=10
    LOW=20
    MEDIUM=30
    HIGH=40
    CRITICAL=50

    @classmethod
    def parse(cls,value:str|int|"Severity")->"Severity":
        if isinstance(value,cls): return value
        if isinstance(value,int): return cls(value)
        return cls[value.upper()]

@dataclass(frozen=True)
class SubjectSnapshot:
    repo_path:str
    git_sha:str|None
    dirty:bool|None
    changed_paths:tuple[str,...]=()

@dataclass(frozen=True)
class Evidence:
    kind:str
    path:str|None=None
    line:int|None=None
    detail:str=""
    content_sha256:str|None=None
    receipt_id:str|None=None
    artifact_id:str|None=None

@dataclass
class Finding:
    rule_id:str
    module_id:str
    severity:Severity
    title:str
    summary:str
    invariant:str
    evidence:list[Evidence]=field(default_factory=list)
    remediation:str=""
    acceptance_tests:list[str]=field(default_factory=list)
    reproduction:list[str]=field(default_factory=list)
    confidence:float=1.0
    status:str="OPEN"
    fingerprint:str=""

    def __post_init__(self):
        if not self.fingerprint:
            basis={
                "rule_id":self.rule_id,
                "module_id":self.module_id,
                "paths":sorted(e.path or "" for e in self.evidence),
            }
            self.fingerprint=sha256(
                json.dumps(basis,sort_keys=True,separators=(",",":")).encode()
            ).hexdigest()

    @property
    def finding_id(self)->str:
        return "finding_"+self.fingerprint[:20]

    def to_dict(self)->dict[str,Any]:
        d=asdict(self)
        d["finding_id"]=self.finding_id
        d["severity"]=self.severity.name
        return d

@dataclass
class ModuleResult:
    module_id:str
    version:str
    findings:list[Finding]=field(default_factory=list)
    notes:list[str]=field(default_factory=list)

    @property
    def status(self)->str:
        return "FAIL" if any(x.severity>=Severity.HIGH and x.status=="OPEN" for x in self.findings) else "PASS"

    def to_dict(self)->dict[str,Any]:
        return {
            "module_id":self.module_id,
            "version":self.version,
            "status":self.status,
            "findings":[x.to_dict() for x in self.findings],
            "notes":self.notes,
        }

@dataclass
class ReviewReport:
    schema_version:str
    subject:SubjectSnapshot
    profile:str
    modules:list[ModuleResult]
    generated_at:str
    receipts:list[dict[str,Any]]=field(default_factory=list)
    attacks:list[dict[str,Any]]=field(default_factory=list)

    @property
    def findings(self)->list[Finding]:
        return [f for m in self.modules for f in m.findings]

    def counts(self)->dict[str,int]:
        return {s.name:sum(1 for f in self.findings if f.severity==s) for s in Severity}

    def blocker_fingerprints(self,threshold:Severity=Severity.HIGH)->tuple[str,...]:
        return tuple(sorted(
            f.fingerprint for f in self.findings
            if f.status=="OPEN" and f.severity>=threshold
        ))

    def to_dict(self)->dict[str,Any]:
        return {
            "schema_version":self.schema_version,
            "subject":asdict(self.subject),
            "profile":self.profile,
            "generated_at":self.generated_at,
            "counts":self.counts(),
            "modules":[m.to_dict() for m in self.modules],
            "receipts":self.receipts,
            "attacks":self.attacks,
        }

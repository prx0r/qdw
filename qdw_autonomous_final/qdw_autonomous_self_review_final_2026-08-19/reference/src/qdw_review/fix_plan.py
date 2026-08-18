from __future__ import annotations
from dataclasses import asdict,dataclass
from hashlib import sha256
import json
from .models import Finding,Severity

@dataclass(frozen=True)
class FixTask:
    task_id:str
    title:str
    finding_ids:tuple[str,...]
    module_ids:tuple[str,...]
    severity:str
    acceptance_tests:tuple[str,...]
    acceptance_hash:str
    expected_paths:tuple[str,...]
    depends_on:tuple[str,...]=()

def build_fix_tasks(findings:list[Finding])->list[FixTask]:
    blockers=[f for f in findings if f.status=="OPEN" and f.severity>=Severity.HIGH]
    groups={}
    for f in blockers:
        path=(f.evidence[0].path if f.evidence else "unknown") or "unknown"
        subsystem=path.split("/")[2] if path.startswith("src/qdw/") and len(path.split("/"))>2 else path.split("/")[0]
        groups.setdefault(subsystem,[]).append(f)
    out=[]
    for idx,(subsystem,fs) in enumerate(sorted(groups.items())):
        tests=tuple(dict.fromkeys(t for f in fs for t in f.acceptance_tests))
        basis={"findings":[f.finding_id for f in fs],"tests":tests}
        ah=sha256(json.dumps(basis,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        paths=tuple(sorted({e.path for f in fs for e in f.evidence if e.path}))
        out.append(FixTask(
            f"review-fix-{idx+1:03d}-{subsystem.replace('.','-')}",
            f"Repair {subsystem} review blockers",
            tuple(f.finding_id for f in fs),
            tuple(sorted({f.module_id for f in fs})),
            max((f.severity for f in fs)).name,
            tests,ah,paths,
        ))
    return out

def to_dict(tasks):
    return [asdict(x) for x in tasks]

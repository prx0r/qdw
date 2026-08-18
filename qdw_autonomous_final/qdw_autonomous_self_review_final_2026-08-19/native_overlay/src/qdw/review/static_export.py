from __future__ import annotations
from dataclasses import asdict
from datetime import UTC,datetime
from pathlib import Path
import json,subprocess
from .static_engine import StaticRuleEngine
from .static_rules import ALL_RULES

def _git(root:Path):
    p=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True)
    sha=p.stdout.strip() if p.returncode==0 else None
    dirty=bool(subprocess.run(["git","status","--porcelain"],cwd=root,capture_output=True,text=True).stdout.strip()) if sha else None
    return sha,dirty

def build_static_report(repo_root:str|Path,profile:str)->dict:
    root=Path(repo_root).resolve()
    result=StaticRuleEngine(ALL_RULES).run(root)
    sha,dirty=_git(root)
    findings=[]
    for f in result.findings:
        findings.append({
            "finding_id":"finding_"+__import__("hashlib").sha256(
                (f.rule_id+"|"+result.reviewer_id+"|"+",".join(str(e.get("path","")) for e in f.evidence)).encode()
            ).hexdigest()[:20],
            "rule_id":f.rule_id,"module_id":result.reviewer_id,"severity":f.severity,
            "title":f.title,"summary":f.summary,"invariant":f.invariant,
            "remediation":f.remediation,"evidence":list(f.evidence),
            "acceptance_tests":list(f.acceptance_tests),
            "acceptance_specs":list(f.acceptance_specs),
            "confidence":f.confidence,"status":"OPEN",
        })
    counts={s:sum(1 for f in findings if f["severity"]==s) for s in ("CRITICAL","HIGH","MEDIUM","LOW","INFO")}
    return {
        "schema_version":"qdw.review.static.v2",
        "subject":{"repo_path":str(root),"git_sha":sha,"dirty":dirty,"changed_paths":[]},
        "profile":profile,"generated_at":datetime.now(UTC).isoformat().replace("+00:00","Z"),
        "counts":counts,
        "modules":[{
            "module_id":result.reviewer_id,"version":result.reviewer_version,
            "status":"FAIL" if counts["CRITICAL"] or counts["HIGH"] else "PASS",
            "findings":findings,"notes":[result.summary],
        }],
        "receipts":[],"attacks":[],
    }

def write_static_report(repo_root,profile,out_dir):
    from pathlib import Path
    from json import dumps
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    report=build_static_report(repo_root,profile)
    (out/"REVIEW.json").write_text(dumps(report,indent=2),encoding="utf-8")
    from .render import html,sarif
    (out/"REPORT.html").write_text(html(report),encoding="utf-8")
    (out/"REVIEW.sarif").write_text(dumps(sarif(report),indent=2),encoding="utf-8")
    return report

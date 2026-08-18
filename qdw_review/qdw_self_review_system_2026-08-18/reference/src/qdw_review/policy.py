from __future__ import annotations
import json
from pathlib import Path
from qdw_review.models import Severity

def evaluate(report:dict,policy:dict)->dict:
    blockers=[]
    threshold=Severity.parse(policy.get("block_at","HIGH"))
    allowed=set(policy.get("allowed_rule_ids",[]))
    for module in report.get("modules",[]):
        for f in module.get("findings",[]):
            if f["rule_id"] in allowed:continue
            if Severity.parse(f["severity"]) >= threshold and f.get("status","OPEN")=="OPEN":
                blockers.append(f)
    required=set(policy.get("required_modules",[]))
    ran={m["module_id"] for m in report.get("modules",[])}
    missing=sorted(required-ran)
    required_receipts=policy.get("minimum_passing_receipts",0)
    passing=sum(1 for r in report.get("receipts",[]) if r.get("status")=="PASS")
    return {
        "status":"PASS" if not blockers and not missing and passing>=required_receipts else "FAIL",
        "blockers":blockers,
        "missing_modules":missing,
        "passing_receipts":passing,
        "minimum_passing_receipts":required_receipts,
    }

def load_policy(path:str|Path)->dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

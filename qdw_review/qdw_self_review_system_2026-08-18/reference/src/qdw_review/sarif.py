from __future__ import annotations

def to_sarif(report:dict)->dict:
    results=[];rules={}
    for m in report.get("modules",[]):
        for f in m.get("findings",[]):
            rid=f["rule_id"]
            rules[rid]={"id":rid,"name":f["title"],"shortDescription":{"text":f["summary"]}}
            ev=(f.get("evidence") or [{}])[0]
            location={}
            if ev.get("path"):
                location={"physicalLocation":{
                    "artifactLocation":{"uri":ev["path"]},
                    "region":{"startLine":ev.get("line") or 1}
                }}
            level={"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note","INFO":"note"}[f["severity"]]
            results.append({"ruleId":rid,"level":level,"message":{"text":f["summary"]},
                            "locations":[location] if location else []})
    return {"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",
            "runs":[{"tool":{"driver":{"name":"qdw-review","rules":list(rules.values())}},"results":results}]}

from __future__ import annotations
import json

def sarif(report:dict)->dict:
    rules={};results=[]
    for module in report.get("modules",[]):
        for finding in module.get("findings",[]):
            rid=finding["rule_id"]
            rules[rid]={"id":rid,"name":finding["title"],
                        "shortDescription":{"text":finding["summary"]}}
            evidence=finding.get("evidence",[])
            locations=[]
            if evidence and evidence[0].get("path"):
                locations=[{"physicalLocation":{
                    "artifactLocation":{"uri":evidence[0]["path"]},
                    "region":{"startLine":evidence[0].get("line") or 1}
                }}]
            level={"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note","INFO":"note"}[finding["severity"]]
            results.append({"ruleId":rid,"level":level,
                            "message":{"text":finding["summary"]},"locations":locations})
    return {
        "version":"2.1.0",
        "$schema":"https://json.schemastore.org/sarif-2.1.0.json",
        "runs":[{"tool":{"driver":{"name":"QDW Review","rules":list(rules.values())}},
                 "results":results}],
    }

def html(report:dict)->str:
    payload=json.dumps(report).replace("</","<\\/")
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<title>QDW Review</title><style>
body{{font-family:system-ui;background:#0f1115;color:#eee;margin:0}}
header{{position:sticky;top:0;background:#0f1115;padding:16px;border-bottom:1px solid #333}}
main{{max-width:1400px;margin:auto;padding:18px}}
.finding{{border:1px solid #333;border-radius:10px;padding:14px;margin:10px 0}}
.CRITICAL{{border-left:6px solid #ff453a}} .HIGH{{border-left:6px solid #ff9f0a}}
.MEDIUM{{border-left:6px solid #ffd60a}} .LOW{{border-left:6px solid #64d2ff}} .INFO{{border-left:6px solid #8e8e93}}
input,select{{background:#1c1e24;color:#fff;border:1px solid #555;padding:7px;margin:3px}}
code{{background:#222;padding:2px 4px}}
</style></head><body><header><b>QDW Review</b> <span id='sha'></span>
<input id='q' placeholder='filter'><select id='sev'><option value=''>all severity</option>
<option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>INFO</option>
</select></header><main><div id='summary'></div><div id='items'></div></main>
<script>
const R={payload}; const F=R.modules.flatMap(m=>m.findings.map(f=>({{...f,module_id:m.module_id}})));
sha.textContent=' @ '+((R.subject&&R.subject.git_sha)||'unknown').slice(0,12);
summary.textContent=Object.entries(R.counts||{{}}).map(([k,v])=>k+':'+v).join('  ');
function draw(){{let query=q.value.toLowerCase(),s=sev.value;items.innerHTML='';
F.filter(f=>(!s||f.severity===s)&&(!query||JSON.stringify(f).toLowerCase().includes(query))).forEach(f=>{{
let d=document.createElement('div');d.className='finding '+f.severity;
d.innerHTML=`<b>${{f.severity}} · ${{f.rule_id}}</b> <small>${{f.module_id}}</small><h3>${{f.title}}</h3>
<p>${{f.summary}}</p><p><b>Invariant:</b> ${{f.invariant}}</p><p><b>Remediation:</b> ${{f.remediation}}</p>
<details><summary>Evidence / acceptance</summary>${{(f.evidence||[]).map(e=>`<div><code>${{e.path||e.kind}}</code> — ${{e.detail||''}}</div>`).join('')}}
<ul>${{(f.acceptance_tests||[]).map(x=>`<li>${{x}}</li>`).join('')}}</ul></details>`;
items.appendChild(d);}});}}
q.oninput=draw;sev.onchange=draw;draw();
</script></body></html>"""

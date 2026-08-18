from __future__ import annotations
from pathlib import Path
import json

def sarif(report:dict)->dict:
    rules={};results=[]
    for module in report.get("modules",[]):
        for f in module.get("findings",[]):
            rid=f["rule_id"]
            rules[rid]={"id":rid,"name":f["title"],"shortDescription":{"text":f["summary"]}}
            evs=f.get("evidence",[])
            locs=[]
            if evs and evs[0].get("path"):
                locs=[{"physicalLocation":{"artifactLocation":{"uri":evs[0]["path"]},
                    "region":{"startLine":evs[0].get("line") or 1}}}]
            level={"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note","INFO":"note"}[f["severity"]]
            results.append({"ruleId":rid,"level":level,"message":{"text":f["summary"]},"locations":locs})
    return {"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",
            "runs":[{"tool":{"driver":{"name":"qdw-review","rules":list(rules.values())}},"results":results}]}

def html(report:dict)->str:
    data=json.dumps(report).replace("</","<\\/")
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>QDW Autonomous Review</title>
<style>
body{{font-family:system-ui;margin:0;background:#101114;color:#eee}}
header{{position:sticky;top:0;background:#101114;border-bottom:1px solid #333;padding:16px 22px;z-index:3}}
main{{max-width:1400px;margin:auto;padding:20px}}
.finding{{border:1px solid #333;border-radius:10px;padding:14px;margin:10px 0}}
.CRITICAL{{border-left:6px solid #ff453a}}.HIGH{{border-left:6px solid #ff9f0a}}
.MEDIUM{{border-left:6px solid #ffd60a}}.LOW{{border-left:6px solid #64d2ff}}.INFO{{border-left:6px solid #8e8e93}}
input,select{{background:#1d1f24;color:#fff;border:1px solid #555;padding:7px;margin:3px}}
.meta{{opacity:.65}} code{{background:#222;padding:2px 4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}}
.card{{background:#191b20;padding:10px;border-radius:8px}}
</style></head><body><header><b>QDW Autonomous Review</b> <span id="sha"></span><br>
<input id="q" placeholder="filter"><select id="sev"><option value="">all severity</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>INFO</option></select>
<select id="mod"><option value="">all modules</option></select></header>
<main><div id="summary" class="grid"></div><div id="items"></div></main>
<script>
const report={data};
const F=report.modules.flatMap(m=>m.findings.map(f=>({{...f,module_id:m.module_id}})));
sha.textContent=" @ "+((report.subject&&report.subject.git_sha)||report.git_sha||"unknown").slice(0,12);
Object.entries(report.counts||{{}}).forEach(([k,v])=>{{let d=document.createElement("div");d.className="card";d.textContent=k+": "+v;summary.appendChild(d)}});
[...new Set(F.map(x=>x.module_id))].sort().forEach(x=>{{let o=document.createElement("option");o.textContent=x;mod.appendChild(o)}});
function draw(){{
 let query=q.value.toLowerCase(), s=sev.value, m=mod.value;items.innerHTML="";
 F.filter(f=>(!s||f.severity===s)&&(!m||f.module_id===m)&&(!query||JSON.stringify(f).toLowerCase().includes(query))).forEach(f=>{{
  let d=document.createElement("div");d.className="finding "+f.severity;
  d.innerHTML=`<b>${{f.severity}} · ${{f.rule_id}}</b> <span class=meta>${{f.module_id}}</span><h3>${{f.title}}</h3>
  <p>${{f.summary}}</p><p><b>Invariant:</b> ${{f.invariant}}</p><p><b>Remediation:</b> ${{f.remediation}}</p>
  <details><summary>Evidence + acceptance</summary>${{(f.evidence||[]).map(e=>`<div><code>${{e.path||e.kind}}</code> — ${{e.detail||""}}</div>`).join("")}}
  <ul>${{(f.acceptance_tests||[]).map(x=>`<li>${{x}}</li>`).join("")}}</ul></details>`;
  items.appendChild(d);
 }});
}}
q.oninput=draw;sev.onchange=draw;mod.onchange=draw;draw();
</script></body></html>'''

def write_outputs(report:dict,json_path,html_path,sarif_path):
    Path(json_path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    Path(html_path).write_text(html(report),encoding="utf-8")
    Path(sarif_path).write_text(json.dumps(sarif(report),indent=2),encoding="utf-8")

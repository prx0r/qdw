from __future__ import annotations
import html, json
from pathlib import Path

def render(report:dict)->str:
    data=json.dumps(report).replace("</","<\\/")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>QDW Review</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}}
header{{padding:18px 24px;border-bottom:1px solid #333;position:sticky;top:0;background:#111;z-index:2}}
main{{padding:20px;max-width:1300px;margin:auto}}
.filters button{{margin:3px;padding:7px 10px}} .finding{{border:1px solid #333;border-radius:10px;padding:14px;margin:10px 0}}
.CRITICAL{{border-left:6px solid #ff3b30}} .HIGH{{border-left:6px solid #ff9500}}
.MEDIUM{{border-left:6px solid #ffd60a}} .LOW{{border-left:6px solid #64d2ff}} .INFO{{border-left:6px solid #8e8e93}}
code,pre{{background:#1d1d1f;padding:2px 5px;border-radius:4px}} .meta{{opacity:.7}} .evidence{{font-family:ui-monospace,monospace}}
.hidden{{display:none}} select,input{{padding:7px;margin:3px;background:#222;color:#eee;border:1px solid #555}}
</style></head>
<body><header><b>QDW Self Review</b> <span id="sha"></span>
<div class="filters">
<input id="q" placeholder="filter findings">
<select id="sev"><option value="">all severities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>INFO</option></select>
<select id="mod"><option value="">all modules</option></select>
</div></header><main><div id="summary"></div><div id="findings"></div></main>
<script>
const report={data}; const findings=report.modules.flatMap(m=>m.findings.map(f=>({{...f,module_id:m.module_id}})));
sha.textContent=report.git_sha?(" @ "+report.git_sha.slice(0,12)):"";
summary.textContent=`${{findings.length}} findings — `+Object.entries(report.counts||{{}}).map(([k,v])=>`${{k}}:${{v}}`).join("  ");
[...new Set(findings.map(x=>x.module_id))].sort().forEach(x=>{{let o=document.createElement("option");o.textContent=x;mod.appendChild(o)}});
function draw(){{
 let query=q.value.toLowerCase(), s=sev.value, m=mod.value; findings.innerHTML="";
 findings.filter(f=>(!s||f.severity===s)&&(!m||f.module_id===m)&&(!query||JSON.stringify(f).toLowerCase().includes(query))).forEach(f=>{{
  let d=document.createElement("div");d.className="finding "+f.severity;
  d.innerHTML=`<b>${{f.severity}} · ${{f.rule_id}}</b> <span class=meta>${{f.module_id}}</span><h3>${{f.title}}</h3><p>${{f.summary}}</p>
  <p><b>Invariant:</b> ${{f.invariant}}</p><p><b>Remediation:</b> ${{f.remediation}}</p>
  <details><summary>Evidence / acceptance</summary><div class=evidence>${{(f.evidence||[]).map(e=>`<div>${{e.path||e.kind}} — ${{e.detail||""}}</div>`).join("")}}</div>
  <ul>${{(f.acceptance_tests||[]).map(x=>`<li>${{x}}</li>`).join("")}}</ul></details>`;
  findings.appendChild(d);
 }});
}}
q.oninput=draw;sev.onchange=draw;mod.onchange=draw;draw();
</script></body></html>"""

def write_html(report:dict,path:str|Path)->None:
    Path(path).write_text(render(report),encoding="utf-8")

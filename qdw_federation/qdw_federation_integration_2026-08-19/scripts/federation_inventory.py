from __future__ import annotations
import argparse,json,re,subprocess
from pathlib import Path

TOKENS={
 "scheduler":["claim_ready","scheduler","route_task","Router"],
 "verification":["certificate","verify","verification"],
 "database":["sqlite","Database(","connect("],
 "api":["FastAPI","@app.","APIRouter"],
 "mcp":["mcp","MCP"],
}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default="worktrees");a=ap.parse_args()
    root=Path(a.root);out={}
    for repo in ["qdw","qdw-forge","qdw-sandbox","gitgoblin","dell"]:
        r=root/repo;rows={k:[] for k in TOKENS}
        for p in r.rglob("*.py"):
            if any(x in p.parts for x in {".venv","venv","site-packages"}):continue
            try:t=p.read_text(errors="replace")
            except Exception:continue
            for kind,needles in TOKENS.items():
                if any(n.lower() in t.lower() for n in needles):
                    rows[kind].append(str(p.relative_to(r)))
        out[repo]={k:v[:100] for k,v in rows.items()}
    print(json.dumps(out,indent=2))

if __name__=="__main__":main()

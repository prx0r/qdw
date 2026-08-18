from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
EXPECTED={
 "qdw":"46920f2547e552b7f1c0e019169a350fe44cb4c1",
 "qdw-forge":"2037cdb93458278bdc4807be8e84111cce72fb10",
 "qdw-sandbox":"5e4278c8eeed008bcf11deff288b19110379ece0",
 "gitgoblin":"c129f801b601af8e088d6fe908f01f769a62b0ee",
 "dell":"f29ed2a9621d307d301c628aa6f00de9d356d5ce",
}
def git(d,*args):
    p=subprocess.run(["git",*args],cwd=d,capture_output=True,text=True,timeout=20)
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="worktrees"); a=ap.parse_args()
    root=Path(a.root); rows=[]; bad=[]
    for name,expected in EXPECTED.items():
        d=root/name
        if not (d/".git").exists(): bad.append(f"{name}:missing"); continue
        actual=git(d,"rev-parse","HEAD"); dirty=bool(git(d,"status","--porcelain"))
        rows.append({"repo":name,"expected":expected,"actual":actual,"dirty":dirty})
        if actual!=expected: bad.append(f"{name}:sha")
        if dirty: bad.append(f"{name}:dirty-before-integration")
    print(json.dumps({"rows":rows,"failures":bad},indent=2))
    raise SystemExit(1 if bad else 0)
if __name__=="__main__": main()

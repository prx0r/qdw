from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path

def git(cwd,*args):
    p=subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default="worktrees");ap.add_argument("--pins",default="pins/REPOS.json")
    a=ap.parse_args();root=Path(a.root);pins=json.loads(Path(a.pins).read_text())
    failures=[];rows=[]
    for name,pin in pins.items():
        d=root/name
        if not (d/".git").exists():
            failures.append(f"{name}: missing checkout");continue
        sha=git(d,"rev-parse","HEAD");dirty=bool(git(d,"status","--porcelain"))
        row={"name":name,"expected":pin["sha"],"actual":sha,"dirty":dirty}
        rows.append(row)
        if sha!=pin["sha"]:failures.append(f"{name}: SHA {sha} != {pin['sha']}")
    print(json.dumps({"checkouts":rows,"failures":failures},indent=2))
    raise SystemExit(1 if failures else 0)

if __name__=="__main__":main()

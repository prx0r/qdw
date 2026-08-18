from __future__ import annotations
import argparse,json,subprocess,tempfile,os
from pathlib import Path
from protocol_surface import public_python_surface,routes

def git(repo,*args):
    p=subprocess.run(["git",*args],cwd=repo,text=True,capture_output=True,timeout=30)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()

def snapshot(repo:Path,ref:str)->dict:
    current=git(repo,"rev-parse","HEAD")
    dirty=git(repo,"status","--porcelain")
    if dirty:raise RuntimeError("pin upgrade report requires clean checkout")
    git(repo,"checkout","--detach",ref)
    try:return {"sha":git(repo,"rev-parse","HEAD"),"python":public_python_surface(repo),"routes":routes(repo)}
    finally:git(repo,"checkout","--detach",current)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("repo");ap.add_argument("old");ap.add_argument("new");ap.add_argument("--out",required=True)
    a=ap.parse_args();r=Path(a.repo)
    old=snapshot(r,a.old);new=snapshot(r,a.new)
    old_routes={(x["method"],x["route"]) for x in old["routes"]}
    new_routes={(x["method"],x["route"]) for x in new["routes"]}
    result={
      "old_sha":old["sha"],"new_sha":new["sha"],
      "routes_added":sorted(new_routes-old_routes),"routes_removed":sorted(old_routes-new_routes),
      "python_files_added":sorted(set(new["python"])-set(old["python"])),
      "python_files_removed":sorted(set(old["python"])-set(new["python"])),
      "requires_full_federation_suite":True,
    }
    Path(a.out).write_text(json.dumps(result,indent=2))

if __name__=="__main__":main()

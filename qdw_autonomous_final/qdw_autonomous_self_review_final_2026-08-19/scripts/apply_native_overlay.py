#!/usr/bin/env python3
"""Apply the final QDW autonomous-review overlay to a QDW checkout.

Safety:
- dry-run by default;
- refuses a dirty checkout unless --allow-dirty;
- can require an expected starting SHA;
- never pushes/merges;
- copies only new overlay files, migrations and explicit replacements.
"""
from __future__ import annotations
from pathlib import Path
import argparse, shutil, subprocess, json, hashlib, sys

PACK=Path(__file__).resolve().parents[1]
EXPECTED="ab809c8e6b829374199eb49dc71cd6f499e4f7fb"

def git(repo:Path,*args:str)->str:
    p=subprocess.run(["git",*args],cwd=repo,text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.strip() or "git failed")
    return p.stdout.strip()

def copy_plan(repo:Path):
    pairs=[]
    for base in [PACK/"native_overlay/src",PACK/"native_overlay/migrations",PACK/"native_overlay/tests"]:
        for src in base.rglob("*"):
            if src.is_file() and "__pycache__" not in src.parts:
                if base.name=="src": rel=Path("src")/src.relative_to(base)
                elif base.name=="migrations": rel=Path("migrations")/src.name
                else: rel=Path("tests")/src.relative_to(base)
                pairs.append((src,repo/rel))
    rep=PACK/"native_overlay/replacements"
    for src in rep.rglob("*"):
        if src.is_file() and "__pycache__" not in src.parts:
            pairs.append((src,repo/src.relative_to(rep)))
    # manifests/prompts/formulas/policies/attacks/acceptance are runtime assets too
    for dirname in ["manifests","prompts","policies","attacks","acceptance"]:
        base=PACK/dirname
        for src in base.rglob("*"):
            if src.is_file():pairs.append((src,repo/src.relative_to(PACK)))
    return sorted(pairs,key=lambda x:str(x[1]))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--apply",action="store_true",help="actually copy files; default is dry-run")
    ap.add_argument("--allow-dirty",action="store_true")
    ap.add_argument("--expected-sha",default=EXPECTED)
    args=ap.parse_args()
    repo=Path(args.repo).resolve()
    if not (repo/"pyproject.toml").exists() or not (repo/"src/qdw").exists():
        raise SystemExit("not a QDW checkout")
    sha=git(repo,"rev-parse","HEAD")
    dirty=bool(git(repo,"status","--porcelain"))
    if args.expected_sha and sha!=args.expected_sha:
        raise SystemExit(f"starting SHA mismatch: expected {args.expected_sha}, got {sha}; re-peer-review before blind apply")
    if dirty and not args.allow_dirty:raise SystemExit("checkout is dirty")
    plan=copy_plan(repo)
    changed=[]
    for src,dst in plan:
        sb=src.read_bytes(); before=dst.read_bytes() if dst.exists() else None
        if before==sb:continue
        changed.append({"path":str(dst.relative_to(repo)),"operation":"replace" if dst.exists() else "create",
                        "sha256":hashlib.sha256(sb).hexdigest()})
        if args.apply:
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    print(json.dumps({"subject_sha":sha,"dirty":dirty,"mode":"APPLY" if args.apply else "DRY_RUN",
                      "changed_files":changed,"count":len(changed)},indent=2))
    if args.apply:
        print("Overlay applied locally. Run frozen acceptance/failing-before tests before committing; never push automatically.")

if __name__=="__main__":main()

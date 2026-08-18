from __future__ import annotations
import argparse,shutil
from pathlib import Path

MAPPINGS=[
 ("native/qdw/migrations","qdw/migrations"),
 ("native/qdw/src/qdw/federation","qdw/src/qdw/federation"),
 ("cross_repo_patches/qdw-forge/src","qdw-forge/src"),
 ("cross_repo_patches/qdw-forge/tests","qdw-forge/tests"),
 ("cross_repo_patches/gitgoblin/gitgoblin","gitgoblin/gitgoblin"),
 ("cross_repo_patches/gitgoblin/tests","gitgoblin/tests"),
 ("cross_repo_patches/dell/app","dell/app"),
 ("cross_repo_patches/dell/tests","dell/tests"),
 ("cross_repo_patches/qdw-sandbox/src","qdw-sandbox/src"),
 ("cross_repo_patches/qdw-sandbox/tests","qdw-sandbox/tests"),
]

def copy_tree(src:Path,dst:Path,apply:bool):
    for p in src.rglob("*"):
        if not p.is_file():continue
        rel=p.relative_to(src);target=dst/rel
        action="CREATE" if not target.exists() else "OVERWRITE"
        print(f"{action:9} {target}")
        if apply:
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pack-root",default=".")
    ap.add_argument("--worktrees",default="worktrees")
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args();pack=Path(a.pack_root).resolve();work=Path(a.worktrees).resolve()
    for s,d in MAPPINGS:
        src=pack/s;dst=work/d
        if src.exists():copy_tree(src,dst,a.apply)
    if not a.apply:print("\\nDRY RUN ONLY. Re-run with --apply after reviewing paths.")

if __name__=="__main__":main()

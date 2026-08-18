from __future__ import annotations
import argparse,shutil
from pathlib import Path
REPOS=("qdw","qdw-forge","qdw-sandbox","gitgoblin","dell")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pack-root",default=".")
    ap.add_argument("--worktrees",default="worktrees")
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args(); pack=Path(a.pack_root).resolve(); work=Path(a.worktrees).resolve()
    for repo in REPOS:
        src=pack/"overlays"/repo; dst=work/repo
        if not src.exists(): continue
        for p in sorted(src.rglob("*")):
            if not p.is_file() or p.name=="INTEGRATE.md": continue
            rel=p.relative_to(src); target=dst/rel
            action="CREATE" if not target.exists() else "REPLACE"
            print(f"{action:8} {repo}/{rel}")
            if a.apply:
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,target)
    if not a.apply:
        print("DRY RUN: no files written. Use --apply after baseline evidence is frozen.")
if __name__=="__main__": main()

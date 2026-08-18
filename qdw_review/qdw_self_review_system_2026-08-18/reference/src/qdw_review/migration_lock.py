from __future__ import annotations
from pathlib import Path
import json
from qdw_review.repo import Repo

def create_lock(repo_path:str|Path,out_path:str|Path)->dict:
    repo=Repo(repo_path)
    files={}
    for p in repo.glob("migrations/*.sql"):
        rel=repo.rel(p);files[rel]=repo.file_hash(rel)
    data={"git_sha":repo.git_sha(),"files":files}
    out=Path(out_path);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(data,indent=2),encoding="utf-8")
    return data

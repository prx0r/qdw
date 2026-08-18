from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import subprocess

class Repo:
    def __init__(self,root:str|Path):
        self.root=Path(root).resolve()

    def path(self,rel:str|Path)->Path:
        return self.root/rel

    def exists(self,rel:str|Path)->bool:
        return self.path(rel).exists()

    def read(self,rel:str|Path,default:str="")->str:
        p=self.path(rel)
        if not p.exists() or not p.is_file(): return default
        return p.read_text(encoding="utf-8",errors="replace")

    def rglob(self,pattern:str):
        return sorted(self.root.rglob(pattern))

    def glob(self,pattern:str):
        return sorted(self.root.glob(pattern))

    def rel(self,p:Path)->str:
        return str(p.resolve().relative_to(self.root))

    def digest(self,rel:str|Path)->str|None:
        p=self.path(rel)
        return sha256(p.read_bytes()).hexdigest() if p.exists() and p.is_file() else None

    def git_sha(self)->str|None:
        try:
            p=subprocess.run(["git","rev-parse","HEAD"],cwd=self.root,capture_output=True,text=True,timeout=5)
            return p.stdout.strip() if p.returncode==0 else None
        except Exception:return None

    def dirty(self)->bool|None:
        try:
            p=subprocess.run(["git","status","--porcelain"],cwd=self.root,capture_output=True,text=True,timeout=5)
            return bool(p.stdout.strip()) if p.returncode==0 else None
        except Exception:return None

    def changed_paths(self,base:str|None=None)->tuple[str,...]:
        try:
            cmd=["git","diff","--name-only",base or "HEAD~1","HEAD"]
            p=subprocess.run(cmd,cwd=self.root,capture_output=True,text=True,timeout=10)
            if p.returncode!=0:return ()
            return tuple(x.strip() for x in p.stdout.splitlines() if x.strip())
        except Exception:return ()

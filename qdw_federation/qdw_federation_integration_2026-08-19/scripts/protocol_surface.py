from __future__ import annotations
import argparse,ast,json,re,subprocess
from pathlib import Path

def public_python_surface(repo:Path)->dict:
    result={}
    for p in repo.rglob("*.py"):
        if any(x in p.parts for x in {".venv","venv","site-packages","tests"}):continue
        try:tree=ast.parse(p.read_text())
        except Exception:continue
        funcs=[];classes=[]
        for n in tree.body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.name.startswith("_"):
                funcs.append(n.name)
            if isinstance(n,ast.ClassDef) and not n.name.startswith("_"):
                classes.append(n.name)
        if funcs or classes:result[str(p.relative_to(repo))]={"functions":funcs,"classes":classes}
    return result

def routes(repo:Path)->list[dict]:
    out=[]
    pat=re.compile(r'@(?:app|router)\.(get|post|put|patch|delete)\(\s*["\\\']([^"\\\']+)')
    for p in repo.rglob("*.py"):
        if "test" in p.parts:continue
        try:text=p.read_text()
        except Exception:continue
        for m in pat.finditer(text):
            out.append({"path":str(p.relative_to(repo)),"method":m.group(1).upper(),"route":m.group(2)})
    return sorted(out,key=lambda x:(x["route"],x["method"],x["path"]))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("repo");ap.add_argument("--out")
    a=ap.parse_args();repo=Path(a.repo)
    obj={"repo":str(repo.resolve()),"python":public_python_surface(repo),"routes":routes(repo)}
    text=json.dumps(obj,indent=2)
    if a.out:Path(a.out).write_text(text)
    else:print(text)

if __name__=="__main__":main()

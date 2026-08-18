from __future__ import annotations
import argparse,ast,json
from pathlib import Path

CODES=[]
def scan(path:Path):
    try:tree=ast.parse(path.read_text())
    except SyntaxError as e:return [{"path":str(path),"line":e.lineno,"code":"SYNTAX"}]
    out=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Assert) and isinstance(n.test,ast.Constant) and n.test.value is True:
            out.append({"path":str(path),"line":n.lineno,"code":"ASSERT_TRUE"})
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_"):
            if len(n.body)==1 and isinstance(n.body[0],ast.Pass):
                out.append({"path":str(path),"line":n.lineno,"code":"EMPTY_TEST"})
            for d in n.decorator_list:
                name=ast.unparse(d)
                if "skip" in name or "xfail" in name:
                    out.append({"path":str(path),"line":n.lineno,"code":"SKIP_XFAIL_DECORATOR"})
        if isinstance(n,ast.Call):
            name=ast.unparse(n.func)
            if name in {"pytest.skip","pytest.xfail"}:
                out.append({"path":str(path),"line":n.lineno,"code":"RUNTIME_SKIP_XFAIL"})
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("roots",nargs="+");a=ap.parse_args()
    findings=[]
    for root in map(Path,a.roots):
        for p in root.rglob("test_*.py"):findings.extend(scan(p))
    print(json.dumps(findings,indent=2))
    raise SystemExit(1 if findings else 0)
if __name__=="__main__":main()

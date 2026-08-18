from __future__ import annotations
import ast
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Finding:
    path:str
    line:int
    code:str
    message:str

class _Visitor(ast.NodeVisitor):
    def __init__(self,path:str):self.path=path;self.findings=[]

    def visit_Assert(self,node:ast.Assert):
        if isinstance(node.test,ast.Constant) and node.test.value is True:
            self.findings.append(Finding(self.path,node.lineno,"ASSERT_TRUE","assert True is not evidence"))
        self.generic_visit(node)

    def visit_Call(self,node:ast.Call):
        name=""
        if isinstance(node.func,ast.Attribute):
            base=node.func.value.id if isinstance(node.func.value,ast.Name) else ""
            name=f"{base}.{node.func.attr}"
        elif isinstance(node.func,ast.Name):name=node.func.id
        if name in {"pytest.skip","pytest.xfail","skip","xfail"}:
            self.findings.append(Finding(self.path,node.lineno,"RUNTIME_SKIP",f"{name} can hide a failing gate"))
        self.generic_visit(node)

    def visit_FunctionDef(self,node:ast.FunctionDef):
        if node.name.startswith("test_"):
            meaningful=[x for x in node.body if not isinstance(x,(ast.Pass,ast.Expr)) or
                        not (isinstance(x,ast.Expr) and isinstance(x.value,ast.Constant) and isinstance(x.value.value,str))]
            if not meaningful:
                self.findings.append(Finding(self.path,node.lineno,"EMPTY_TEST","empty test function"))
            for dec in node.decorator_list:
                text=ast.unparse(dec) if hasattr(ast,"unparse") else ""
                if "skip" in text or "xfail" in text:
                    self.findings.append(Finding(self.path,node.lineno,"DECORATOR_SKIP",f"test decorator: {text}"))
        self.generic_visit(node)

def scan_test_file(path:str|Path)->list[Finding]:
    p=Path(path)
    try:tree=ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
    except SyntaxError as e:return [Finding(str(p),e.lineno or 0,"SYNTAX","test file does not parse")]
    v=_Visitor(str(p));v.visit(tree);return v.findings

def scan_test_tree(path:str|Path)->list[Finding]:
    out=[]
    for p in Path(path).rglob("test_*.py"):out.extend(scan_test_file(p))
    return out

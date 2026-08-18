from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class CheckResult:
    system:str
    ok:bool
    status:str
    detail:str

class FederationDoctor:
    def __init__(self,checks:dict[str,Callable[[],dict]]):self.checks=checks
    def run(self)->list[CheckResult]:
        out=[]
        for system,fn in self.checks.items():
            try:
                r=fn()
                ok=bool(r.get("ok",r.get("status") in {"ok","OK"}))
                out.append(CheckResult(system,ok,"OK" if ok else "DEGRADED",str(r)))
            except Exception as exc:
                out.append(CheckResult(system,False,"UNAVAILABLE",repr(exc)))
        return out

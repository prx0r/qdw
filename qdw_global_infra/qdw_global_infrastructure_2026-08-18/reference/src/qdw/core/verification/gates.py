from __future__ import annotations
from dataclasses import dataclass
from typing import Callable,Any

@dataclass(frozen=True)
class Gate:
    gate_id:str
    description:str
    fn:Callable[[dict[str,Any]],tuple[bool,dict[str,Any]]]

@dataclass(frozen=True)
class GateResult:
    gate_id:str
    passed:bool
    detail:dict[str,Any]

def run_gates(context:dict[str,Any],gates:list[Gate])->list[GateResult]:
    out=[]
    for g in gates:
        passed,detail=g.fn(context)
        out.append(GateResult(g.gate_id,bool(passed),detail))
    return out

def all_pass(results:list[GateResult])->bool:
    return bool(results) and all(r.passed for r in results)

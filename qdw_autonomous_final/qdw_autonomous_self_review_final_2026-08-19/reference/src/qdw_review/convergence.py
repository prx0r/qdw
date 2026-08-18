from __future__ import annotations
from dataclasses import dataclass
from .models import ReviewReport,Severity

@dataclass(frozen=True)
class ConvergenceState:
    round_no:int=0
    total_cost_usd:float=0.0
    previous_blockers:tuple[str,...]=()
    status:str="RUNNING"
    stop_reason:str|None=None

def next_state(state:ConvergenceState,report:ReviewReport,*,round_cost_usd:float,
               max_rounds:int,max_cost_usd:float|None,threshold:Severity=Severity.HIGH)->ConvergenceState:
    blockers=report.blocker_fingerprints(threshold)
    total=state.total_cost_usd+round_cost_usd
    if not blockers:
        return ConvergenceState(state.round_no+1,total,blockers,"READY_TO_CERTIFY",None)
    if state.round_no+1>=max_rounds:
        return ConvergenceState(state.round_no+1,total,blockers,"STOPPED","MAX_ROUNDS")
    if max_cost_usd is not None and total>=max_cost_usd:
        return ConvergenceState(state.round_no+1,total,blockers,"STOPPED","BUDGET_EXHAUSTED")
    if blockers==state.previous_blockers and blockers:
        return ConvergenceState(state.round_no+1,total,blockers,"STALLED","NO_PROGRESS")
    return ConvergenceState(state.round_no+1,total,blockers,"NEEDS_FIX",None)

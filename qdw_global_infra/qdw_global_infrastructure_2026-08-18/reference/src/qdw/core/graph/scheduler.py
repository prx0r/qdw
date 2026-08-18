from __future__ import annotations
from dataclasses import dataclass
from math import sqrt,log
from typing import Iterable

@dataclass(frozen=True)
class Candidate:
    node_id:str
    expected_value:float
    expected_cost:float
    confidence:float=1.0
    urgency:float=0.0
    risk:float=0.0
    sample_count:int=0

def net_value(c:Candidate)->float:
    return c.expected_value*c.confidence-c.expected_cost-c.risk+c.urgency

def opportunity_cost(chosen:Candidate,candidates:Iterable[Candidate])->float:
    alts=[net_value(c) for c in candidates if c.node_id!=chosen.node_id]
    return (max(alts) if alts else 0.0)-net_value(chosen)

def allocation_index(mean_utility:float,sample_count:int,total_samples:int,exploration:float=.25)->float:
    if sample_count<=0:return float("inf")
    return mean_utility+exploration*sqrt(max(0.0,log(max(2,total_samples)))/sample_count)

def choose(candidates:list[Candidate])->Candidate|None:
    eligible=[c for c in candidates if net_value(c)>0]
    if not eligible:return None
    return max(eligible,key=lambda c:(net_value(c),c.confidence,-c.expected_cost))

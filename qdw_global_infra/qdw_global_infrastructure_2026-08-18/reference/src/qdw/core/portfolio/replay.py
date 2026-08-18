from __future__ import annotations
from dataclasses import dataclass
from typing import Callable,Any

@dataclass(frozen=True)
class HistoricalDecision:
    decided_at:str
    opportunity_id:str
    feature_snapshot_hash:str
    frozen_features:dict[str,Any]
    realized_utility:float
    realized_cost:float

def replay(rows:list[HistoricalDecision],policy:Callable[[dict[str,Any]],bool])->dict:
    selected=[r for r in rows if policy(r.frozen_features)]
    if not selected:return {"selected":0,"utility":0.0,"cost":0.0}
    return {"selected":len(selected),
            "utility":sum(r.realized_utility for r in selected),
            "cost":sum(r.realized_cost for r in selected)}

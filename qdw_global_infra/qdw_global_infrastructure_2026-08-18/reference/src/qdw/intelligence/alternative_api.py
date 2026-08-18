from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .stack_oracle import StackOracle, ResourceRecommendation
from .opportunities import OpportunitySynthesizer

@dataclass(frozen=True)
class AlternativeSet:
    capability_key:str
    alternatives:tuple[ResourceRecommendation,...]
    build_gap:bool
    opportunity_id:str|None=None

class AlternativeAPI:
    """AlternativeAPI product logic: find substitutes; if none qualify, produce a build candidate."""

    def __init__(self,stack:StackOracle,synth:OpportunitySynthesizer):
        self.stack,self.synth=stack,synth

    def match(self,capability_key:str,*,current_resource_id:str|None=None,
              required_attributes:dict[str,Any]|None=None,max_cost:float|None=None,
              min_quality:float|None=None,max_latency_ms:float|None=None,
              create_gap:bool=False)->AlternativeSet:
        recs=self.stack.recommend(capability_key,required_attributes=required_attributes,
            max_cost=max_cost,min_quality=min_quality,max_latency_ms=max_latency_ms)
        recs=[r for r in recs if r.resource_id!=current_resource_id]
        if recs:
            return AlternativeSet(capability_key,tuple(recs),False,None)
        oid=None
        if create_gap:
            oid=self.synth.api_gap(capability_key,problem_key=f"alternative:{capability_key}",
                                   current_resource_id=current_resource_id,evidence_resources=[])
        return AlternativeSet(capability_key,(),True,oid)

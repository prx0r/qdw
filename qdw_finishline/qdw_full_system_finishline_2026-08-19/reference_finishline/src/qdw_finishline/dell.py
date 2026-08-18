from __future__ import annotations
from dataclasses import dataclass
from .models import Status

@dataclass(frozen=True)
class Workload:
    input_tokens:int=1000;output_tokens:int=500;requests:int=1

def workload_cost(input_per_m,output_per_m,free,workload:Workload):
    if free:return 0.0
    if input_per_m is None:return None
    if workload.output_tokens>0 and output_per_m is None:return None
    return ((input_per_m*workload.input_tokens + (output_per_m or 0)*workload.output_tokens)/1_000_000)*workload.requests

class DellService:
    schema="qdw-federation-resource/1"
    def __init__(self,candidates=None):
        self.candidates=list(candidates or [])
        self.available=True
    def federation_resolve(self,workload=None,max_cost=None):
        if not self.available:raise ConnectionError("dell unavailable")
        wl=workload or Workload()
        eligible=[];excluded=[]
        for raw in self.candidates:
            c=dict(raw)
            cost=workload_cost(c.get("input_per_m"),c.get("output_per_m"),bool(c.get("free")),wl)
            c["estimated_cost"]=cost
            if max_cost is not None and cost is None and not c.get("free"):
                excluded.append({"candidate":c,"reasons":["PRICE_UNKNOWN"]});continue
            if max_cost is not None and cost is not None and cost>max_cost:
                excluded.append({"candidate":c,"reasons":["COST_EXCEEDS_BUDGET"]});continue
            eligible.append(c)
        eligible.sort(key=lambda x:(x["estimated_cost"] is None,x["estimated_cost"] or 0,-float(x.get("score",0))))
        return {"schema_version":self.schema,"authority":"ADVISORY","status":Status.OK if eligible else Status.OK_EMPTY,
                "candidates":eligible,"recommended":eligible[0] if eligible else None,"excluded":excluded}

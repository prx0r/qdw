from __future__ import annotations
from dataclasses import dataclass
from ..core import hash_object,utc_now

@dataclass(frozen=True)
class OpportunityFeatures:
    need:float
    recurrence:float
    actionability:float
    verifiability:float
    distribution:float
    data_access:float
    competition:float
    integration_cost:float
    failure_risk:float
    confidence:float

def agentic_opportunity_score(f:OpportunityFeatures)->float:
    positives=[f.need,f.recurrence,f.actionability,f.verifiability,f.distribution,f.data_access]
    if any(x<=0 for x in positives):return 0.0
    p=1.0
    for x in positives:p*=max(1e-9,min(1,x))
    base=p**(1/len(positives))
    friction=.45*f.competition+.30*f.integration_cost+.25*f.failure_risk
    return max(0.0,min(1.0,base*(1-friction)*f.confidence))

def snapshot(features:dict)->dict:
    return {"observed_at":utc_now(),"features":features,"feature_snapshot_hash":hash_object(features)}

from __future__ import annotations
from dataclasses import dataclass
from .models import ResourceCandidate,CapabilityAssetView,FederatedRef
from .hashing import digest

@dataclass(frozen=True)
class FinalChoice:
    route_kind:str
    selected_ref:FederatedRef
    expected_cost_usd:float|None
    quality_hint:float|None
    reason_codes:tuple[str,...]
    candidate_set_digest:str

class QDWReferenceRouter:
    """Reference composition policy, not a replacement for production QDW HotSwap.

    It exists to contract-test that foreign scores remain advisory and unknown cost is not silently zero.
    """
    def choose(self,*,capability:str,dell_candidates:tuple[ResourceCandidate,...],
               forge_assets:tuple[CapabilityAssetView,...],quality_floor:float,
               max_cost_usd:float|None)->FinalChoice|None:
        rows=[]
        for c in dell_candidates:
            if c.capability!=capability:continue
            if max_cost_usd is not None and c.estimated_cost_usd is None:
                continue  # unknown hard budget => exclude in reference policy
            if max_cost_usd is not None and c.estimated_cost_usd>max_cost_usd:continue
            if c.quality is not None and c.quality<quality_floor:continue
            rows.append(("dell",c.external_ref,c.estimated_cost_usd,c.quality,
                         ("DELL_CANDIDATE","FOREIGN_ADVISORY_NOT_AUTHORITY")))
        for a in forge_assets:
            if capability not in a.capabilities or not a.certified or a.status!="ACTIVE":continue
            if max_cost_usd is not None and a.pricing_per_call is None:continue
            if max_cost_usd is not None and a.pricing_per_call>max_cost_usd:continue
            if a.posterior_mean is not None and a.sample_count>0 and a.posterior_mean<quality_floor:continue
            rows.append(("forge",a.external_ref,a.pricing_per_call,a.posterior_mean,
                         ("FORGE_CERTIFIED_ASSET","QDW_FINAL_SELECTION")))
        if not rows:return None
        # Explicit deterministic reference ranking. Production uses HotSwap.
        def rank(r):
            cost=r[2] if r[2] is not None else float("inf")
            q=r[3] if r[3] is not None else quality_floor
            return (cost/max(q,.05), -q, r[1].system, r[1].object_id)
        rows.sort(key=rank)
        k,ref,cost,q,reasons=rows[0]
        return FinalChoice(k,ref,cost,q,reasons,digest([
            {"kind":x[0],"ref":x[1],"cost":x[2],"quality":x[3]} for x in rows
        ]))

from __future__ import annotations
from typing import Any
from app.services.decision import (
    ResolveRequest,Workload,Constraints,Preferences,EvidencePolicy,
    build_candidates,calculate_workload_cost,apply_hard_constraints,assess_route,
)

SCHEMA="qdw-federation-resource/1"

def request_from_dict(raw:dict[str,Any])->ResolveRequest:
    return ResolveRequest(
      workload=Workload(**(raw.get("workload") or {})),
      constraints=Constraints(**(raw.get("constraints") or {})),
      preferences=Preferences(**(raw.get("preferences") or {})),
      evidence_policy=EvidencePolicy(**(raw.get("evidence_policy") or {})),
    )

def _candidate(c,a=None)->dict[str,Any]:
    return {
      "offer_id":c.offer_id,"model_id":c.model_id,"provider_id":c.provider_id,
      "endpoint_id":c.endpoint_id,"input_per_m":c.input_per_m,"output_per_m":c.output_per_m,
      "free":c.free,"context_tokens":c.context_tokens,"max_output_tokens":c.max_output_tokens,
      "tools_supported":c.tools_supported,"json_schema_support":c.json_schema_support,
      "streaming_support":c.streaming_support,"openai_compatible":c.openai_compatible,
      "automation_allowed":c.automation_allowed,"requires_card":c.requires_card,
      "requires_phone":c.requires_phone,"requires_kyc":c.requires_kyc,"region":c.region,
      "lifecycle_state":c.lifecycle_state,"freshness_state":c.freshness_state,
      "reliability":c.reliability,"throughput_tps":c.throughput_tps,"ttft_ms":c.ttft_ms,
      "quota_rpd":c.quota_rpd,"estimated_cost":c._workload_cost,
      "score":a.score if a else None,
      "evidence_coverage":a.evidence_coverage if a else None,
      "confidence":a.confidence if a else None,
    }

def federation_resolve(raw:dict[str,Any],offers:list[dict],endpoints:list[dict]|None=None)->dict[str,Any]:
    """Expose Dell resource truth + its recommendation as ADVISORY.

    Unlike the normal product response this returns every assessed eligible candidate, so QDW does not have to
    infer prices/capabilities from the top-five recommendation projection.
    """
    req=request_from_dict(raw)
    candidates=build_candidates(offers,endpoints or [])
    eligible=[];excluded=[]
    for c in candidates:
        c._workload_cost=calculate_workload_cost(c,req.workload)
        c._cost_known=c._workload_cost is not None
        reasons=apply_hard_constraints(c,req.constraints,req.evidence_policy)
        if reasons:
            excluded.append({"candidate":_candidate(c),"reasons":reasons})
        else:
            a=assess_route(c,req);eligible.append((c,a))
    eligible.sort(key=lambda x:x[1].score,reverse=True)
    recommended=_candidate(*eligible[0]) if eligible else None
    return {
      "schema_version":SCHEMA,"authority":"ADVISORY",
      "candidates":[_candidate(c,a) for c,a in eligible],
      "recommended":recommended,
      "excluded":excluded,
      "decision":{
        "status":"RESOLVED" if eligible else "NO_CANDIDATES",
        "eligible_count":len(eligible),"excluded_count":len(excluded),
        "method":"decision_service_v2_federation",
      },
    }

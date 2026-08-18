from __future__ import annotations
from qdw.core import hash_object,utc_now
from .contracts import *

class DellFederationAdapter:
    system_id="dell";protocol_version="dell.resolve/1";adapter_version="1.0.0"

    def normalize(self,request:dict,result:dict)->tuple[ExternalSnapshot,DecisionAdvisory|None]:
        decision=result.get("decision") or {}
        status={"RESOLVED":ExternalStatus.OK,"NO_CANDIDATES":ExternalStatus.OK_EMPTY}.get(
            decision.get("status"),ExternalStatus.DEGRADED
        )
        rows=[]
        if result.get("recommended"):rows.append(result["recommended"])
        rows.extend(result.get("alternatives") or [])
        # Do not convert Dell's score to QDW probability.
        normalized={"candidates":[{
            "ref":{"system":"dell","object_type":"route_candidate",
                   "object_id":x.get("offer_id") or f"{x.get('provider_id')}:{x.get('model_id')}"},
            "provider_id":x.get("provider_id"),"model_id":x.get("model_id"),
            "endpoint_id":x.get("endpoint_id"),
            "input_per_m":x.get("input_per_m"),"output_per_m":x.get("output_per_m"),
            "free":x.get("free"),"estimated_cost_usd":x.get("estimated_cost"),
            "context_tokens":x.get("context_tokens"),"tools_supported":x.get("tools_supported"),
            "json_schema_support":x.get("json_schema_support"),
            "reliability":x.get("reliability"),"ttft_ms":x.get("ttft_ms"),
            "dell_score":x.get("score"),"confidence":x.get("confidence"),
            "evidence_coverage":x.get("evidence_coverage"),
        } for x in rows],"excluded":result.get("excluded") or []}
        snap=ExternalSnapshot(
          "dell","resource_candidates",self.protocol_version,hash_object(request),hash_object(result),
          status,utc_now(),normalized,adapter_version=self.adapter_version,
          warnings=tuple(decision.get("reasons") or []))
        advisory=None
        if result.get("recommended"):
            advisory=DecisionAdvisory("dell","dell_"+hash_object(result)[:20],
                decision.get("method","decision_service"),hash_object(snap),
                {"recommended":result["recommended"],"alternatives":result.get("alternatives") or [],
                 "excluded":result.get("excluded") or []},decision.get("as_of",utc_now()))
        return snap,advisory

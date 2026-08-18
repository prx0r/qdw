from __future__ import annotations
from dataclasses import asdict
from qdw.core import hash_object,utc_now
from .contracts import *

class DellFederationAdapter:
    system_id="dell"
    protocol_version="qdw-federation-resource/1"
    adapter_version="2.0.0"

    def normalize(self,request:dict,result:dict)->tuple[ExternalSnapshot,DecisionAdvisory|None]:
        schema=result.get("schema_version")
        if schema!=self.protocol_version:
            snap=ExternalSnapshot(
              "dell","resource_candidates",str(schema or "unknown"),
              hash_object(request),hash_object(result),ExternalStatus.INCOMPATIBLE_PROTOCOL,
              utc_now(),{"candidates":[],"excluded":[]},adapter_version=self.adapter_version,
              warnings=(f"expected {self.protocol_version}, got {schema}",))
            return snap,None
        decision=result.get("decision") or {}
        status={"RESOLVED":ExternalStatus.OK,"NO_CANDIDATES":ExternalStatus.OK_EMPTY}.get(
            decision.get("status"),ExternalStatus.DEGRADED)
        rows=list(result.get("candidates") or [])
        normalized={"candidates":[{
          "ref":{"system":"dell","object_type":"route_candidate",
                 "object_id":x.get("offer_id") or f"{x.get('provider_id')}:{x.get('model_id')}",
                 "digest":hash_object(x)},
          "provider_id":x.get("provider_id"),"model_id":x.get("model_id"),
          "endpoint_id":x.get("endpoint_id"),
          "input_per_m":x.get("input_per_m"),"output_per_m":x.get("output_per_m"),
          "free":x.get("free"),"estimated_cost_usd":x.get("estimated_cost"),
          "context_tokens":x.get("context_tokens"),"max_output_tokens":x.get("max_output_tokens"),
          "tools_supported":x.get("tools_supported"),
          "json_schema_support":x.get("json_schema_support"),
          "streaming_support":x.get("streaming_support"),
          "openai_compatible":x.get("openai_compatible"),
          "automation_allowed":x.get("automation_allowed"),
          "requires_card":x.get("requires_card"),"requires_phone":x.get("requires_phone"),
          "requires_kyc":x.get("requires_kyc"),"region":x.get("region"),
          "lifecycle_state":x.get("lifecycle_state"),"freshness_state":x.get("freshness_state"),
          "reliability":x.get("reliability"),"throughput_tps":x.get("throughput_tps"),
          "ttft_ms":x.get("ttft_ms"),"quota_rpd":x.get("quota_rpd"),
          "dell_score":x.get("score"),"confidence":x.get("confidence"),
          "evidence_coverage":x.get("evidence_coverage"),
        } for x in rows],"excluded":result.get("excluded") or []}
        snap=ExternalSnapshot(
          "dell","resource_candidates",schema,hash_object(request),hash_object(result),
          status,utc_now(),normalized,adapter_version=self.adapter_version)
        rec=result.get("recommended")
        advisory=None
        if rec:
            advisory=DecisionAdvisory(
              "dell","dell_"+hash_object(result)[:20],
              decision.get("method","decision_service_v2_federation"),
              hash_object(asdict(snap)),
              {"recommended":rec,"candidate_count":len(rows),"excluded":result.get("excluded") or []},
              decision.get("as_of",utc_now()),authority="ADVISORY")
        return snap,advisory

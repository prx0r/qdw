from __future__ import annotations
from dataclasses import dataclass
from qdw.core import hash_object,utc_now
from qdw.hotswap.types import Route
from .contracts import ExternalSnapshot,FederatedRef
from .store import FederationStore

@dataclass(frozen=True)
class CandidateBinding:
    route:Route
    external_ref:FederatedRef
    route_kind:str
    source_snapshot_digest:str|None
    profile:dict

class FederatedCandidateCollector:
    """Convert foreign facts into QDW Route candidates without surrendering final route authority."""

    def dell(self,snapshot:ExternalSnapshot)->list[CandidateBinding]:
        rows=(snapshot.normalized or {}).get("candidates") or []
        out=[]
        for x in rows:
            refd=x["ref"]
            ref=FederatedRef("dell",refd["object_type"],refd["object_id"],
                             version=refd.get("version"),revision=refd.get("revision"),
                             digest=refd.get("digest"))
            # Prefer actual token prices from the dedicated Dell federation endpoint.
            free=bool(x.get("free",False))
            input_per_m=x.get("input_per_m")
            output_per_m=x.get("output_per_m")
            reliability=x.get("reliability")
            if reliability is not None and reliability>1:
                reliability=reliability/100.0
            route=Route(
              route_id="dell:"+ref.object_id,
              model_id=str(x.get("model_id") or ref.object_id),
              provider_id=str(x.get("provider_id") or "dell"),
              endpoint_id=x.get("endpoint_id"),
              active=True,free=free,input_per_m=input_per_m,output_per_m=output_per_m,
              context_tokens=x.get("context_tokens"),tools_supported=x.get("tools_supported"),
              json_supported=x.get("json_schema_support"),reliability=reliability,
              latency_ms=x.get("ttft_ms"),
              prior_success=None,prior_confidence=0.0,
              evidence_ids=[snapshot.response_digest,ref.digest] if ref.digest else [snapshot.response_digest],
            )
            out.append(CandidateBinding(route,ref,"DELL_INFERENCE",hash_object(snapshot),{
              "dell_score":x.get("score"),"confidence":x.get("confidence"),
              "evidence_coverage":x.get("evidence_coverage"),
            }))
        return out

    def forge(self,assets:list[dict],*,source_snapshot_digest:str|None=None)->list[CandidateBinding]:
        out=[]
        for a in assets:
            if a.get("status")!="ACTIVE" or not a.get("certificate_id"):
                continue
            version=str(a["version"])
            ref=FederatedRef("forge","capability_asset",str(a["asset_id"]),version=version,
                             digest=a.get("manifest_hash"))
            profile=a.get("profile") or {}
            mean=a.get("posterior_mean",profile.get("success_mean"))
            samples=int(a.get("sample_count",profile.get("sample_count",0)) or 0)
            # Foreign profile is only a prior feature, never copied as QDW's posterior.
            prior=float(mean) if mean is not None else None
            confidence=min(1.0,samples/50.0) if samples else 0.0
            price=(a.get("pricing") or {}).get("per_call")
            route=Route(
              route_id=f"forge:{ref.object_id}@{version}",
              model_id=f"forge-capability:{ref.object_id}",
              provider_id="forge",
              active=True,free=(price==0),fixed_request_cost_usd=price,
              reliability=prior,prior_success=prior,prior_confidence=confidence,
              evidence_ids=[x for x in (a.get("certificate_id"),ref.digest,source_snapshot_digest) if x],
            )
            out.append(CandidateBinding(route,ref,"FORGE_CAPABILITY",source_snapshot_digest,{
              "foreign_success_mean":prior,"foreign_sample_count":samples,
              "certificate_id":a.get("certificate_id")
            }))
        return out

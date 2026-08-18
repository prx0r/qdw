from __future__ import annotations
from datetime import UTC,datetime
from typing import Any
from ..models import *
from ..hashing import digest

class DellAdapter:
    """Normalize Dell DecisionService output as a resource snapshot + advisory.

    Dell scores are intentionally not mapped to QDW p_success.
    """

    system="dell"
    schema_version="qdw-federation-resource/1"

    def resolve_to_snapshot(self,request:dict[str,Any],result:dict[str,Any],
                            *,source_revision:str|None=None)->tuple[ResourceCandidateSnapshot,DecisionAdvisory|None]:
        fetched=datetime.now(UTC).isoformat()
        request_digest=digest(request)
        raw_digest=digest(result)
        decision=result.get("decision") or {}
        status_name=decision.get("status","")
        if status_name=="NO_CANDIDATES":
            status=ExternalStatus.OK_EMPTY
        elif status_name=="RESOLVED":
            status=ExternalStatus.OK
        else:
            status=ExternalStatus.DEGRADED

        normalized=[]
        by_key={}
        items=[]
        if result.get("recommended"):items.append(result["recommended"])
        items.extend(result.get("alternatives") or [])
        # Deduplicate offer/model/provider tuple while preserving recommended first.
        for x in items:
            key=(x.get("offer_id"),x.get("model_id"),x.get("provider_id"),x.get("endpoint_id"))
            if key in by_key:continue
            by_key[key]=x
        for x in by_key.values():
            oid=str(x.get("offer_id") or f"{x.get('provider_id')}:{x.get('model_id')}")
            ext=FederatedRef(
                self.system,"route_candidate",oid,
                revision=source_revision,
                digest=digest(x),
            )
            # DecisionService fields available in current result are deliberately sparse.
            # Unknown values stay None.
            normalized.append(ResourceCandidate(
                external_ref=ext,
                capability=str(request.get("capability") or request.get("workload",{}).get("task") or "inference"),
                provider_id=x.get("provider_id"),
                model_id=x.get("model_id"),
                endpoint_id=x.get("endpoint_id"),
                estimated_cost_usd=x.get("estimated_cost"),
                quality=None,
                reliability=None,
                attributes={
                    "dell_score":x.get("score"),
                    "evidence_coverage":x.get("evidence_coverage"),
                    "confidence":x.get("confidence"),
                    "reasons":x.get("reasons"),
                },
            ))
        snapshot=ResourceCandidateSnapshot(
            self.system,self.schema_version,request_digest,fetched,status,tuple(normalized),
            raw_digest,warnings=tuple(decision.get("reasons") or []),
        )
        advisory=None
        rec=result.get("recommended")
        if rec:
            rid=str(rec.get("offer_id") or f"{rec.get('provider_id')}:{rec.get('model_id')}")
            rec_ref=next((c.external_ref for c in normalized if c.external_ref.object_id==rid),None)
            alt_refs=tuple(c.external_ref for c in normalized if c.external_ref!=rec_ref)
            advisory=DecisionAdvisory(
                self.system,
                advisory_id="dell:"+raw_digest.split(":",1)[1][:20],
                method=str(decision.get("method") or "dell-decision-service"),
                recommended_ref=rec_ref,
                alternative_refs=alt_refs,
                excluded=tuple(result.get("excluded") or []),
                evidence_snapshot_digest=snapshot.snapshot_digest,
                as_of=str(decision.get("as_of") or fetched),
            )
        return snapshot,advisory

    def failure_snapshot(self,request:dict[str,Any],error:str)->ResourceCandidateSnapshot:
        return ResourceCandidateSnapshot(
            self.system,self.schema_version,digest(request),datetime.now(UTC).isoformat(),
            ExternalStatus.UNAVAILABLE,(),digest({"error":error}),warnings=(error,)
        )

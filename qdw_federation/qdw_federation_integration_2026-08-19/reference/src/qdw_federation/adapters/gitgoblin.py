from __future__ import annotations
from datetime import UTC,datetime
from typing import Any
from ..models import *
from ..hashing import digest

class GitGoblinAdapter:
    """Normalize GitGoblin's current VentureLab-compatible export into federation v1."""

    system="gitgoblin"
    schema_version="qdw-federation-observation/1"

    def market_records_to_batch(self,records:list[dict[str,Any]],*,cursor:str,
                                source_revision:str|None=None)->ObservationBatch:
        obs=[]
        for r in records:
            oid=str(r["observation_id"])
            evidence=r.get("evidence") or {}
            artifact=str(evidence.get("artifact_sha256") or digest(r))
            if not artifact.startswith("sha256:"):artifact="sha256:"+artifact
            quality=r.get("quality") or {}
            env=EvidenceEnvelope(
                source_system=self.system,
                authority=AuthorityKind.OBSERVATION,
                observed_at=str(r["observed_at"]),
                content_digest=artifact,
                evidence_refs=(),
                confidence=quality.get("confidence"),
                source_family=r.get("source_family") or "gitgoblin",
            )
            ext=FederatedRef(self.system,"observation",oid,revision=source_revision,digest=digest(r))
            obs.append(ObservationRecord(
                external_ref=ext,
                metric=str(r["metric"]),
                value=r.get("value"),
                unit=r.get("unit"),
                entity_key=str(r["entity_id"]),
                evidence=env,
                dimensions={"sector":r.get("sector"),"oracle_id":r.get("oracle_id"),"quality":quality},
            ))
        return ObservationBatch(self.system,self.schema_version,cursor,tuple(obs),
                                source_revision,datetime.now(UTC).isoformat())

    def opportunity_proposal(self,raw:dict[str,Any])->dict[str,Any]:
        """Preserve external proposal identity; never claim it is a QDW portfolio decision."""
        return {
            "proposal_ref": FederatedRef(
                self.system,"opportunity_proposal",str(raw["opportunity_id"]),digest=digest(raw)
            ),
            "problem": raw.get("problem"),
            "evidence_refs": tuple(
                FederatedRef(self.system,"evidence",str(x)) for x in raw.get("evidence",[])
            ),
            "scorecard": raw.get("scorecard") or {},
            "external_decision": raw.get("decision"),
            "solution_hypotheses": tuple(raw.get("solution_hypotheses") or []),
            "authority": AuthorityKind.ADVISORY,
        }

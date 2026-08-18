from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from .models import ObservationBatch,ResourceCandidateSnapshot,DecisionAdvisory,InvocationOutcome,VerificationCertificateRef
from .hashing import digest

@dataclass
class FederationStore:
    """Small in-memory reference store.

    QDW production implementation persists equivalent records in QDW's canonical DB.
    """
    observation_batches:dict[str,ObservationBatch]=field(default_factory=dict)
    observation_keys:set[str]=field(default_factory=set)
    snapshots:dict[str,ResourceCandidateSnapshot]=field(default_factory=dict)
    advisories:dict[str,DecisionAdvisory]=field(default_factory=dict)
    invocations:dict[str,InvocationOutcome]=field(default_factory=dict)
    certificates:dict[str,VerificationCertificateRef]=field(default_factory=dict)
    events:list[dict[str,Any]]=field(default_factory=list)

    def ingest_batch(self,batch:ObservationBatch)->dict[str,int]:
        if batch.idempotency_key in self.observation_batches:
            return {"inserted":0,"duplicates":len(batch.observations)}
        inserted=0;dupes=0
        for o in batch.observations:
            key=f"{o.external_ref.system}:{o.external_ref.object_type}:{o.external_ref.object_id}:{o.external_ref.digest}"
            if key in self.observation_keys:dupes+=1
            else:self.observation_keys.add(key);inserted+=1
        self.observation_batches[batch.idempotency_key]=batch
        self.events.append({"type":"observations.ingested","batch":batch.idempotency_key,
                            "inserted":inserted,"duplicates":dupes})
        return {"inserted":inserted,"duplicates":dupes}

    def put_snapshot(self,s:ResourceCandidateSnapshot):
        self.snapshots[s.snapshot_digest]=s
        self.events.append({"type":"external.snapshot","source":s.source_system,"digest":s.snapshot_digest})

    def put_advisory(self,a:DecisionAdvisory):
        self.advisories[a.advisory_id]=a
        self.events.append({"type":"external.advisory","source":a.adviser_system,"id":a.advisory_id})

    def put_invocation(self,x:InvocationOutcome):
        self.invocations[x.invocation_ref.object_id]=x
        self.events.append({"type":"external.invocation","id":x.invocation_ref.object_id,"status":x.status})

    def put_certificate(self,c:VerificationCertificateRef):
        self.certificates[c.certificate_id]=c
        self.events.append({"type":"external.certificate","id":c.certificate_id,"status":c.status})

from __future__ import annotations
from typing import Any
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now
from .contracts import *
from .store import FederationStore

class FederationService:
    """External I/O composition only; WorkGraph/HotSwap/Verification remain owned by QDW."""
    def __init__(self,system,*,store:FederationStore,
                 gitgoblin_client=None,gitgoblin_adapter=None,
                 dell_client=None,dell_adapter=None,forge_adapter=None):
        self.system=system;self.store=store
        self.gitgoblin_client,self.gitgoblin_adapter=gitgoblin_client,gitgoblin_adapter
        self.dell_client,self.dell_adapter=dell_client,dell_adapter
        self.forge=forge_adapter

    def health(self):
        return {"systems":{
          "gitgoblin":{"configured":self.gitgoblin_client is not None},
          "dell":{"configured":self.dell_client is not None},
          "forge":{"configured":self.forge is not None},
          "sandbox":{"configured":False,"mode":"INCUBATOR"}}}

    def sync_gitgoblin(self,params=None):
        if self.gitgoblin_client is None or self.gitgoblin_adapter is None:
            raise RuntimeError("GITGOBLIN_NOT_CONFIGURED")
        raw=self.gitgoblin_client.export_qdw(params or {})
        snap=self.gitgoblin_adapter.normalize(raw,params or {})
        sid=self.store.put_snapshot(snap)
        result=self.gitgoblin_adapter.to_source_result(snap)
        self.system.world.register_source(
          "federation:gitgoblin","technical_frontier","GitGoblin",
          config={"protocol":snap.protocol_version,"adapter":snap.adapter_version})
        ids=self.system.world.record_source_result(result)
        proposals=snap.normalized.get("opportunity_proposals",[])
        for proposal in proposals:
            ref=proposal.get("external_ref") or {}
            external_id=str(ref.get("object_id") or hash_object(proposal))
            external_digest=str(ref.get("digest") or hash_object(proposal))
            pid="extprop_"+hash_object({"system":"gitgoblin","id":external_id,"digest":external_digest})[:24]
            with self.system.db.tx(immediate=True) as con:
                con.execute("""INSERT OR IGNORE INTO external_opportunity_proposals(
                  proposal_id,system_id,external_object_id,external_object_digest,snapshot_id,
                  authority,problem_text,proposal_json,status,created_at
                ) VALUES(?,?,?,?,?,'ADVISORY',?,?,'UNASSESSED',?)""",
                (pid,"gitgoblin",external_id,external_digest,sid,proposal.get("problem"),
                 canonical_json(proposal).decode(),utc_now()))
                self.system.ledger.append_in_tx(con,"federation.opportunity_proposal",
                    "external_opportunity_proposal",pid,{"snapshot_id":sid,"authority":"ADVISORY"})
        return {
          "snapshot_id":sid,"status":snap.status.value,"observation_ids":ids,
          "batch_digest":snap.normalized.get("batch_digest"),
          "cursor":snap.normalized.get("cursor"),
          "proposal_ids":["extprop_"+hash_object({"system":"gitgoblin","id":str((p.get("external_ref") or {}).get("object_id") or hash_object(p)),
                        "digest":str((p.get("external_ref") or {}).get("digest") or hash_object(p))})[:24] for p in proposals]}

    def dell_candidates(self,request):
        if self.dell_client is None or self.dell_adapter is None:
            raise RuntimeError("DELL_NOT_CONFIGURED")
        raw=self.dell_client.resolve(request)
        snap,adv=self.dell_adapter.normalize(request,raw)
        sid=self.store.put_snapshot(snap)
        aid=self.store.put_advisory(adv,sid) if adv else None
        return snap,adv,sid,aid

    def forge_assets(self,capability):
        if self.forge is None:raise RuntimeError("FORGE_NOT_CONFIGURED")
        return self.forge.client.assets(capability)

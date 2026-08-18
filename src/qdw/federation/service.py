from __future__ import annotations
from typing import Any
from .contracts import *
from .store import FederationStore

class FederationService:
    """Composition service. It never replaces WorkGraph/HotSwap/Verification."""

    def __init__(self,system,*,store:FederationStore,
                 gitgoblin_client=None,gitgoblin_adapter=None,
                 dell_client=None,dell_adapter=None,
                 forge_adapter=None):
        self.system=system;self.store=store
        self.gitgoblin_client,self.gitgoblin_adapter=gitgoblin_client,gitgoblin_adapter
        self.dell_client,self.dell_adapter=dell_client,dell_adapter
        self.forge=forge_adapter

    def health(self)->dict[str,Any]:
        return {"systems":{
          "gitgoblin":{"configured":self.gitgoblin_client is not None},
          "dell":{"configured":self.dell_client is not None},
          "forge":{"configured":self.forge is not None},
          "sandbox":{"configured":False,"mode":"INCUBATOR"},
        }}

    def sync_gitgoblin(self,params:dict|None=None)->dict:
        if self.gitgoblin_client is None or self.gitgoblin_adapter is None:
            raise RuntimeError("GITGOBLIN_UNAVAILABLE: not configured")
        raw=self.gitgoblin_client.export_qdw(params or {})
        snap=self.gitgoblin_adapter.normalize(raw,params or {})
        sid=self.store.put_snapshot(snap)
        result=self.gitgoblin_adapter.to_source_result(snap)
        self.system.world.register_source(
          "federation:gitgoblin","technical_frontier","GitGoblin",
          config={"protocol":snap.protocol_version,"adapter":snap.adapter_version})
        observation_ids=self.system.world.record_source_result(result)
        # Opportunity proposals are intentionally not portfolio decisions. A separate OpportunityProposal
        # importer can create QDW opportunity evidence after policy/scoring.
        return {
          "snapshot_id":sid,"status":snap.status.value,
          "observation_ids":observation_ids,
          "opportunity_proposals":snap.normalized.get("opportunity_proposals",[]),
        }

    def dell_candidates(self,request:dict)->tuple[ExternalSnapshot,DecisionAdvisory|None]:
        if self.dell_client is None or self.dell_adapter is None:
            raise RuntimeError("DELL_UNAVAILABLE: not configured")
        raw=self.dell_client.resolve(request)
        snap,advisory=self.dell_adapter.normalize(request,raw)
        sid=self.store.put_snapshot(snap)
        if advisory:self.store.put_advisory(advisory,sid)
        return snap,advisory

    def forge_assets(self,capability:str)->list[dict]:
        if self.forge is None:raise RuntimeError("FORGE_UNAVAILABLE: not configured")
        return self.forge.client.assets(capability)

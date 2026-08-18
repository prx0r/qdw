from __future__ import annotations
import json
from qdw.core import hash_object,utc_now
from .candidates import CandidateBinding
from .store import FederationStore

class FederatedRouteRegistry:
    """Registers QDW Route plus the exact foreign object it represents."""

    def __init__(self,system,federation_store:FederationStore):
        self.system=system;self.federation_store=federation_store

    def register(self,b:CandidateBinding,snapshot_id:str|None=None,advisory_id:str|None=None)->None:
        self.system.route_registry.register(b.route)
        xref=self.federation_store.put_ref(b.external_ref)
        now=utc_now()
        bd=hash_object({
          "route_id":b.route.route_id,"external_ref":b.external_ref,
          "route_kind":b.route_kind,"snapshot":snapshot_id,"advisory":advisory_id,"profile":b.profile,
        })
        with self.system.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO federation_route_bindings(
              route_id,route_kind,federated_ref_id,source_snapshot_id,source_advisory_id,
              external_profile_json,binding_digest,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(route_id) DO UPDATE SET
              route_kind=excluded.route_kind,federated_ref_id=excluded.federated_ref_id,
              source_snapshot_id=excluded.source_snapshot_id,source_advisory_id=excluded.source_advisory_id,
              external_profile_json=excluded.external_profile_json,binding_digest=excluded.binding_digest,
              updated_at=excluded.updated_at""",
            (b.route.route_id,b.route_kind,xref,snapshot_id,advisory_id,
             json.dumps(b.profile,sort_keys=True),bd,now,now))
            self.system.ledger.append_in_tx(con,"federation.route_bound","route",b.route.route_id,
                {"external_ref_id":xref,"route_kind":b.route_kind,"binding_digest":bd})

    def binding(self,route_id:str)->dict:
        with self.system.db.connect() as con:
            r=con.execute("""SELECT b.*,r.system_id,r.object_type,r.object_id,r.object_version,
                                    r.object_revision,r.object_digest
                             FROM federation_route_bindings b JOIN federated_refs r
                             ON r.federated_ref_id=b.federated_ref_id WHERE b.route_id=?""",
                          (route_id,)).fetchone()
        if not r:raise KeyError(route_id)
        return dict(r)

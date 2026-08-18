from __future__ import annotations
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now
from .contracts import FederatedRef,ExternalSnapshot,DecisionAdvisory

class FederationStore:
    def __init__(self,db,ledger,artifact_store=None):
        self.db,self.ledger,self.artifacts=db,ledger,artifact_store

    def register_system(self,system_id:str,role:str,protocol_version:str,base_url:str|None=None,
                        trust_policy:dict|None=None)->None:
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT role,protocol_version FROM external_systems WHERE system_id=?",
                            (system_id,)).fetchone()
            if old and old["role"]!=role:
                raise ValueError("external system role immutable without explicit migration")
            con.execute("""INSERT INTO external_systems(
              system_id,role,protocol_version,base_url,enabled,trust_policy_json,created_at,updated_at
            ) VALUES(?,?,?,?,1,?,?,?)
            ON CONFLICT(system_id) DO UPDATE SET
              protocol_version=excluded.protocol_version,base_url=excluded.base_url,
              trust_policy_json=excluded.trust_policy_json,updated_at=excluded.updated_at""",
              (system_id,role,protocol_version,base_url,
               json.dumps(trust_policy or {},sort_keys=True),now,now))
            self.ledger.append_in_tx(con,"federation.system_registered","external_system",system_id,
                                     {"role":role,"protocol_version":protocol_version})

    def put_ref(self,ref:FederatedRef)->str:
        key=hash_object({
            "system":ref.system,"type":ref.object_type,"id":ref.object_id,
            "version":ref.version,"revision":ref.revision,"digest":ref.digest,
        })
        rid="xref_"+key[:24];now=utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO federated_refs(
              federated_ref_id,system_id,object_type,object_id,object_version,object_revision,
              object_digest,first_seen_at,last_seen_at
            ) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(system_id,object_type,object_id,object_version,object_revision,object_digest)
            DO UPDATE SET last_seen_at=excluded.last_seen_at""",
            (rid,ref.system,ref.object_type,ref.object_id,ref.version,ref.revision,ref.digest,now,now))
        return rid

    def put_snapshot(self,s:ExternalSnapshot)->str:
        from dataclasses import asdict
        sid="extsnap_"+hash_object(asdict(s))[:24]
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT OR IGNORE INTO external_snapshots(
              snapshot_id,system_id,snapshot_kind,protocol_version,request_digest,response_digest,
              raw_artifact_id,external_status,fetched_at,freshness_deadline,source_revision,
              adapter_version,normalized_digest,warning_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid,s.source_system,s.kind,s.protocol_version,s.request_digest,s.response_digest,
             s.raw_artifact_id,s.status.value,s.fetched_at,s.freshness_deadline,s.source_revision,
             s.adapter_version,hash_object(s.normalized),json.dumps(s.warnings)))
            self.ledger.append_in_tx(con,"federation.snapshot","external_snapshot",sid,
                                     {"system":s.source_system,"status":s.status.value})
        return sid

    def put_advisory(self,a:DecisionAdvisory,snapshot_id:str|None=None)->str:
        if a.authority!="ADVISORY":raise ValueError("external advisory cannot claim authority")
        aid="advisory_"+hash_object(a)[:24]
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT OR IGNORE INTO external_advisories(
              advisory_id,system_id,advisory_kind,snapshot_id,external_object_id,method,
              advisory_json,advisory_digest,as_of,authority
            ) VALUES(?,?,?,?,?,?,?,?,?,'ADVISORY')""",
            (aid,a.adviser_system,"route",snapshot_id,a.external_advisory_id,a.method,
             canonical_json(a.payload).decode(),hash_object(a),a.as_of))
            self.ledger.append_in_tx(con,"federation.advisory","external_advisory",aid,
                                     {"system":a.adviser_system,"method":a.method})
        return aid

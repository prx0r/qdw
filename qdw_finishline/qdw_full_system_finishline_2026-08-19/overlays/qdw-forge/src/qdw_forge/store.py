from __future__ import annotations
import json,secrets
from datetime import UTC,datetime
from .models import CapabilityAsset,AssetStatus,AssetProfile
from .hashing import sha256_obj

def now():return datetime.now(UTC).isoformat()

def definition_payload(asset:CapabilityAsset):
    d=asset.model_dump(mode="json")
    # Lifecycle/certificate are mutable activation state, not immutable capability definition.
    d.pop("status",None);d.pop("certificate_id",None)
    return d

def definition_hash(asset:CapabilityAsset):return sha256_obj(definition_payload(asset))

class ForgeStore:
    def __init__(self,db):
        self.db=db
        self._normalize_legacy_definition_hashes()

    def _normalize_legacy_definition_hashes(self):
        """One-time V1→V2 manifest-hash migration with an auditable old/new mapping."""
        with self.db.tx(immediate=True) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS asset_manifest_hash_migrations(
              asset_id TEXT NOT NULL,version TEXT NOT NULL,old_hash TEXT NOT NULL,new_hash TEXT NOT NULL,
              migrated_at TEXT NOT NULL,PRIMARY KEY(asset_id,version,old_hash,new_hash))""")
            rows=con.execute("SELECT asset_id,version,manifest_json,manifest_hash FROM assets").fetchall()
            for r in rows:
                raw=json.loads(r["manifest_json"])
                raw.pop("status",None);raw.pop("certificate_id",None)
                new_hash=sha256_obj(raw)
                if new_hash==r["manifest_hash"]:
                    continue
                con.execute("""INSERT OR IGNORE INTO asset_manifest_hash_migrations(
                  asset_id,version,old_hash,new_hash,migrated_at) VALUES(?,?,?,?,?)""",
                  (r["asset_id"],r["version"],r["manifest_hash"],new_hash,now()))
                con.execute("UPDATE assets SET manifest_hash=? WHERE asset_id=? AND version=?",
                            (new_hash,r["asset_id"],r["version"]))

    def register_asset(self,asset:CapabilityAsset):
        h=definition_hash(asset);key=(asset.asset_id,asset.version)
        canonical=asset.model_copy(update={"status":AssetStatus.CANDIDATE,"certificate_id":None})
        payload=json.dumps(canonical.model_dump(mode="json"),sort_keys=True,separators=(",",":"))
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT manifest_hash FROM assets WHERE asset_id=? AND version=?",key).fetchone()
            if old and old["manifest_hash"]!=h:
                raise ValueError("immutable asset version conflict; bump version")
            if not old:
                con.execute("""INSERT INTO assets(
                  asset_id,version,kind,name,status,manifest_json,manifest_hash,
                  certificate_id,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (asset.asset_id,asset.version,asset.kind.value,asset.name,
                 "CANDIDATE",payload,h,None,now()))
            for cap in asset.capabilities:
                con.execute("""INSERT OR IGNORE INTO asset_capabilities(
                  asset_id,version,capability) VALUES(?,?,?)""",
                  (asset.asset_id,asset.version,cap))
            con.execute("""INSERT OR IGNORE INTO asset_activations_v2(
              asset_id,version,status,certificate_id,certificate_hash,updated_at
            ) VALUES(?,?, 'CANDIDATE',NULL,NULL,?)""",(asset.asset_id,asset.version,now()))
        return self.get(asset.asset_id,asset.version)

    def bind_source(self,asset_id,version,*,repository_uri,source_commit,manifest_path,manifest_digest):
        sid="src_"+secrets.token_hex(12)
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT OR IGNORE INTO asset_source_bindings(
              source_binding_id,asset_id,version,source_kind,repository_uri,source_commit,
              manifest_path,manifest_digest,observed_at
            ) VALUES(?,?,?,'FORGEJO',?,?,?,?,?)""",
            (sid,asset_id,version,repository_uri,source_commit,manifest_path,manifest_digest,now()))

    def activate(self,asset_id,version,*,certificate_id,certificate_hash):
        if not certificate_id or not certificate_hash:raise ValueError("activation certificate required")
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM assets WHERE asset_id=? AND version=?",(asset_id,version)).fetchone():
                raise KeyError((asset_id,version))
            con.execute("""UPDATE asset_activations_v2 SET
              status='ACTIVE',certificate_id=?,certificate_hash=?,activated_at=COALESCE(activated_at,?),
              updated_at=? WHERE asset_id=? AND version=?""",
              (certificate_id,certificate_hash,now(),now(),asset_id,version))
        return self.get(asset_id,version)

    def get(self,asset_id,version):
        with self.db.connect() as con:
            r=con.execute("""SELECT a.manifest_json,x.status,x.certificate_id
              FROM assets a JOIN asset_activations_v2 x USING(asset_id,version)
              WHERE a.asset_id=? AND a.version=?""",(asset_id,version)).fetchone()
        if not r:raise KeyError((asset_id,version))
        d=json.loads(r["manifest_json"]);d["status"]=r["status"];d["certificate_id"]=r["certificate_id"]
        return CapabilityAsset.model_validate(d)

    def list_assets(self):
        with self.db.connect() as con:keys=con.execute("SELECT asset_id,version FROM assets ORDER BY asset_id,version").fetchall()
        return [self.get(r["asset_id"],r["version"]) for r in keys]

    def candidates(self,capability,active_only=True):
        xs=[x for x in self.list_assets() if capability in x.capabilities]
        if active_only:xs=[x for x in xs if x.status==AssetStatus.ACTIVE]
        return xs

    def profile(self,asset_id,version,capability):
        with self.db.connect() as con:r=con.execute("""SELECT * FROM asset_profiles
          WHERE asset_id=? AND version=? AND capability=?""",(asset_id,version,capability)).fetchone()
        if r:
            return AssetProfile(asset_id=asset_id,version=version,capability=capability,
                                alpha=float(r["alpha"]),beta=float(r["beta"]),
                                sample_count=int(r["sample_count"]),total_cost_usd=float(r["total_cost_usd"]))
        return AssetProfile(asset_id=asset_id,version=version,capability=capability)

    def get_profile(self,asset_id,version,capability):
        return self.profile(asset_id,version,capability)

    def apply_verified_result(self,*,asset_id,version,capability,certificate_id,certificate_hash,
                              invocation_id,output_hash,policy_hash,success,cost_usd):
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT invocation_id FROM verification_applications WHERE certificate_id=?",
                            (certificate_id,)).fetchone()
            if old:
                if old["invocation_id"]!=invocation_id:raise ValueError("certificate replay across invocations")
                return False
            if con.execute("SELECT 1 FROM verification_applications WHERE invocation_id=?",(invocation_id,)).fetchone():
                raise ValueError("invocation already has verification application")
            con.execute("""INSERT INTO verification_applications(
              certificate_id,certificate_hash,issuer_system,invocation_id,subject_output_hash,
              policy_hash,status,applied_at
            ) VALUES(?,?,'qdw',?,?,?,?,?)""",
            (certificate_id,certificate_hash,invocation_id,output_hash,policy_hash,
             "VERIFIED" if success else "REJECTED",now()))
            r=con.execute("""SELECT alpha,beta,sample_count,total_cost_usd FROM asset_profiles
              WHERE asset_id=? AND version=? AND capability=?""",(asset_id,version,capability)).fetchone()
            a,b,n,total=(float(r["alpha"]),float(r["beta"]),int(r["sample_count"]),float(r["total_cost_usd"])) if r else (1,1,0,0)
            a+=1 if success else 0;b+=0 if success else 1;n+=1;total+=cost_usd
            con.execute("""INSERT INTO asset_profiles(asset_id,version,capability,alpha,beta,sample_count,total_cost_usd,updated_at)
              VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(asset_id,version,capability) DO UPDATE SET
              alpha=excluded.alpha,beta=excluded.beta,sample_count=excluded.sample_count,
              total_cost_usd=excluded.total_cost_usd,updated_at=excluded.updated_at""",
              (asset_id,version,capability,a,b,n,total,now()))
        return True

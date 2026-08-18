from __future__ import annotations
import uuid
from .hashing import digest
from .models import *
from .runtime_store import RuntimeStore
from .route_store import RouteStore
from .verifier import QDWVerifier

class FederationRuntime:
    def __init__(self,db_path,route_db_path,gitgoblin,dell,forge,verifier=None):
        self.store=RuntimeStore(db_path);self.routes=RouteStore(route_db_path)
        self.gitgoblin=gitgoblin;self.dell=dell;self.forge=forge;self.verifier=verifier or QDWVerifier()
        self._lease_cache={}

    def sync_gitgoblin(self):
        b=self.gitgoblin.export_qdw()
        if b.schema_version!="qdw-federation-observation/1":raise ValueError("INCOMPATIBLE_PROTOCOL")
        inserted=0;props=0
        for o in b.observations:
            eid=(o.get("external_ref") or {}).get("object_id")
            inserted+=self.store.add_observation("gitgoblin",eid,digest(o),o)
        for p in b.proposals:
            eid=(p.get("external_ref") or {}).get("object_id")
            if p.get("authority")!="ADVISORY":raise ValueError("proposal authority violation")
            props+=self.store.add_proposal("gitgoblin",eid,digest(p),p)
        return {"observations":inserted,"proposals":props,"batch_digest":b.batch_digest}

    def refresh_routes(self,capability,workload=None,max_cost=None):
        result=self.dell.federation_resolve(workload,max_cost)
        if result["authority"]!="ADVISORY":raise ValueError("Dell authority violation")
        for c in result["candidates"]:
            oid=str(c.get("offer_id") or f"{c.get('provider_id')}:{c.get('model_id')}")
            self.routes.save(Route("dell:"+oid,"dell",capability,c.get("estimated_cost"),
                                   c.get("quality"),True,Ref("dell","offer",oid)))
        for a in self.forge.assets(capability,active_only=True):
            prof=a.get("profile") or {}
            self.routes.save(Route(f"forge:{a['asset_id']}@{a['version']}","forge",capability,
                                   (a.get("pricing") or {}).get("per_call"),prof.get("success_mean"),
                                   True,Ref("forge","capability_asset",a["asset_id"],a["version"],a["manifest_hash"])))
        return self.routes.all()

    def choose(self,capability):
        candidates=[r for r in self.routes.all() if r.active and r.capability==capability]
        if not candidates:return None
        known=[r for r in candidates if r.fixed_cost is not None]
        pool=known or candidates
        return sorted(pool,key=lambda r:(r.fixed_cost is None,r.fixed_cost or 0,-(r.quality or 0),r.route_id))[0]

    def execute(self,capability,arguments,max_spend=None,attempt_id=None,stop_after=None):
        aid=attempt_id or "att_"+uuid.uuid4().hex[:16]
        try:self.store.get(aid)
        except KeyError:self.store.create_attempt(aid,capability,arguments)
        row=self.store.get(aid)
        if row["state"]==AttemptState.COMMITTED.value:return row

        if row["state"]==AttemptState.DISCOVERING.value:
            self.refresh_routes(capability,max_cost=max_spend)
            self.store.set(aid,AttemptState.CANDIDATES_READY)
            if stop_after=="CANDIDATES_READY":return self.store.get(aid)
        row=self.store.get(aid)

        if row["state"]==AttemptState.CANDIDATES_READY.value:
            choice=self.choose(capability)
            if not choice:
                self.store.set(aid,AttemptState.FAILED,error="NO_ROUTE");return self.store.get(aid)
            self.store.set(aid,AttemptState.ROUTED,route_id=choice.route_id)
            if stop_after=="ROUTED":return self.store.get(aid)
        row=self.store.get(aid);route=self.routes.load(row["route_id"])

        if route.source!="forge":
            self.store.set(aid,AttemptState.FAILED,error="REFERENCE_ONLY_FORGE_EXECUTION")
            return self.store.get(aid)

        if row["state"]==AttemptState.ROUTED.value:
            ref=route.external_ref
            lease=self.forge.create_lease(capability=capability,asset_id=ref.object_id,version=ref.version,
                                          calls=1,max_spend=max_spend,operations=("invoke",))
            self._lease_cache[aid]=lease
            self.store.set(aid,AttemptState.LEASED)
            if stop_after=="LEASED":return self.store.get(aid)
        row=self.store.get(aid)

        if row["state"]==AttemptState.LEASED.value:
            lease=self._lease_cache.get(aid)
            if lease is None:
                ref=route.external_ref
                lease=self.forge.create_lease(capability=capability,asset_id=ref.object_id,version=ref.version,
                                              calls=1,max_spend=max_spend,operations=("invoke",))
                self._lease_cache[aid]=lease
            self.store.set(aid,AttemptState.RUNNING)
            inv=self.forge.invoke(lease_token=lease["token"],capability=capability,arguments=arguments,
                                  client_request_id=aid)
            self.store.set(aid,AttemptState.SUCCEEDED_UNVERIFIED if inv.status=="SUCCEEDED_UNVERIFIED" else AttemptState.FAILED,
                           external_invocation_id=inv.invocation_id,output_digest=inv.output_digest,cost=inv.cost)
            if stop_after=="SUCCEEDED_UNVERIFIED":return self.store.get(aid)
        row=self.store.get(aid)

        if row["state"]==AttemptState.FAILED.value:return row
        inv=self.forge.invocations[row["external_invocation_id"]]
        if row["state"]==AttemptState.SUCCEEDED_UNVERIFIED.value:
            self.store.set(aid,AttemptState.VERIFYING)
            cert=self.verifier.verify(inv)
            self.forge.bind_certificate(inv.invocation_id,cert)
            self.store.set(aid,AttemptState.VERIFIED,certificate_id=cert.certificate_id)
            if stop_after=="VERIFIED":return self.store.get(aid)
        row=self.store.get(aid)

        if row["state"]==AttemptState.VERIFIED.value:
            self.store.commit_result(aid,route.route_id,True,float(row["cost"] or 0),
                                     row["external_invocation_id"],row["certificate_id"])
        return self.store.get(aid)

from __future__ import annotations
from typing import Any
from .hashing import digest

class FakeForgeTransport:
    def __init__(self,assets:list[dict[str,Any]],*,substitute:bool=False):
        self._assets=assets
        self.substitute=substitute
        self.leases={}
        self.invocations={}
        self.bound_certificates={}
        self._n=0

    def list_assets(self,capability:str):
        return [dict(a) for a in self._assets if capability in a.get("capabilities",[])]

    def create_lease(self,body):
        self._n+=1
        lid=f"lease_{self._n}"
        self.leases[lid]=dict(body)
        return {"lease":{"lease_id":lid,**body},"token":lid}

    def invoke(self,body):
        lease=self.leases[body["lease_token"]]
        asset_id=lease["asset_id"];version=lease["version"]
        if self.substitute:
            other=next((x for x in self._assets if x["asset_id"]!=asset_id),None)
            if other:asset_id,version=other["asset_id"],other["version"]
        inv=f"inv_{len(self.invocations)+1}"
        output={"ok":True,"asset":asset_id,"arguments":body["arguments"]}
        record={
            "invocation_id":inv,"asset_id":asset_id,"version":version,
            "status":"SUCCEEDED_UNVERIFIED","output":output,"output_hash":digest(output),
            "cost_usd":next((x.get("pricing",{}).get("per_call",0) for x in self._assets if x["asset_id"]==asset_id),0),
            "route_decision":{"policy":"lease-pinned","chosen_asset_id":asset_id,"chosen_version":version},
        }
        self.invocations[inv]=record
        return record

    def bind_certificate(self,invocation_id,body):
        if "passed" in body:raise AssertionError("caller-authored passed boolean forbidden")
        cert=body["certificate"]
        if cert["subject"]["object_id"]!=invocation_id:raise ValueError("certificate subject mismatch")
        self.bound_certificates[invocation_id]=body
        return {"ok":True}

def forge_asset(asset_id="worker.api",version="1.0.0",capability="api.build",cost=.01,
                quality=.9,samples=10):
    return {
        "asset_id":asset_id,"version":version,"name":asset_id,
        "capabilities":[capability],"certificate_id":"fixture-cert",
        "status":"ACTIVE","pricing":{"per_call":cost},
        "posterior_mean":quality,"sample_count":samples,
        "transport":{"kind":"HTTP"},"manifest_hash":digest({"asset_id":asset_id,"version":version}),
    }

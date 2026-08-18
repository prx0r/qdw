from __future__ import annotations
import hashlib,secrets
from dataclasses import dataclass
from .hashing import digest
from .models import AssetManifest,Lease,Invocation,Certificate,Ref

class ForgeError(RuntimeError):pass
class AuthorizationError(ForgeError):pass
class BudgetError(ForgeError):pass
class ConflictError(ForgeError):pass

@dataclass(frozen=True)
class Activation:
    asset_id:str;version:str;certificate_id:str;certificate_digest:str;active:bool=True

class ForgeService:
    """Corrected reference Forge semantics.

    Immutable manifest, separate activation, authorization-before-idempotency,
    operation enforcement, exact request replay semantics, spend settlement,
    and idempotent certificate application.
    """
    def __init__(self):
        self.manifests={}
        self.activations={}
        self.leases={}
        self.tokens={}
        self.invocations={}
        self.idempotency={}
        self.profiles={}
        self.cert_applications={}
        self.actual_cost_overrides={}

    def register_asset(self,m:AssetManifest):
        key=(m.asset_id,m.version)
        old=self.manifests.get(key)
        if old and old.manifest_digest!=m.manifest_digest:raise ConflictError("immutable manifest conflict")
        self.manifests[key]=old or m
        return self.manifests[key]

    def activate(self,asset_id,version,certificate_id,certificate_digest):
        key=(asset_id,version)
        if key not in self.manifests:raise KeyError(key)
        # Does not mutate manifest.
        a=Activation(asset_id,version,certificate_id,certificate_digest,True)
        self.activations[key]=a
        return a

    def assets(self,capability=None,active_only=False):
        out=[]
        for key,m in sorted(self.manifests.items()):
            if capability and capability not in m.capabilities:continue
            a=self.activations.get(key)
            if active_only and not (a and a.active):continue
            out.append({
                "asset_id":m.asset_id,"version":m.version,"name":m.name,
                "capabilities":list(m.capabilities),"manifest_hash":m.manifest_digest,
                "status":"ACTIVE" if a and a.active else "CANDIDATE",
                "certificate_id":a.certificate_id if a else None,
                "pricing":{"per_call":m.per_call},
                "profile":self.profile(m.asset_id,m.version,capability or (m.capabilities[0] if m.capabilities else "")),
                "provenance":{"source_repo":m.source_repo,"source_commit":m.source_commit,
                              "source_manifest_digest":m.source_manifest_digest},
            })
        return out

    def create_lease(self,*,capability,asset_id,version,calls=1,max_spend=None,operations=("invoke",)):
        key=(asset_id,version);m=self.manifests.get(key);a=self.activations.get(key)
        if not m or not a or not a.active:raise KeyError("asset not active")
        if capability not in m.capabilities:raise ValueError("capability mismatch")
        if calls<=0:raise ValueError("calls")
        token="lease-token-"+secrets.token_hex(16)
        lid="lease_"+secrets.token_hex(8)
        th=hashlib.sha256(token.encode()).hexdigest()
        self.leases[lid]=Lease(lid,asset_id,version,capability,th,calls,0,max_spend,0.0,tuple(operations),True)
        self.tokens[th]=lid
        return {"lease_id":lid,"token":token,"asset_id":asset_id,"version":version}

    def _authorize(self,token,capability,operation):
        th=hashlib.sha256(token.encode()).hexdigest()
        lid=self.tokens.get(th)
        if not lid:raise AuthorizationError("bad lease token")
        l=self.leases[lid]
        if not l.active:raise AuthorizationError("inactive lease")
        if l.capability!=capability:raise AuthorizationError("capability outside lease")
        if operation not in l.operations:raise AuthorizationError("operation outside lease")
        return l

    def invoke(self,*,lease_token,capability,arguments,client_request_id):
        # Critical ordering: authorize before idempotency disclosure.
        l=self._authorize(lease_token,capability,"invoke")
        request_digest=digest({"capability":capability,"arguments":arguments})
        ikey=(l.lease_id,client_request_id)
        old_id=self.idempotency.get(ikey)
        if old_id:
            old=self.invocations[old_id]
            if old.request_digest!=request_digest:raise ConflictError("idempotency request mismatch")
            return old

        m=self.manifests[(l.asset_id,l.version)]
        if l.calls_used>=l.calls_total:raise AuthorizationError("call limit")
        reserve=m.per_call
        if l.max_spend is not None and l.spend+reserve>l.max_spend+1e-12:raise BudgetError("spend limit")
        # Reserve.
        l.calls_used+=1;l.spend+=reserve
        iid="inv_"+secrets.token_hex(8)
        self.idempotency[ikey]=iid
        # Fixture dispatcher.
        output={"ok":True,"asset":m.asset_id,"version":m.version,"arguments":arguments}
        actual=self.actual_cost_overrides.get((m.asset_id,m.version),reserve)
        if actual<0:raise ValueError("negative actual")
        # Settle: if actual > reserve, reject if budget would be exceeded.
        delta=actual-reserve
        if delta>0 and l.max_spend is not None and l.spend+delta>l.max_spend+1e-12:
            # Reservation is kept as incurred minimum for this reference; invocation fails clearly.
            inv=Invocation(iid,l.lease_id,client_request_id,m.asset_id,m.version,capability,
                           request_digest,"FAILED",None,None,reserve)
            self.invocations[iid]=inv
            return inv
        l.spend+=delta
        inv=Invocation(iid,l.lease_id,client_request_id,m.asset_id,m.version,capability,
                       request_digest,"SUCCEEDED_UNVERIFIED",output,digest(output),actual)
        self.invocations[iid]=inv
        return inv

    def bind_certificate(self,invocation_id,cert:Certificate):
        inv=self.invocations.get(invocation_id)
        if not inv:raise KeyError(invocation_id)
        if cert.issuer!="qdw":raise AuthorizationError("untrusted issuer")
        if cert.subject.system!="forge" or cert.subject.kind!="invocation" or cert.subject.object_id!=invocation_id:
            raise AuthorizationError("certificate subject mismatch")
        if cert.output_digest!=(inv.output_digest or digest({"failed":invocation_id})):
            raise AuthorizationError("certificate output mismatch")
        applied=self.cert_applications.get(cert.certificate_id)
        if applied:
            if applied!=invocation_id:raise ConflictError("certificate replay across subjects")
            return self.invocations[invocation_id]  # exact replay = idempotent
        if inv.status not in {"SUCCEEDED_UNVERIFIED","FAILED"}:raise ConflictError("not awaiting verification")
        status="VERIFIED" if cert.status=="VERIFIED" else "REJECTED"
        new=Invocation(inv.invocation_id,inv.lease_id,inv.client_request_id,inv.asset_id,inv.version,
                       inv.capability,inv.request_digest,status,inv.output,inv.output_digest,inv.cost)
        self.invocations[invocation_id]=new
        self.cert_applications[cert.certificate_id]=invocation_id
        pkey=(inv.asset_id,inv.version,inv.capability)
        p=self.profiles.setdefault(pkey,{"alpha":1.0,"beta":1.0,"sample_count":0,"total_cost":0.0})
        if cert.status=="VERIFIED":p["alpha"]+=1
        else:p["beta"]+=1
        p["sample_count"]+=1;p["total_cost"]+=inv.cost
        return new

    def profile(self,asset_id,version,capability):
        p=self.profiles.get((asset_id,version,capability),{"alpha":1.0,"beta":1.0,"sample_count":0,"total_cost":0.0})
        mean=p["alpha"]/(p["alpha"]+p["beta"])
        return {**p,"success_mean":mean,"mean_cost":p["total_cost"]/p["sample_count"] if p["sample_count"] else None}

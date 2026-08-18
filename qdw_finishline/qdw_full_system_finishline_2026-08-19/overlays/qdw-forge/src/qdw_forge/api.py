from __future__ import annotations
import os
from fastapi import FastAPI,HTTPException,Depends
from pydantic import BaseModel
from .app import from_env
from .models import CapabilityAsset,LeaseRequest,InvocationRequest
from .federation import CertificateEnvelope,CertificateReference
from .client_auth import authenticate_client,admin_token
from .hashing import sha256_obj

app=FastAPI(title="QDW Forge",version="0.2.0")
_state=None
def state():
    global _state
    if _state is None:_state=from_env()
    return _state

class ActivateBody(BaseModel):
    certificate:CertificateReference
class ForgejoSyncBody(BaseModel):
    base_url:str;org:str;token:str|None=None;page_size:int=50
class LabFixtureBody(BaseModel):
    capability:str="fixture.echo"

@app.get("/health")
def health():
    return {"status":"ok","protocol":"qdw-forge/2"}

@app.get("/v1/protocol")
def protocol():
    return {
      "version":"qdw-forge/2",
      "schemas":{
        "invocation_verification":{"fields":["certificate"]},
        "lease":{"client_identity":"authenticated","operations_enforced":True},
        "idempotency":{"scope":"authenticated_client_id + client_request_id","auth_before_lookup":True},
      }}

@app.post("/v1/assets")
def register(asset:CapabilityAsset,client_id:str=Depends(authenticate_client)):
    try:return state().store.register_asset(asset).model_dump(mode="json")
    except ValueError as e:raise HTTPException(409,str(e))

@app.get("/v1/assets")
def assets(capability:str|None=None):
    xs=state().store.candidates(capability,active_only=False) if capability else state().store.list_assets()
    out=[]
    for x in xs:
        d=x.model_dump(mode="json")
        d["manifest_hash"]=__import__("qdw_forge.store",fromlist=["definition_hash"]).definition_hash(x)
        d["profile"]=state().store.profile(x.asset_id,x.version,capability or x.capabilities[0]).model_dump(mode="json")
        with state().db.connect() as con:
            src=con.execute("""SELECT repository_uri,source_commit,manifest_path,manifest_digest
              FROM asset_source_bindings WHERE asset_id=? AND version=?
              ORDER BY observed_at DESC LIMIT 1""",(x.asset_id,x.version)).fetchone()
        d["provenance"]=dict(src) if src else None
        out.append(d)
    return out

@app.post("/v1/assets/{asset_id}/{version}/activate")
def activate(asset_id:str,version:str,body:ActivateBody,client_id:str=Depends(authenticate_client)):
    c=body.certificate
    if c.subject.system!="forge" or c.subject.object_type!="capability_asset":
        raise HTTPException(400,"activation certificate subject must be forge capability_asset")
    if c.subject.object_id!=asset_id or c.subject.version!=version:
        raise HTTPException(400,"activation certificate asset/version mismatch")
    try:
        resolved=state().certificate_resolver.resolve(c)
        asset=state().store.get(asset_id,version)
        from .store import definition_hash
        if c.subject.digest and c.subject.digest!=definition_hash(asset):
            raise ValueError("activation certificate definition hash mismatch")
        return state().store.activate(
          asset_id,version,certificate_id=c.certificate_id,certificate_hash=c.certificate_hash
        ).model_dump(mode="json")
    except KeyError:raise HTTPException(404,"asset not found")
    except (ValueError,PermissionError) as e:raise HTTPException(400,str(e))

@app.post("/v1/leases")
def lease(req:LeaseRequest,client_id:str=Depends(authenticate_client)):
    try:
        l,t,decision=state().leases.create(req,client_id=client_id)
        return {"lease":l.model_dump(mode="json"),"token":t,
                "route_decision":decision.model_dump(mode="json")}
    except (LookupError,ValueError,PermissionError) as e:raise HTTPException(400,str(e))

@app.post("/v1/invoke")
def invoke(req:InvocationRequest,client_id:str=Depends(authenticate_client)):
    try:return state().invocations.invoke(req,client_id=client_id).model_dump(mode="json")
    except (ValueError,PermissionError,LookupError) as e:raise HTTPException(400,str(e))

@app.get("/v1/invocations/{invocation_id}")
def invocation(invocation_id:str,client_id:str=Depends(authenticate_client)):
    try:
        with state().db.connect() as con:
            own=con.execute("SELECT client_id FROM invocations WHERE invocation_id=?",(invocation_id,)).fetchone()
        if not own:raise KeyError(invocation_id)
        if own["client_id"]!=client_id:raise PermissionError("invocation client mismatch")
        return state().invocations.get(invocation_id).model_dump(mode="json")
    except KeyError:raise HTTPException(404,"invocation not found")
    except PermissionError as e:raise HTTPException(403,str(e))

@app.post("/v1/invocations/{invocation_id}/verification")
def verify(invocation_id:str,body:CertificateEnvelope,client_id:str=Depends(authenticate_client)):
    try:return state().invocations.bind_verification(
      invocation_id,body.certificate,client_id=client_id).model_dump(mode="json")
    except KeyError:raise HTTPException(404,"invocation not found")
    except PermissionError as e:raise HTTPException(403,str(e))
    except ValueError as e:raise HTTPException(400,str(e))

@app.post("/v1/admin/forgejo/sync")
def sync_forgejo(body:ForgejoSyncBody,_admin:str=Depends(admin_token)):
    try:return state().forgejo.sync_org(
      base_url=body.base_url,org=body.org,token=body.token,page_size=body.page_size)
    except Exception as e:raise HTTPException(400,str(e))

@app.post("/v1/lab/ensure-fixture")
def lab_fixture(body:LabFixtureBody,client_id:str=Depends(authenticate_client)):
    if os.environ.get("QDW_FORGE_LAB_MODE")!="1":raise HTTPException(404)
    from .models import AssetKind,TransportSpec,TransportKind,Pricing
    a=CapabilityAsset(
      asset_id="fixture.echo",version="1.0.0",kind=AssetKind.TOOL,name="fixture.echo",
      capabilities=[body.capability],
      transport=TransportSpec(kind=TransportKind.HTTP,endpoint=os.environ.get(
        "QDW_FORGE_LAB_ECHO_URL","http://127.0.0.1:8914/invoke")),
      pricing=Pricing(per_call=0.001),metadata={"verification_policy":"fixture.echo"})
    state().store.register_asset(a)
    from .store import definition_hash
    state().store.activate(a.asset_id,a.version,certificate_id="lab-asset-cert",
                           certificate_hash=sha256_obj({"lab":"asset-cert","hash":definition_hash(a)}))
    return {"asset_id":a.asset_id,"version":a.version,"manifest_hash":definition_hash(a)}

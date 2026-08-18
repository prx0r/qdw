from __future__ import annotations
from typing import Any
import httpx

class FederationHTTPError(RuntimeError):
    def __init__(self,system:str,status:str,detail:str):
        self.system,self.status,self.detail=system,status,detail
        super().__init__(f"{system}:{status}: {detail}")

class BaseHTTPClient:
    def __init__(self,system:str,base_url:str,*,client:httpx.Client|None=None,timeout:float=20):
        self.system=system;self.base_url=base_url.rstrip("/")
        self._owned=client is None
        self.client=client or httpx.Client(timeout=timeout,follow_redirects=True)

    def close(self):
        if self._owned:self.client.close()

    def request(self,method,path,**kwargs)->httpx.Response:
        try:r=self.client.request(method,self.base_url+path,**kwargs)
        except httpx.TimeoutException as e:raise FederationHTTPError(self.system,"UNAVAILABLE","timeout") from e
        except httpx.HTTPError as e:raise FederationHTTPError(self.system,"UNAVAILABLE",type(e).__name__) from e
        if r.status_code in {401,403}:raise FederationHTTPError(self.system,"UNAUTHORIZED",str(r.status_code))
        if r.status_code>=500:raise FederationHTTPError(self.system,"UNAVAILABLE",str(r.status_code))
        if r.status_code>=400:raise FederationHTTPError(self.system,"FAILED",f"{r.status_code}: {r.text[:500]}")
        return r

class GitGoblinHTTPClient(BaseHTTPClient):
    def __init__(self,base_url,**kw):super().__init__("gitgoblin",base_url,**kw)
    def export_qdw(self,params:dict[str,Any]|None=None):
        return self.request("GET","/v1/export/qdw",params=params or {}).json()

class DellHTTPClient(BaseHTTPClient):
    def __init__(self,base_url,**kw):super().__init__("dell",base_url,**kw)
    def resolve(self,body:dict[str,Any]):
        return self.request("POST","/v1/federation/resolve",json=body).json()

class ForgeHTTPClient(BaseHTTPClient):
    def __init__(self,base_url,*,client_key:str,**kw):
        if not client_key:raise ValueError("Forge client key required")
        super().__init__("forge",base_url,**kw)
        self.client_key=client_key
    def request(self,method,path,**kwargs):
        headers=dict(kwargs.pop("headers",{}) or {})
        headers["X-Forge-Client-Key"]=self.client_key
        return super().request(method,path,headers=headers,**kwargs)
    def assets(self,capability):
        return self.request("GET","/v1/assets",params={"capability":capability}).json()
    def lease(self,body):
        return self.request("POST","/v1/leases",json=body).json()
    def invoke(self,body):
        return self.request("POST","/v1/invoke",json=body).json()
    def invocation(self,invocation_id):
        return self.request("GET",f"/v1/invocations/{invocation_id}").json()
    def bind_certificate(self,invocation_id,body):
        return self.request("POST",f"/v1/invocations/{invocation_id}/verification",json=body).json()

from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json
import httpx
from qdw.core import hash_object,utc_now
from .contracts import *

class FederationProtocolError(RuntimeError):pass

class BaseClient:
    def __init__(self,base_url:str,system_id:str,timeout:float=20):
        self.base_url=base_url.rstrip("/");self.system_id=system_id;self.timeout=timeout
    def _request(self,method,path,**kwargs):
        try:
            r=httpx.request(method,self.base_url+path,timeout=self.timeout,**kwargs)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"{self.system_id.upper()}_UNAVAILABLE: {exc}") from exc
        if r.status_code>=500:raise RuntimeError(f"{self.system_id.upper()}_UNAVAILABLE: HTTP {r.status_code}")
        if r.status_code in {401,403}:raise PermissionError(f"{self.system_id.upper()}_UNAUTHORIZED")
        if r.status_code>=400:raise FederationProtocolError(f"{self.system_id} HTTP {r.status_code}: {r.text[:500]}")
        return r

class GitGoblinClient(BaseClient):
    def export_qdw(self,params:dict|None=None)->dict:
        return self._request("GET","/v1/export/qdw",params=params or {}).json()

class DellClient(BaseClient):
    def resolve(self,body:dict)->dict:
        return self._request("POST","/v1/federation/resolve",json=body).json()

class ForgeClient(BaseClient):
    def assets(self,capability:str)->list[dict]:
        return self._request("GET","/v1/assets",params={"capability":capability}).json()
    def lease(self,body:dict)->dict:
        return self._request("POST","/v1/leases",json=body).json()
    def invoke(self,body:dict)->dict:
        return self._request("POST","/v1/invoke",json=body).json()
    def bind_certificate(self,invocation_id:str,body:dict)->dict:
        return self._request("POST",f"/v1/invocations/{invocation_id}/verification",json=body).json()

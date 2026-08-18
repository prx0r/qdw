from __future__ import annotations
import hmac,json,os
from fastapi import Header,HTTPException

def _keys()->dict[str,str]:
    raw=os.environ.get("QDW_FORGE_CLIENT_KEYS_JSON","").strip()
    if not raw:
        if os.environ.get("QDW_FORGE_LAB_MODE")=="1":
            return {"lab-client-key":"qdw-lab"}
        return {}
    parsed=json.loads(raw)
    if not isinstance(parsed,dict) or any(not k or not v for k,v in parsed.items()):
        raise RuntimeError("QDW_FORGE_CLIENT_KEYS_JSON must map api-key -> client-id")
    return {str(k):str(v) for k,v in parsed.items()}

def authenticate_client(x_forge_client_key:str|None=Header(default=None))->str:
    keys=_keys()
    if not keys:
        raise HTTPException(503,"Forge client authentication is not configured")
    if x_forge_client_key is None:
        raise HTTPException(401,"missing X-Forge-Client-Key")
    for secret,client_id in keys.items():
        if hmac.compare_digest(secret,x_forge_client_key):return client_id
    raise HTTPException(403,"invalid Forge client credential")

def admin_token(x_qdw_admin_token:str|None=Header(default=None))->str:
    expected=os.environ.get("QDW_FORGE_ADMIN_TOKEN","")
    if not expected and os.environ.get("QDW_FORGE_LAB_MODE")=="1":expected="lab-admin-token"
    if not expected:raise HTTPException(503,"Forge admin auth not configured")
    if not x_qdw_admin_token or not hmac.compare_digest(expected,x_qdw_admin_token):
        raise HTTPException(403,"invalid admin credential")
    return "admin"

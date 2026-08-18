from __future__ import annotations
import base64,secrets
from datetime import UTC,datetime
from urllib.parse import urlparse
import httpx,yaml
from .hashing import sha256_obj
from .models import CapabilityAsset

def now():return datetime.now(UTC).isoformat()

class ForgejoSync:
    def __init__(self,store,db,*,client:httpx.Client|None=None):
        self.store,self.db=store,db
        self.client=client or httpx.Client(timeout=20,follow_redirects=True)

    def _headers(self,token):return {"Authorization":f"token {token}"} if token else {}

    def _request(self,method,url,**kw):
        r=self.client.request(method,url,**kw)
        if r.status_code==404:return None
        r.raise_for_status();return r

    def _repos(self,base,org,token,page_size):
        page=1
        while True:
            r=self._request("GET",f"{base}/api/v1/orgs/{org}/repos",
                            headers=self._headers(token),params={"page":page,"limit":page_size})
            xs=r.json() if r else []
            if not xs:break
            for x in xs:yield x
            if len(xs)<page_size:break
            page+=1

    def _commit(self,base,org,name,ref,token):
        r=self._request("GET",f"{base}/api/v1/repos/{org}/{name}/commits/{ref}",
                        headers=self._headers(token))
        if r is None:raise ValueError("default ref cannot be resolved")
        sha=r.json().get("sha")
        if not sha or len(sha)<7:raise ValueError("invalid commit SHA")
        return sha

    def _manifest(self,base,org,name,commit,token):
        r=self._request("GET",f"{base}/api/v1/repos/{org}/{name}/contents/qdw.yaml",
                        headers=self._headers(token),params={"ref":commit})
        if r is None:return None,None
        raw=r.json();encoded=raw.get("content","")
        content=base64.b64decode(encoded).decode() if raw.get("encoding")=="base64" else encoded
        return yaml.safe_load(content),sha256_obj({"text":content})

    def sync_org(self,*,base_url,org,token,page_size=50):
        base=base_url.rstrip("/");seen=registered=0;errors=[]
        if page_size<=0 or page_size>100:raise ValueError("page_size outside 1..100")
        for repo in self._repos(base,org,token,page_size):
            seen+=1;name=repo["name"];rid="sync_"+secrets.token_hex(12)
            try:
                commit=self._commit(base,org,name,repo.get("default_branch") or "main",token)
                doc,md=self._manifest(base,org,name,commit,token)
                if doc is None:
                    self._receipt(rid,base,org,name,None,None,"NO_MANIFEST",None,None);continue
                if doc.get("schema_version") not in {None,"qdw.asset-manifest/1"}:
                    raise ValueError("unsupported qdw.yaml schema_version")
                for raw in doc.get("assets",[]):
                    asset=CapabilityAsset.model_validate(raw)
                    self.store.register_asset(asset)
                    self.store.bind_source(
                      asset.asset_id,asset.version,repository_uri=f"{base}/{org}/{name}",
                      source_commit=commit,manifest_path="qdw.yaml",manifest_digest=md)
                    registered+=1
                self._receipt(rid,base,org,name,commit,md,"REGISTERED",None,None)
            except Exception as exc:
                code=type(exc).__name__
                errors.append({"repo":name,"code":code,"detail":str(exc)})
                self._receipt(rid,base,org,name,None,None,"ERROR",code,str(exc))
        return {"repos_seen":seen,"assets_registered":registered,"errors":errors}

    def _receipt(self,rid,base,org,name,commit,md,status,code,detail):
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO forgejo_sync_receipts(
              sync_receipt_id,forgejo_base_url,org,repo_name,source_commit,manifest_path,
              manifest_digest,status,error_code,error_detail,observed_at
            ) VALUES(?,?,?,?,?,'qdw.yaml',?,?,?,?,?)""",
            (rid,base,org,name,commit,md,status,code,detail,now()))

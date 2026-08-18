from __future__ import annotations
import base64,os
from fastapi import FastAPI,HTTPException,Query

app=FastAPI(title="QDW Forgejo deterministic test double")
COUNT=int(os.environ.get("FORGEJO_STUB_REPOS","61"))

def repo(i):
    return {"name":f"repo-{i:03d}","default_branch":"main",
            "sha":f"{i:040x}"[-40:]}

@app.get("/health")
def health():return {"status":"ok","repos":COUNT}

@app.get("/api/v1/orgs/{org}/repos")
def repos(org:str,page:int=1,limit:int=50):
    xs=[repo(i) for i in range(COUNT)]
    start=(page-1)*limit
    return xs[start:start+limit]

@app.get("/api/v1/repos/{owner}/{name}/commits/{ref}")
def resolve(owner:str,name:str,ref:str):
    try:i=int(name.rsplit("-",1)[1])
    except Exception:raise HTTPException(404)
    return {"sha":repo(i)["sha"]}

@app.get("/api/v1/repos/{owner}/{name}/contents/qdw.yaml")
def contents(owner:str,name:str,ref:str|None=None):
    try:i=int(name.rsplit("-",1)[1])
    except Exception:raise HTTPException(404)
    expected=repo(i)["sha"]
    if ref!=expected:
        raise HTTPException(409,detail="qdw.yaml must be fetched at immutable commit SHA")
    doc=f"""schema_version: qdw.asset-manifest/1
assets:
  - asset_id: fixture.asset.{i}
    version: "1.0.0"
    name: fixture-{i}
    kind: TOOL
    capabilities: [fixture.echo]
    transport:
      kind: HTTP
      endpoint: http://127.0.0.1:8914/invoke
    pricing:
      per_call: 0.001
"""
    return {"name":"qdw.yaml","sha":f"manifest{i}","content":base64.b64encode(doc.encode()).decode(),"encoding":"base64"}

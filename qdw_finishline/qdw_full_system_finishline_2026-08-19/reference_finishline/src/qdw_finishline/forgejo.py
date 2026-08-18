from __future__ import annotations
from dataclasses import dataclass
from .hashing import digest
from .models import AssetManifest

@dataclass(frozen=True)
class Repo:
    owner:str;name:str;default_branch:str;commit:str;qdw_doc:dict

class ForgejoService:
    """Deterministic Forgejo fixture with pagination and commit-pinned manifest reads."""
    def __init__(self,repos=None):
        self.repos=list(repos or [])
        self.read_log=[]
    def list_org_repos(self,org,page=1,limit=50):
        xs=[r for r in self.repos if r.owner==org]
        start=(page-1)*limit;return xs[start:start+limit]
    def resolve_ref(self,owner,repo,ref):
        r=next(x for x in self.repos if x.owner==owner and x.name==repo)
        if ref not in {r.default_branch,r.commit}:raise KeyError(ref)
        return r.commit
    def get_qdw(self,owner,repo,commit):
        r=next(x for x in self.repos if x.owner==owner and x.name==repo)
        if commit!=r.commit:raise ValueError("manifest must be read at immutable commit")
        self.read_log.append((owner,repo,commit))
        return r.qdw_doc

class ForgejoSync:
    def __init__(self,forgejo:ForgejoService,forge):
        self.forgejo=forgejo;self.forge=forge;self.receipts=[]
    def sync_org(self,org,limit=50):
        page=1;count=0
        while True:
            repos=self.forgejo.list_org_repos(org,page,limit)
            if not repos:break
            for repo in repos:
                commit=self.forgejo.resolve_ref(org,repo.name,repo.default_branch)
                doc=self.forgejo.get_qdw(org,repo.name,commit)
                doc_digest=digest(doc)
                for a in doc.get("assets",[]):
                    m=AssetManifest(
                      a["asset_id"],str(a["version"]),a.get("name",a["asset_id"]),
                      tuple(a.get("capabilities",[])),float(a.get("pricing",{}).get("per_call",0)),
                      a.get("transport","fixture"),f"forgejo://{org}/{repo.name}",commit,doc_digest)
                    self.forge.register_asset(m);count+=1
                self.receipts.append({"repo":repo.name,"commit":commit,"manifest_digest":doc_digest})
            page+=1
        return {"assets":count,"repos":len(self.receipts)}

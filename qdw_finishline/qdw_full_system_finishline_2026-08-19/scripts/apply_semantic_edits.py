from __future__ import annotations
import argparse
from pathlib import Path

def replace_once(path:Path,old:str,new:str):
    text=path.read_text()
    count=text.count(old)
    if count!=1:
        raise RuntimeError(f"{path}: expected exactly one semantic anchor, found {count}")
    path.write_text(text.replace(old,new,1))

def patch_qdw(root:Path):
    system=root/"qdw/src/qdw/system.py"
    candidates=[
'''        # Federation adapter layer: wraps external intelligence/capability services.
        from qdw.federation.service import FederationService
        from qdw.federation.store import FederationStore
        self.federation_store=FederationStore(self.db,self.ledger)
        self.federation=FederationService(system=self,store=self.federation_store)
''',
'''        from qdw.federation.service import FederationService
        from qdw.federation.store import FederationStore
        self.federation_store=FederationStore(self.db,self.ledger)
        self.federation=FederationService(system=self,store=self.federation_store)
'''
    ]
    old=next((x for x in candidates if x in system.read_text()),None)
    if old is None:
        raise RuntimeError("QDW federation composition anchor drifted")
    new='''        from qdw.federation.composition import compose_federation
        fed=compose_federation(self,repo_root=self.repo_root)
        self.federation_store=fed["store"]
        self.federation=fed["service"]
        self.federation_certificates=fed["certificates"]
        self.federation_verification_policies=fed["policies"]
        self.federation_runtime=fed["runtime"]
'''
    replace_once(system,old,new)

    api=root/"qdw/src/qdw/interfaces/api.py"
    text=api.read_text()
    include="app.include_router(federation_router)"
    if include not in text:
        anchor='app = FastAPI(title="QDW API", lifespan=lifespan)'
        addition=anchor+'\n\nfrom qdw.interfaces.federation_api import router as federation_router\napp.include_router(federation_router)'
        replace_once(api,anchor,addition)

    fake=root/"qdw/src/qdw/federation/forge_client.py"
    if fake.exists():
        fake.unlink()

def patch_gitgoblin(root:Path):
    api=root/"gitgoblin/gitgoblin/api.py"
    text=api.read_text()
    import_line="from .integrations.qdw import build_export"
    if import_line not in text:
        anchor="from .integrations.cuntgoblin import signal_to_market_observations, opportunity_to_cuntgoblin"
        if anchor not in text:
            raise RuntimeError("GitGoblin integration import anchor drifted")
        text=text.replace(anchor,anchor+"\n"+import_line,1)
    if '"/v1/export/qdw"' not in text:
        text=text.rstrip()+'''


@app.get("/v1/export/qdw")
def export_qdw(sector: str | None = None, cursor: str | None = None, limit: int = 1000):
    return build_export(store, sector=sector, cursor=cursor, limit=min(limit, 5000))
'''
    api.write_text(text)

def patch_dell(root:Path):
    decision=root/"dell/app/services/decision.py"
    old='''    # Output price can be None (unknown) — cost is still calculable from input
    output_per_m = candidate.output_per_m if candidate.output_per_m is not None else 0
'''
    new='''    if workload.output_tokens_per_request > 0 and candidate.output_per_m is None:
        return None
    output_per_m = candidate.output_per_m or 0.0
'''
    replace_once(decision,old,new)

    api=root/"dell/app/api_canonical.py"
    text=api.read_text()
    import_line="from app.federation import federation_resolve, load_endpoints"
    if import_line not in text:
        anchor="from verification import get_verification_status"
        if anchor not in text:
            raise RuntimeError("Dell API import anchor drifted")
        text=text.replace(anchor,anchor+"\n"+import_line,1)
    if '"/v1/federation/resolve"' not in text:
        text=text.rstrip()+'''


@app.post("/v1/federation/resolve")
def qdw_federation_resolve(body: dict):
    data=_load_all()
    conn=canonical_db.connect()
    canonical_db.migrate(conn)
    try:
        endpoints=load_endpoints(conn)
    finally:
        conn.close()
    return federation_resolve(body,data["offers"],endpoints)
'''
    api.write_text(text)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="worktrees"); a=ap.parse_args()
    root=Path(a.root).resolve()
    patch_qdw(root); patch_gitgoblin(root); patch_dell(root)
    print("Semantic edits applied successfully.")
if __name__=="__main__":
    main()

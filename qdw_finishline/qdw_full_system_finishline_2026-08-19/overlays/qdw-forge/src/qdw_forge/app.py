from __future__ import annotations
import os
from pathlib import Path
from .db import Database
from .routing import VerifiedProfileRouter
from .tokens import LeaseTokenSigner
from .invokers import Dispatcher
from .leases import LeaseService
from .store import ForgeStore
from .invocation import InvocationService
from .federation import QDWCertificateResolver
from .forgejo import ForgejoSync
from .strict_migrations import apply_finishline_migrations

class ForgeApp:
    def __init__(self,db_path:str|Path,secret:bytes,qdw_certificate_base_url:str):
        self.db=Database(db_path)
        # Establish the reviewed legacy baseline, then all subsequent evolution is strict numbered migration.
        self.db.migrate()
        apply_finishline_migrations(self.db)
        self.store=ForgeStore(self.db)
        self.router=VerifiedProfileRouter(self.store)
        self.signer=LeaseTokenSigner(secret)
        self.leases=LeaseService(self.db,self.router,self.signer)
        self.dispatcher=Dispatcher()
        self.certificate_resolver=QDWCertificateResolver(qdw_certificate_base_url)
        self.invocations=InvocationService(
          self.db,self.store,self.leases,self.router,self.dispatcher,self.certificate_resolver)
        self.forgejo=ForgejoSync(self.store,self.db)

def from_env()->ForgeApp:
    secret=os.environ.get("QDW_FORGE_LEASE_SECRET","").encode()
    if len(secret)<32:
        if os.environ.get("QDW_FORGE_LAB_MODE")!="1":
            raise RuntimeError("QDW_FORGE_LEASE_SECRET must be >=32 bytes")
        secret=b"dev-only-not-for-production-000000000000"
    qdw=os.environ.get("QDW_CERTIFICATE_BASE_URL","").strip()
    if not qdw:
        if os.environ.get("QDW_FORGE_LAB_MODE")=="1":qdw="http://127.0.0.1:8910"
        else:raise RuntimeError("QDW_CERTIFICATE_BASE_URL required")
    return ForgeApp(os.environ.get("QDW_FORGE_DB","data/forge.db"),secret,qdw)

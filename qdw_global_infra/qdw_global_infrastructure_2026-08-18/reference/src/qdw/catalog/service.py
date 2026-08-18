from __future__ import annotations
from qdw.core.db import Database

class GlobalCatalog:
    """Backstage-like read model over QDW's canonical DB; not a second source of truth."""
    def __init__(self,db:Database):self.db=db

    def search(self,query:str,limit:int=50)->dict:
        like=f"%{query.lower()}%"
        with self.db.connect() as con:
            entities=[dict(r) for r in con.execute("""SELECT * FROM entities
                WHERE lower(canonical_name) LIKE ? LIMIT ?""",(like,limit)).fetchall()]
            ideas=[dict(r) for r in con.execute("""SELECT * FROM ideas
                WHERE lower(canonical_title) LIKE ? OR lower(summary) LIKE ? LIMIT ?""",(like,like,limit)).fetchall()]
            products=[dict(r) for r in con.execute("""SELECT * FROM products
                WHERE lower(name) LIKE ? LIMIT ?""",(like,limit)).fetchall()]
            resources=[dict(r) for r in con.execute("""SELECT * FROM resources
                WHERE lower(name) LIKE ? LIMIT ?""",(like,limit)).fetchall()]
        return {"entities":entities,"ideas":ideas,"products":products,"resources":resources}

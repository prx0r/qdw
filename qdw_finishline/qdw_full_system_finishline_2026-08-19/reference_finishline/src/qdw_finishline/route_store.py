from __future__ import annotations
import sqlite3
from pathlib import Path
from .models import Route,Ref

SCHEMA = '''
CREATE TABLE IF NOT EXISTS routes(
 route_id TEXT PRIMARY KEY, source TEXT NOT NULL, capability TEXT NOT NULL,
 fixed_cost REAL, quality REAL, active INTEGER NOT NULL,
 ref_system TEXT, ref_kind TEXT, ref_id TEXT, ref_version TEXT, ref_digest TEXT
);
'''

class RouteStore:
    def __init__(self,path):
        self.path=str(path); Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:c.executescript(SCHEMA)
    def connect(self):
        c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;return c
    def save(self,r:Route):
        ref=r.external_ref
        with self.connect() as c:
            c.execute('''INSERT INTO routes VALUES(?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(route_id) DO UPDATE SET source=excluded.source,capability=excluded.capability,
              fixed_cost=excluded.fixed_cost,quality=excluded.quality,active=excluded.active,
              ref_system=excluded.ref_system,ref_kind=excluded.ref_kind,ref_id=excluded.ref_id,
              ref_version=excluded.ref_version,ref_digest=excluded.ref_digest''',
              (r.route_id,r.source,r.capability,r.fixed_cost,r.quality,int(r.active),
               ref.system if ref else None,ref.kind if ref else None,ref.object_id if ref else None,
               ref.version if ref else None,ref.digest_value if ref else None))
    def load(self,route_id):
        with self.connect() as c:x=c.execute("SELECT * FROM routes WHERE route_id=?",(route_id,)).fetchone()
        if not x:raise KeyError(route_id)
        ref=None
        if x["ref_system"]:ref=Ref(x["ref_system"],x["ref_kind"],x["ref_id"],x["ref_version"],x["ref_digest"])
        return Route(x["route_id"],x["source"],x["capability"],x["fixed_cost"],x["quality"],bool(x["active"]),ref)
    def all(self):
        with self.connect() as c:ids=[x[0] for x in c.execute("SELECT route_id FROM routes ORDER BY route_id")]
        return [self.load(i) for i in ids]

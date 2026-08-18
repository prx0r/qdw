from __future__ import annotations
import json,sqlite3
from pathlib import Path
from .models import AttemptState

SCHEMA='''
CREATE TABLE IF NOT EXISTS attempts(
 attempt_id TEXT PRIMARY KEY,
 capability TEXT NOT NULL,
 state TEXT NOT NULL,
 route_id TEXT,
 external_invocation_id TEXT,
 output_digest TEXT,
 certificate_id TEXT,
 cost REAL,
 request_json TEXT NOT NULL,
 error TEXT
);
CREATE TABLE IF NOT EXISTS world_observations(
 source TEXT NOT NULL, external_id TEXT NOT NULL, digest TEXT NOT NULL, payload_json TEXT NOT NULL,
 PRIMARY KEY(source,external_id,digest)
);
CREATE TABLE IF NOT EXISTS proposals(
 source TEXT NOT NULL, external_id TEXT NOT NULL, digest TEXT NOT NULL, payload_json TEXT NOT NULL,
 authority TEXT NOT NULL CHECK(authority='ADVISORY'),
 PRIMARY KEY(source,external_id,digest)
);
CREATE TABLE IF NOT EXISTS costs(
 cost_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE, amount REAL NOT NULL, evidence_ref TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learning(
 route_id TEXT PRIMARY KEY, alpha REAL NOT NULL DEFAULT 1, beta REAL NOT NULL DEFAULT 1
);
'''

class RuntimeStore:
    def __init__(self,path):
        self.path=str(path);Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:c.executescript(SCHEMA)
    def connect(self):
        c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row;return c
    def create_attempt(self,attempt_id,capability,request):
        with self.connect() as c:
            c.execute("INSERT INTO attempts(attempt_id,capability,state,request_json) VALUES(?,?,?,?)",
                      (attempt_id,capability,AttemptState.DISCOVERING.value,json.dumps(request,sort_keys=True)))
    def set(self,attempt_id,state:AttemptState,**fields):
        allowed={"route_id","external_invocation_id","output_digest","certificate_id","cost","error"}
        bad=set(fields)-allowed
        if bad:raise KeyError(bad)
        cols=["state=?"];vals=[state.value]
        for k,v in fields.items():cols.append(f"{k}=?");vals.append(v)
        vals.append(attempt_id)
        with self.connect() as c:c.execute(f"UPDATE attempts SET {','.join(cols)} WHERE attempt_id=?",vals)
    def get(self,attempt_id):
        with self.connect() as c:r=c.execute("SELECT * FROM attempts WHERE attempt_id=?",(attempt_id,)).fetchone()
        if not r:raise KeyError(attempt_id)
        return dict(r)
    def add_observation(self,source,external_id,digest_value,payload):
        with self.connect() as c:
            cur=c.execute("INSERT OR IGNORE INTO world_observations VALUES(?,?,?,?)",
                          (source,external_id,digest_value,json.dumps(payload,sort_keys=True)))
            return cur.rowcount
    def add_proposal(self,source,external_id,digest_value,payload):
        with self.connect() as c:
            cur=c.execute("INSERT OR IGNORE INTO proposals VALUES(?,?,?,?, 'ADVISORY')",
                          (source,external_id,digest_value,json.dumps(payload,sort_keys=True)))
            return cur.rowcount
    def commit_result(self,attempt_id,route_id,success,cost,evidence_ref,certificate_id):
        with self.connect() as c:
            row=c.execute("SELECT state FROM attempts WHERE attempt_id=?",(attempt_id,)).fetchone()
            if not row:raise KeyError(attempt_id)
            if row["state"]==AttemptState.COMMITTED.value:return
            c.execute("INSERT OR IGNORE INTO learning(route_id,alpha,beta) VALUES(?,1,1)",(route_id,))
            if success:c.execute("UPDATE learning SET alpha=alpha+1 WHERE route_id=?",(route_id,))
            else:c.execute("UPDATE learning SET beta=beta+1 WHERE route_id=?",(route_id,))
            c.execute("INSERT OR IGNORE INTO costs(cost_id,attempt_id,amount,evidence_ref) VALUES(?,?,?,?)",
                      ("cost_"+attempt_id,attempt_id,cost,evidence_ref))
            c.execute("UPDATE attempts SET state=?,cost=?,certificate_id=? WHERE attempt_id=?",
                      (AttemptState.COMMITTED.value,cost,certificate_id,attempt_id))

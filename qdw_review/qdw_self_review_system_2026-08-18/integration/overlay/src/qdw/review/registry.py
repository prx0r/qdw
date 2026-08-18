from __future__ import annotations
import json
from pathlib import Path
from qdw.core import hash_object,utc_now
from qdw.core.db import Database

class ReviewerRegistry:
    def __init__(self,db:Database):self.db=db

    def register(self,path:str|Path):
        m=json.loads(Path(path).read_text())
        rid,version=m["contractor_id"],m["version"]
        h=hash_object(m)
        with self.db.tx(immediate=True) as con:
            old=con.execute(
                "SELECT definition_hash FROM reviewer_definitions WHERE reviewer_id=? AND version=?",
                (rid,version)
            ).fetchone()
            if old and old["definition_hash"] != h:
                raise ValueError("reviewer version immutable; bump version")
            con.execute("""INSERT OR IGNORE INTO reviewer_definitions(
                reviewer_id,version,definition_hash,manifest_json,status,created_at
            ) VALUES(?,?,?,?, 'CANDIDATE',?)""",(rid,version,h,json.dumps(m,sort_keys=True),utc_now()))
        return rid,version,h

    def activate(self,reviewer_id:str,version:str,fixture_certificate_id:str)->None:
        # Integration task: resolve a contractor/reviewer fixture certificate bound to exact reviewer hash.
        # Do not replace this with a boolean.
        raise NotImplementedError("wire to certified reviewer fixture")

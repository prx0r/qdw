from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
import json
from qdw.core import canonical_json

class FixPlanner:
    def __init__(self,graphs,db):
        self.graphs,self.db=graphs,db

    def create_fix_graph(self,review_run_id:str,findings:list[dict])->str:
        groups=defaultdict(list)
        for f in findings:
            path=""
            with self.db.connect() as con:
                ev=con.execute("SELECT path FROM review_evidence WHERE finding_id=? ORDER BY created_at LIMIT 1",
                               (f["finding_id"],)).fetchone()
                path=(ev["path"] if ev and ev["path"] else "unknown")
            subsystem=path.split("/")[2] if path.startswith("src/qdw/") and len(path.split("/"))>2 else path.split("/")[0]
            groups[subsystem].append(f)

        gid=self.graphs.create_graph()
        for subsystem,fs in sorted(groups.items()):
            finding_ids=sorted(x["finding_id"] for x in fs)
            acceptance=[]
            with self.db.connect() as con:
                for fid in finding_ids:
                    rows=con.execute("""SELECT a.spec_hash,a.spec_json FROM review_finding_acceptance fa
                        JOIN review_acceptance_specs a ON a.acceptance_spec_id=fa.acceptance_spec_id
                        WHERE fa.finding_id=?""",(fid,)).fetchall()
                    acceptance.extend({"spec_hash":r["spec_hash"],"spec_json":r["spec_json"]} for r in rows)
            payload={
                "review_run_id":review_run_id,
                "finding_ids":finding_ids,
                "subsystem":subsystem,
                "acceptance_specs":acceptance,
                "rule":"Do not weaken/delete/skip frozen acceptance. Fix production code, run exact specs, record receipts.",
            }
            self.graphs.add_node(
                gid,"review_fix",f"Fix peer-review blockers: {subsystem}",payload,
                quality_floor=0.85,max_retries=2,
                idempotency_key="fix:"+sha256(canonical_json(payload)).hexdigest()[:24],
            )
        if hasattr(self.graphs,"freeze"):self.graphs.freeze(gid)
        else:raise RuntimeError("fix planning requires hardened graph freeze")
        return gid

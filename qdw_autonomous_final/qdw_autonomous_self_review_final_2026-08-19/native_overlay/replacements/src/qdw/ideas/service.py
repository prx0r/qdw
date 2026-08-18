"""IdeaService v2 — stable fingerprints, append-only decisions/cemetery episodes, atomic provenance."""
from __future__ import annotations
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now

def idea_fingerprint(problem_key,solution_key,customer,product_form):
    return hash_object({
        "problem_key":" ".join(problem_key.lower().split()),
        "solution_key":" ".join(solution_key.lower().split()),
        "customer":" ".join(customer.lower().split()),
        "product_form":product_form.lower().strip(),
    })

class IdeaService:
    def __init__(self,db,ledger):
        self.db,self.ledger=db,ledger

    def propose(self,*,problem_key,solution_key,title,summary,customer,product_form,opportunity_id=None):
        fp=idea_fingerprint(problem_key,solution_key,customer,product_form)
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT idea_id FROM ideas WHERE fingerprint=?",(fp,)).fetchone()
            if old:return old["idea_id"],False
            iid=new_id("idea");now=utc_now()
            con.execute("""INSERT INTO ideas(
                idea_id,opportunity_id,problem_key,solution_key,canonical_title,summary,customer,
                product_form,fingerprint,status,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,'PROPOSED',?,?)""",
            (iid,opportunity_id,problem_key,solution_key,title,summary,customer,product_form,fp,now,now))
            self.ledger.append_in_tx(con,"idea.proposed","idea",iid,{"fingerprint":fp})
        return iid,True

    def relate(self,from_id,relation_type,to_id,rationale=""):
        if from_id==to_id:raise ValueError("self idea relation")
        with self.db.tx(immediate=True) as con:
            old=con.execute("""SELECT relation_id FROM idea_relations
                WHERE from_idea_id=? AND relation_type=? AND to_idea_id=?""",
                (from_id,relation_type,to_id)).fetchone()
            if old:return old["relation_id"]
            rid=new_id("idearel")
            con.execute("""INSERT INTO idea_relations(
                relation_id,from_idea_id,relation_type,to_idea_id,rationale,created_at
            ) VALUES(?,?,?,?,?,?)""",(rid,from_id,relation_type,to_id,rationale,utc_now()))
            self.ledger.append_in_tx(con,"idea.related","idea_relation",rid,{
                "from":from_id,"to":to_id,"type":relation_type,
            })
        return rid

    def transfer(self,idea_id,target_form,*,solution_key=None,title=None):
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM ideas WHERE idea_id=?",(idea_id,)).fetchone()
        if not row:raise KeyError(idea_id)
        child,_=self.propose(
            problem_key=row["problem_key"],solution_key=solution_key or row["solution_key"],
            title=title or f"{row['canonical_title']} ({target_form})",summary=row["summary"],
            customer=row["customer"],product_form=target_form,opportunity_id=row["opportunity_id"],
        )
        if child!=idea_id:self.relate(child,"reimplements",idea_id,f"Transferred to {target_form}")
        return child

    def decide(self,idea_id,stage,decision,score,reason_codes,snapshot,*,evidence_ref,reviewer_id,reviewer_version):
        if not evidence_ref:raise ValueError("idea decision requires evidence_ref")
        did=new_id("ideadec");snap_hash=hash_object(snapshot)
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM ideas WHERE idea_id=?",(idea_id,)).fetchone():
                raise KeyError(idea_id)
            con.execute("""INSERT INTO idea_decisions(
                decision_id,idea_id,stage,decision,score_json,reason_codes_json,snapshot_hash,created_at,
                evidence_ref,reviewer_id,reviewer_version
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (did,idea_id,stage,decision,canonical_json(score).decode(),
             canonical_json(reason_codes).decode(),snap_hash,utc_now(),evidence_ref,reviewer_id,reviewer_version))
            con.execute("UPDATE ideas SET status=?,updated_at=? WHERE idea_id=?",(decision,utc_now(),idea_id))
            self.ledger.append_in_tx(con,"idea.decided","idea",idea_id,{
                "decision":decision,"stage":stage,"snapshot_hash":snap_hash,"evidence_ref":evidence_ref,
            })
        return did

    def bury(self,idea_id,reason_code,*,assumptions,revisit_triggers,next_review_at=None):
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM ideas WHERE idea_id=?",(idea_id,)).fetchone():
                raise KeyError(idea_id)
            prior=con.execute("""SELECT * FROM cemetery_entries WHERE idea_id=?
                ORDER BY episode_no DESC LIMIT 1""",(idea_id,)).fetchone()
            if prior and prior["status"]=="DORMANT":
                raise ValueError("idea already dormant")
            episode=(prior["episode_no"]+1) if prior else 1
            cid=new_id("grave")
            con.execute("""INSERT INTO cemetery_entries(
                cemetery_id,idea_id,episode_no,reason_code,assumptions_json,revisit_triggers_json,
                buried_at,next_review_at,status,supersedes_cemetery_id
            ) VALUES(?,?,?,?,?,?,?,?,'DORMANT',?)""",
            (cid,idea_id,episode,reason_code,canonical_json(assumptions).decode(),
             canonical_json(revisit_triggers).decode(),utc_now(),next_review_at,
             prior["cemetery_id"] if prior else None))
            con.execute("UPDATE ideas SET status='DORMANT',updated_at=? WHERE idea_id=?",(utc_now(),idea_id))
            self.ledger.append_in_tx(con,"idea.buried","idea",idea_id,{
                "cemetery_id":cid,"episode_no":episode,"reason_code":reason_code,
            })
        return cid

    def revive(self,idea_id,trigger):
        with self.db.tx(immediate=True) as con:
            row=con.execute("""SELECT * FROM cemetery_entries WHERE idea_id=? AND status='DORMANT'
                ORDER BY episode_no DESC LIMIT 1""",(idea_id,)).fetchone()
            if not row:raise ValueError("idea is not dormant")
            con.execute("""UPDATE cemetery_entries SET status='REVIVED',revived_at=?
                WHERE cemetery_id=?""",(utc_now(),row["cemetery_id"]))
            con.execute("UPDATE ideas SET status='PROPOSED',updated_at=? WHERE idea_id=?",(utc_now(),idea_id))
            self.ledger.append_in_tx(con,"idea.revived","idea",idea_id,{
                "cemetery_id":row["cemetery_id"],"trigger":trigger,
            })

    def cemetery(self):
        with self.db.connect() as con:
            rows=con.execute("""SELECT c.*,i.canonical_title FROM cemetery_entries c
                JOIN ideas i ON i.idea_id=c.idea_id ORDER BY c.buried_at DESC""").fetchall()
        out=[]
        for row in rows:
            d=dict(row)
            d["assumptions"]=json.loads(d.pop("assumptions_json") or "{}")
            d["revisit_triggers"]=json.loads(d.pop("revisit_triggers_json") or "[]")
            out.append(d)
        return out

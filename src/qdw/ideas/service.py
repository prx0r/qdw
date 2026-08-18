"""IdeaService — propose, relate, transfer, decide, bury, revive."""

from __future__ import annotations

import json
from typing import Any

from qdw.core import canonical_json, hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


def idea_fingerprint(problem_key: str, solution_key: str, customer: str, product_form: str) -> str:
    return hash_object({
        "problem_key": " ".join(problem_key.lower().split()),
        "solution_key": " ".join(solution_key.lower().split()),
        "customer": " ".join(customer.lower().split()),
        "product_form": product_form.lower().strip(),
    })


class IdeaService:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def propose(self, *, problem_key: str, solution_key: str, title: str, summary: str,
                customer: str, product_form: str, opportunity_id: str | None = None) -> tuple[str, bool]:
        fp = idea_fingerprint(problem_key, solution_key, customer, product_form)
        with self.db.tx(immediate=True) as con:
            old = con.execute("SELECT idea_id FROM ideas WHERE fingerprint=?", (fp,)).fetchone()
            if old:
                return old["idea_id"], False
            iid = new_id("idea")
            now = utc_now()
            con.execute(
                """INSERT INTO ideas(idea_id,opportunity_id,problem_key,solution_key,canonical_title,summary,
                customer,product_form,fingerprint,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,'PROPOSED',?,?)""",
                (iid, opportunity_id, problem_key, solution_key, title, summary, customer, product_form, fp, now, now),
            )
        self.ledger.append("idea.proposed", "idea", iid, {"fingerprint": fp, "problem_key": problem_key})
        return iid, True

    def relate(self, from_id: str, relation_type: str, to_id: str, rationale: str = "") -> str:
        if from_id == to_id:
            raise ValueError("self idea relation")
        rid = new_id("idearel")
        with self.db.tx(immediate=True) as con:
            old = con.execute(
                """SELECT relation_id FROM idea_relations WHERE from_idea_id=? AND relation_type=? AND to_idea_id=?""",
                (from_id, relation_type, to_id),
            ).fetchone()
            if old:
                return old["relation_id"]
            con.execute(
                """INSERT INTO idea_relations(relation_id,from_idea_id,relation_type,to_idea_id,rationale,created_at)
                VALUES(?,?,?,?,?,?)""",
                (rid, from_id, relation_type, to_id, rationale, utc_now()),
            )
        self.ledger.append("idea.related", "idea_relation", rid, {"from": from_id, "to": to_id, "type": relation_type})
        return rid

    def transfer(self, idea_id: str, target_form: str, *, solution_key: str | None = None,
                 title: str | None = None) -> str:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM ideas WHERE idea_id=?", (idea_id,)).fetchone()
            if not r:
                raise KeyError(idea_id)
        child, created = self.propose(
            problem_key=r["problem_key"], solution_key=solution_key or r["solution_key"],
            title=title or f"{r['canonical_title']} ({target_form})", summary=r["summary"],
            customer=r["customer"], product_form=target_form, opportunity_id=r["opportunity_id"],
        )
        if child != idea_id:
            self.relate(child, "reimplements", idea_id, f"Transferred to {target_form}")
        return child

    def decide(self, idea_id: str, stage: str, decision: str, score: dict[str, Any],
               reason_codes: list[str], snapshot: dict[str, Any]) -> str:
        did = new_id("ideadec")
        snap_hash = hash_object(snapshot)
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM ideas WHERE idea_id=?", (idea_id,)).fetchone():
                raise KeyError(idea_id)
            con.execute(
                """INSERT INTO idea_decisions(decision_id,idea_id,stage,decision,score_json,reason_codes_json,
                snapshot_hash,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (did, idea_id, stage, decision, canonical_json(score).decode(),
                 canonical_json(reason_codes).decode(), snap_hash, utc_now()),
            )
            con.execute("UPDATE ideas SET status=?,updated_at=? WHERE idea_id=?", (decision, utc_now(), idea_id))
        self.ledger.append("idea.decided", "idea", idea_id,
                           {"decision": decision, "stage": stage, "snapshot_hash": snap_hash})
        return did

    def bury(self, idea_id: str, reason_code: str, *, assumptions: dict[str, Any],
             revisit_triggers: list[dict[str, Any]], next_review_at: str | None = None) -> str:
        cid = new_id("grave")
        with self.db.tx(immediate=True) as con:
            existing = con.execute(
                "SELECT cemetery_id FROM cemetery_entries WHERE idea_id=?", (idea_id,)
            ).fetchone()
            if existing:
                raise ValueError(f"idea {idea_id} is already buried (cemetery_id={existing['cemetery_id']})")
            if not con.execute("SELECT 1 FROM ideas WHERE idea_id=?", (idea_id,)).fetchone():
                raise KeyError(idea_id)
            con.execute(
                """INSERT INTO cemetery_entries(cemetery_id,idea_id,reason_code,assumptions_json,
                revisit_triggers_json,buried_at,next_review_at,status) VALUES(?,?,?,?,?,?,?,'DORMANT')""",
                (cid, idea_id, reason_code, canonical_json(assumptions).decode(),
                 canonical_json(revisit_triggers).decode(), utc_now(), next_review_at),
            )
            con.execute("UPDATE ideas SET status='DORMANT',updated_at=? WHERE idea_id=?", (utc_now(), idea_id))
        self.ledger.append("idea.buried", "idea", idea_id, {"reason_code": reason_code})
        return cid

    def revive(self, idea_id: str, trigger: dict[str, Any]) -> None:
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                """UPDATE cemetery_entries SET status='REVIVED',revived_at=? WHERE idea_id=? AND status='DORMANT'""",
                (utc_now(), idea_id),
            ).rowcount
            if changed != 1:
                raise ValueError("idea is not dormant")
            con.execute("UPDATE ideas SET status='PROPOSED',updated_at=? WHERE idea_id=?", (utc_now(), idea_id))
        self.ledger.append("idea.revived", "idea", idea_id, {"trigger": trigger})

    def cemetery(self) -> list[dict]:
        with self.db.connect() as con:
            rows = con.execute(
                """SELECT c.*,i.canonical_title FROM cemetery_entries c JOIN ideas i ON i.idea_id=c.idea_id
                ORDER BY c.buried_at DESC""",
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["assumptions"] = json.loads(d.pop("assumptions_json"))
            d["revisit_triggers"] = json.loads(d.pop("revisit_triggers_json"))
            out.append(d)
        return out

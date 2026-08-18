"""ProductRegistry — create, release, passport, outcomes."""

from __future__ import annotations

import json
from typing import Any

from qdw.core import canonical_json, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class ProductRegistry:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def create(self, name: str, slug: str, product_type: str, *, idea_id: str | None = None,
               factory_id: str | None = None, factory_version: str | None = None,
               build_run_id: str | None = None) -> str:
        pid = new_id("prod")
        now = utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO products(product_id,idea_id,factory_id,factory_version,name,slug,product_type,
                status,build_run_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'BUILDING',?,?,?)""",
                (pid, idea_id, factory_id, factory_version, name, slug, product_type, build_run_id, now, now),
            )
        self.ledger.append("product.created", "product", pid, {"name": name, "slug": slug, "idea_id": idea_id})
        return pid

    def release(self, product_id: str, certificate_id: str) -> None:
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                """UPDATE products SET status='RELEASED',certificate_id=?,released_at=?,updated_at=?
                WHERE product_id=? AND status!='RELEASED'""",
                (certificate_id, utc_now(), utc_now(), product_id),
            ).rowcount
            if changed != 1:
                raise ValueError("product missing or already released")
        self.ledger.append("product.released", "product", product_id, {"certificate_id": certificate_id})

    def passport(self, product_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            p = con.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
            if not p:
                raise KeyError(product_id)
            idea = con.execute("SELECT * FROM ideas WHERE idea_id=?", (p["idea_id"],)).fetchone() if p["idea_id"] else None
            genomes = con.execute(
                "SELECT genome_hash,genome_json,created_at FROM factory_genomes WHERE product_id=?",
                (product_id,),
            ).fetchall()
            outcomes = con.execute(
                "SELECT * FROM outcome_events WHERE product_id=? ORDER BY occurred_at", (product_id,),
            ).fetchall()
        return {
            "product": dict(p),
            "idea": dict(idea) if idea else None,
            "factory_genomes": [{**dict(g), "genome": json.loads(g["genome_json"])} for g in genomes],
            "outcomes": [dict(x) for x in outcomes],
        }

    def outcome(self, product_id: str, metric: str, *, value: float | None = None,
                text_value: str | None = None, unit: str | None = None, source: str = "manual",
                evidence: dict[str, Any] | None = None, occurred_at: str | None = None) -> str:
        if value is None and text_value is None:
            raise ValueError("outcome requires value or text")
        oid = new_id("outcomeevent")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO outcome_events(outcome_event_id,product_id,metric,value,text_value,unit,source,
                occurred_at,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (oid, product_id, metric, value, text_value, unit, source, occurred_at or utc_now(),
                 canonical_json(evidence or {}).decode(), utc_now()),
            )
        self.ledger.append("product.outcome", "outcome_event", oid, {"product_id": product_id, "metric": metric})
        return oid

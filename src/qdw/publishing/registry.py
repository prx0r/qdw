"""DistributionRegistry — data-driven distribution surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qdw.core import canonical_json, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class DistributionRegistry:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def register_manifest(self, path: str | Path) -> str:
        m = json.loads(Path(path).read_text(encoding="utf-8"))
        sid = m["surface_id"]
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO distribution_surfaces(surface_id,name,kind,manifest_json,status,created_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(surface_id) DO UPDATE SET name=excluded.name,kind=excluded.kind,
                manifest_json=excluded.manifest_json,status=excluded.status""",
                (sid, m["name"], m["kind"], canonical_json(m).decode(), m.get("status", "ACTIVE"), utc_now()),
            )
        self.ledger.append("distribution.registered", "distribution_surface", sid, {"kind": m["kind"]})
        return sid

    def eligible(self, product_type: str) -> list[dict[str, Any]]:
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM distribution_surfaces WHERE status='ACTIVE'").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            m = json.loads(d["manifest_json"])
            if product_type in m.get("product_types", []) or "*" in m.get("product_types", []):
                d["manifest"] = m
                out.append(d)
        return out

    def record_publication(self, product_id: str, surface_id: str, status: str, *,
                           external_ref: str | None = None, evidence: dict[str, Any] | None = None) -> str:
        pid = new_id("pub")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO publications(publication_id,product_id,surface_id,status,external_ref,evidence_json,
                published_at,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (pid, product_id, surface_id, status, external_ref, canonical_json(evidence or {}).decode(),
                 utc_now() if status == "PUBLISHED" else None, utc_now()),
            )
        self.ledger.append("publication.recorded", "publication", pid,
                           {"product_id": product_id, "surface_id": surface_id, "status": status})
        return pid

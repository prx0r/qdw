"""ContractorRegistry — versioned global contractor definitions."""

from __future__ import annotations

import json
from pathlib import Path

from qdw.core import hash_object, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class ContractorRegistry:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def register_manifest(self, path: str | Path) -> tuple[str, str]:
        m = json.loads(Path(path).read_text(encoding="utf-8"))
        required = {"contractor_id", "version", "team", "specialization", "inputs", "outputs", "gates"}
        missing = required - set(m)
        if missing:
            raise ValueError(f"missing {sorted(missing)}")
        h = hash_object(m)
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO contractor_definitions(contractor_id,version,definition_hash,manifest_json,status,created_at)
                VALUES(?,?,?,?, 'CANDIDATE',?)
                ON CONFLICT(contractor_id,version) DO UPDATE SET definition_hash=excluded.definition_hash,
                manifest_json=excluded.manifest_json""",
                (m["contractor_id"], m["version"], h, json.dumps(m, sort_keys=True), utc_now()),
            )
        self.ledger.append("contractor.registered", "contractor", m["contractor_id"],
                           {"version": m["version"], "team": m["team"], "specialization": m["specialization"]})
        return m["contractor_id"], m["version"]

    def activate(self, contractor_id: str, version: str) -> None:
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                "UPDATE contractor_definitions SET status='ACTIVE' WHERE contractor_id=? AND version=?",
                (contractor_id, version),
            ).rowcount
            if changed != 1:
                raise KeyError((contractor_id, version))

    def list(self) -> list[dict]:
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT contractor_id,version,status,definition_hash FROM contractor_definitions ORDER BY contractor_id"
            ).fetchall()]

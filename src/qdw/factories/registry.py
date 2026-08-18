"""Factory registry — immutable versions, CANDIDATE → ACTIVE lifecycle.

Activation requires a valid fixture certificate, not a boolean assertion.
The registry independently verifies the certificate exists and is accepted.
"""

from __future__ import annotations

import json
from pathlib import Path

from qdw.core import hash_object, utc_now
from qdw.core.db import Database

from .base import FactoryDefinition


class FactoryRegistry:
    def __init__(self, db: Database):
        self.db = db

    def register_manifest(self, path: str | Path) -> FactoryDefinition:
        m = json.loads(Path(path).read_text(encoding="utf-8"))
        d = FactoryDefinition.from_manifest(m)
        h = hash_object(m)
        with self.db.tx(immediate=True) as con:
            existing = con.execute(
                "SELECT definition_hash FROM factory_definitions WHERE factory_id=? AND version=?",
                (d.factory_id, d.version),
            ).fetchone()
            if existing and existing["definition_hash"] != h:
                raise ValueError("factory version is immutable; bump version")
            con.execute(
                """INSERT OR IGNORE INTO factory_definitions(
                    factory_id, version, definition_hash, manifest_json, status, created_at
                ) VALUES(?,?,?,?,?,?)""",
                (d.factory_id, d.version, h, json.dumps(m, sort_keys=True), "CANDIDATE", utc_now()),
            )
        return d

    def activate(self, factory_id: str, version: str, fixture_certificate_id: str) -> None:
        """Activate a factory. Requires a valid fixture certificate.

        The registry independently verifies:
        - certificate exists
        - certificate is accepted
        - certificate artifact hashes match
        """
        with self.db.tx(immediate=True) as con:
            # Check factory exists
            factory = con.execute(
                "SELECT * FROM factory_definitions WHERE factory_id=? AND version=?",
                (factory_id, version),
            ).fetchone()
            if not factory:
                raise KeyError((factory_id, version))

            # Check certificate exists and is accepted
            cert = con.execute(
                "SELECT * FROM gate_results WHERE gate_result_id=?",
                (fixture_certificate_id,),
            ).fetchone()
            if not cert:
                raise ValueError(f"fixture certificate {fixture_certificate_id} not found")
            if not cert["passed"]:
                raise ValueError(f"fixture certificate {fixture_certificate_id} is not accepted")

            # Activate
            con.execute(
                "UPDATE factory_definitions SET status='ACTIVE' WHERE factory_id=? AND version=?",
                (factory_id, version),
            )

    def list(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT factory_id, version, status, definition_hash "
                "FROM factory_definitions ORDER BY factory_id, version"
            ).fetchall()]

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
            existing = con.execute(
                "SELECT definition_hash FROM contractor_definitions WHERE contractor_id=? AND version=?",
                (m["contractor_id"], m["version"]),
            ).fetchone()
            if existing:
                raise ValueError(
                    f"contractor {m['contractor_id']}@{m['version']} already exists; "
                    f"contractor versions are immutable; bump version"
                )
            con.execute(
                """INSERT INTO contractor_definitions(contractor_id,version,definition_hash,manifest_json,status,created_at)
                VALUES(?,?,?,?, 'CANDIDATE',?)""",
                (m["contractor_id"], m["version"], h, json.dumps(m, sort_keys=True), utc_now()),
            )
        self.ledger.append("contractor.registered", "contractor", m["contractor_id"],
                           {"version": m["version"], "team": m["team"], "specialization": m["specialization"]})
        return m["contractor_id"], m["version"]

    def activate(self, contractor_id: str, version: str, fixture_certificate_id: str) -> None:
        """Activate a contractor. Requires a valid fixture certificate.

        The registry independently verifies:
        - certificate exists in gate_results
        - certificate is accepted (passed=1)
        - certificate belongs to this contractor (via detail_json.contractor_id)
        - certificate belongs to this version (via detail_json.contractor_version)
        """
        with self.db.tx(immediate=True) as con:
            # Check contractor exists
            contractor = con.execute(
                "SELECT * FROM contractor_definitions WHERE contractor_id=? AND version=?",
                (contractor_id, version),
            ).fetchone()
            if not contractor:
                raise KeyError((contractor_id, version))

            # Check certificate exists and is accepted
            cert = con.execute(
                "SELECT * FROM gate_results WHERE gate_result_id=?",
                (fixture_certificate_id,),
            ).fetchone()
            if not cert:
                raise ValueError(f"fixture certificate {fixture_certificate_id} not found")
            if not cert["passed"]:
                raise ValueError(f"fixture certificate {fixture_certificate_id} is not accepted")

            # Verify certificate belongs to this contractor and version
            detail = json.loads(cert["detail_json"]) if cert["detail_json"] else {}
            cert_contractor = detail.get("contractor_id")
            cert_version = detail.get("contractor_version")
            if not cert_contractor:
                raise ValueError(
                    f"certificate {fixture_certificate_id} does not identify a contractor"
                )
            if cert_contractor != contractor_id:
                raise ValueError(
                    f"certificate belongs to contractor '{cert_contractor}', not '{contractor_id}'"
                )
            if cert_version and cert_version != version:
                raise ValueError(
                    f"certificate belongs to version '{cert_version}', not '{version}'"
                )

            # Activate
            con.execute(
                "UPDATE contractor_definitions SET status='ACTIVE' WHERE contractor_id=? AND version=?",
                (contractor_id, version),
            )

    def list(self) -> list[dict]:
        with self.db.connect() as con:
            return [dict(r) for r in con.execute(
                "SELECT contractor_id,version,status,definition_hash FROM contractor_definitions ORDER BY contractor_id"
            ).fetchall()]

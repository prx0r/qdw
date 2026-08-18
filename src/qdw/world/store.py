"""WorldStore — canonical entity/observation/claim/relation plane."""

from __future__ import annotations

import json
import re
from typing import Any

from qdw.core import canonical_json, hash_object, new_id, sha256_hex, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.sources.protocol import SourceResult


def normalize_text(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


class WorldStore:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def register_source(self, source_id: str, family: str, name: str, *,
                        terms_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        now = utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO source_connectors(source_id,family,name,config_json,terms_url,status,created_at,updated_at)
                VALUES(?,?,?,?,?,'ACTIVE',?,?)
                ON CONFLICT(source_id) DO UPDATE SET family=excluded.family,name=excluded.name,
                config_json=excluded.config_json,terms_url=excluded.terms_url,updated_at=excluded.updated_at""",
                (source_id, family, name, canonical_json(config or {}).decode(), terms_url, now, now),
            )
        self.ledger.append("source.registered", "source", source_id, {"family": family, "name": name})

    def upsert_entity(self, kind: str, canonical_name: str, *, external_key: str | None = None,
                      attributes: dict[str, Any] | None = None, aliases: list[str] | None = None) -> str:
        now = utc_now()
        entity_id = None
        with self.db.tx(immediate=True) as con:
            if external_key is not None:
                row = con.execute(
                    "SELECT entity_id FROM entities WHERE kind=? AND external_key=?",
                    (kind, external_key),
                ).fetchone()
                if row:
                    entity_id = row["entity_id"]
            if entity_id is None:
                entity_id = new_id("ent")
                con.execute(
                    """INSERT INTO entities(entity_id,kind,canonical_name,external_key,attributes_json,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,'ACTIVE',?,?)""",
                    (entity_id, kind, canonical_name, external_key, canonical_json(attributes or {}).decode(), now, now),
                )
            else:
                con.execute(
                    "UPDATE entities SET canonical_name=?,attributes_json=?,updated_at=? WHERE entity_id=?",
                    (canonical_name, canonical_json(attributes or {}).decode(), now, entity_id),
                )
            for alias in aliases or []:
                n = normalize_text(alias)
                if n:
                    con.execute(
                        "INSERT OR IGNORE INTO entity_aliases(entity_id,alias,normalized_alias) VALUES(?,?,?)",
                        (entity_id, alias, n),
                    )
        self.ledger.append("entity.upserted", "entity", entity_id, {"kind": kind, "external_key": external_key})
        return entity_id

    def record_source_result(self, result: SourceResult, *, observed_at: str | None = None) -> list[str]:
        t = observed_at or result.observed_at or utc_now()
        ids: list[str] = []
        if not result.ok:
            oid = new_id("obs")
            payload = {"error": result.error, "context": result.context or {}}
            with self.db.tx(immediate=True) as con:
                con.execute(
                    """INSERT INTO observations(observation_id,source_id,source_item_id,source_family,
                    observed_at,status,error_code,payload_json,created_at)
                    VALUES(?,?,?,?,?,'ERROR',?,?,?)""",
                    (oid, result.source_id, None, result.source_family, t, result.error,
                     canonical_json(payload).decode(), utc_now()),
                )
            self.ledger.append("observation.error", "observation", oid,
                               {"source_id": result.source_id, "error": result.error})
            return [oid]
        if not result.items:
            payload = {"empty": True, "context": result.context or {}}
            payload_bytes = canonical_json(payload)
            content_hash = sha256_hex(payload_bytes)
            source_item_id = "__empty__:" + hash_object(result.context or {})[:16]
            oid = new_id("obs")
            with self.db.tx(immediate=True) as con:
                existing = con.execute(
                    """SELECT observation_id FROM observations
                    WHERE source_id=? AND source_item_id=? AND content_hash=?""",
                    (result.source_id, source_item_id, content_hash),
                ).fetchone()
                if existing:
                    return [existing["observation_id"]]
                con.execute(
                    """INSERT INTO observations(observation_id,source_id,source_item_id,source_family,
                    observed_at,status,content_hash,payload_json,created_at)
                    VALUES(?,?,?,?,?,'OK_EMPTY',?,?,?)""",
                    (oid, result.source_id, source_item_id, result.source_family, t, content_hash,
                     payload_bytes.decode(), utc_now()),
                )
            self.ledger.append("observation.empty", "observation", oid,
                               {"source_id": result.source_id, "content_hash": content_hash})
            return [oid]
        for i, item in enumerate(result.items):
            payload_bytes = canonical_json(item)
            content_hash = sha256_hex(payload_bytes)
            source_item_id = str(item.get("id") or item.get("url") or item.get("external_id") or i)
            oid = new_id("obs")
            with self.db.tx(immediate=True) as con:
                existing = con.execute(
                    """SELECT observation_id FROM observations
                    WHERE source_id=? AND source_item_id=? AND content_hash=?""",
                    (result.source_id, source_item_id, content_hash),
                ).fetchone()
                if existing:
                    ids.append(existing["observation_id"])
                    continue
                con.execute(
                    """INSERT INTO observations(observation_id,source_id,source_item_id,source_family,
                    observed_at,published_at,freshness_until,status,content_hash,payload_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (oid, result.source_id, source_item_id, result.source_family, t, item.get("published_at"),
                     item.get("freshness_until"), "OK", content_hash, payload_bytes.decode(), utc_now()),
                )
            ids.append(oid)
            self.ledger.append("observation.recorded", "observation", oid,
                               {"source_id": result.source_id, "content_hash": content_hash})
        return ids

    def add_claim(self, predicate: str, obj: Any, *, observation_id: str | None = None,
                  subject_entity_id: str | None = None, confidence: float = 1.0) -> str:
        if not 0 <= confidence <= 1:
            raise ValueError("confidence")
        body = {"observation_id": observation_id, "subject_entity_id": subject_entity_id,
                "predicate": predicate, "object": obj}
        claim_hash = hash_object(body)
        with self.db.tx(immediate=True) as con:
            old = con.execute("SELECT claim_id FROM claims WHERE claim_hash=?", (claim_hash,)).fetchone()
            if old:
                return old["claim_id"]
            cid = new_id("clm")
            con.execute(
                """INSERT INTO claims(claim_id,observation_id,subject_entity_id,predicate,
                object_json,confidence,claim_hash,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                (cid, observation_id, subject_entity_id, predicate, canonical_json(obj).decode(),
                 confidence, claim_hash, utc_now()),
            )
        self.ledger.append("claim.added", "claim", cid, {"claim_hash": claim_hash, "predicate": predicate})
        return cid

    def relate(self, subject_id: str, predicate: str, object_id: str, *,
               supporting_claim_id: str | None = None, confidence: float = 1.0) -> str:
        rid = new_id("rel")
        with self.db.tx(immediate=True) as con:
            old = con.execute(
                """SELECT relation_id FROM relations WHERE subject_entity_id=? AND predicate=?
                AND object_entity_id=? AND supporting_claim_id IS ?""",
                (subject_id, predicate, object_id, supporting_claim_id),
            ).fetchone()
            if old:
                return old["relation_id"]
            con.execute(
                """INSERT INTO relations(relation_id,subject_entity_id,predicate,object_entity_id,
                supporting_claim_id,confidence,created_at) VALUES(?,?,?,?,?,?,?)""",
                (rid, subject_id, predicate, object_id, supporting_claim_id, confidence, utc_now()),
            )
        self.ledger.append("relation.added", "relation", rid,
                           {"subject": subject_id, "predicate": predicate, "object": object_id})
        return rid

    def entity(self, entity_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM entities WHERE entity_id=?", (entity_id,)).fetchone()
            if not r:
                raise KeyError(entity_id)
            d = dict(r)
            d["attributes"] = json.loads(d.pop("attributes_json"))
            return d

    def graph(self, entity_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            out = [dict(r) for r in con.execute(
                "SELECT * FROM relations WHERE subject_entity_id=? OR object_entity_id=?",
                (entity_id, entity_id),
            ).fetchall()]
        return {"entity": self.entity(entity_id), "relations": out}

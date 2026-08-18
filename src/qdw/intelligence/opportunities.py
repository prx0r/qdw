"""Opportunity store and synthesizer — deterministic join layer."""

from __future__ import annotations

import json
from typing import Any

from qdw.core import canonical_json, hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class OpportunityStore:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def create(self, *, kind: str, problem_key: str, title: str, thesis: str,
               features: dict[str, Any], evidence_refs: list[dict[str, str]],
               score: dict[str, Any], factory_hint: str | None = None) -> str:
        feature_hash = hash_object(features)
        evidence_hash = hash_object(sorted(evidence_refs, key=lambda x: canonical_json(x)))
        oid = new_id("opp")
        now = utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO opportunities_global(opportunity_id,kind,problem_key,title,thesis,factory_hint,
                status,score_json,feature_snapshot_json,feature_snapshot_hash,evidence_snapshot_hash,created_at,updated_at)
                VALUES(?,?,?,?,?,?,'CANDIDATE',?,?,?,?,?,?)""",
                (oid, kind, problem_key, title, thesis, factory_hint, canonical_json(score).decode(),
                 canonical_json(features).decode(), feature_hash, evidence_hash, now, now),
            )
            for ref in evidence_refs:
                con.execute(
                    """INSERT OR IGNORE INTO opportunity_evidence(opportunity_id,observation_id,claim_id,
                    pain_cluster_id,startup_event_id,resource_id,role) VALUES(?,?,?,?,?,?,?)""",
                    (oid, ref.get("observation_id"), ref.get("claim_id"), ref.get("pain_cluster_id"),
                     ref.get("startup_event_id"), ref.get("resource_id"), ref.get("role", "support")),
                )
        self.ledger.append("opportunity.created", "opportunity", oid,
                           {"kind": kind, "problem_key": problem_key, "feature_snapshot_hash": feature_hash})
        return oid

    def get(self, opportunity_id: str) -> dict:
        with self.db.connect() as con:
            r = con.execute(
                "SELECT * FROM opportunities_global WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
            if not r:
                raise KeyError(opportunity_id)
            d = dict(r)
            d["score"] = json.loads(d.pop("score_json"))
            d["features"] = json.loads(d.pop("feature_snapshot_json"))
            return d


class OpportunitySynthesizer:
    def __init__(self, db: Database, store: OpportunityStore):
        self.db = db
        self.store = store

    def from_pain_cluster(self, cluster_id: str, *, new_capability_resource_id: str | None = None,
                          factory_hint: str = "app") -> str:
        with self.db.connect() as con:
            c = con.execute("SELECT * FROM pain_clusters WHERE cluster_id=?", (cluster_id,)).fetchone()
            if not c:
                raise KeyError(cluster_id)
        features = {
            "need": min(1.0, c["mention_count"] / 5),
            "source_breadth": min(1.0, c["source_family_count"] / 3),
            "recurrence": c["recurrence"],
            "intensity": c["intensity"],
            "agent_solvability": c["solvability"],
            "verifiability": c["verifiability"],
            "confidence": c["confidence"],
            "new_capability": 1.0 if new_capability_resource_id else 0.0,
        }
        value = (
            features["need"] * 0.20 + features["source_breadth"] * 0.10 + features["recurrence"] * 0.15
            + features["intensity"] * 0.10 + features["agent_solvability"] * 0.20
            + features["verifiability"] * 0.15 + features["confidence"] * 0.10
        )
        evidence = [{"pain_cluster_id": cluster_id, "role": "problem"}]
        if new_capability_resource_id:
            evidence.append({"resource_id": new_capability_resource_id, "role": "enabler"})
        return self.store.create(
            kind="agentic_problem", problem_key=c["problem_key"],
            title=f"Solve: {c['title']}", thesis=c["summary"], features=features,
            evidence_refs=evidence, score={"expected_value_proxy": value, "confidence": c["confidence"]},
            factory_hint=factory_hint,
        )

    def api_gap(self, capability_key: str, *, problem_key: str, current_resource_id: str | None,
                evidence_resources: list[str]) -> str:
        features = {
            "capability_gap": 1.0, "known_candidates": len(evidence_resources),
            "current_resource_present": 1.0 if current_resource_id else 0.0,
        }
        refs = [{"resource_id": r, "role": "candidate"} for r in evidence_resources]
        return self.store.create(
            kind="api_gap", problem_key=problem_key, title=f"API gap: {capability_key}",
            thesis="No candidate satisfies the declared capability constraints; evaluate whether QDW can build one.",
            features=features, evidence_refs=refs,
            score={"expected_value_proxy": 0.55, "confidence": 0.5}, factory_hint="api",
        )

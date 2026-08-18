"""PainFinder — source-family-aware pain clustering with confidence scoring."""

from __future__ import annotations

import re
from collections import Counter

from qdw.core import hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

_STOP = {
    "i", "we", "you", "they", "a", "an", "the", "and", "or", "but", "to", "of", "for", "in", "on", "at",
    "is", "are", "was", "were", "it", "this", "that", "with", "from", "my", "our", "your", "their",
    "do", "does", "how", "why", "can", "could", "would", "should", "really", "just", "anyone", "there",
    "have", "has", "had", "get", "getting", "need", "want", "wish", "using", "use", "used",
    "manually", "manual", "problem", "issue", "tool", "tools", "app", "api",
}
_PAIN = {
    "hate", "annoying", "pain", "painful", "slow", "expensive", "broken", "hard", "difficult",
    "frustrating", "tedious", "missing", "cannot", "can't", "doesn't", "waste", "wasting",
    "workaround", "wish",
}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in _STOP and t not in _PAIN]


def problem_key(text: str) -> str:
    toks = _tokens(text)
    if not toks:
        return "unknown:" + hash_object(text)[:12]
    counts = Counter(toks)
    chosen = sorted(counts, key=lambda x: (-counts[x], x))[:8]
    return " ".join(sorted(chosen))


class PainFinder:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def ingest(self, observation_id: str, text: str, *, intensity: float = 0.5,
               recurrence_hint: float = 0.5, workaround: str | None = None,
               willingness_to_pay: float | None = None, machine_solvable: float = 0.5,
               verifiable: float = 0.5) -> tuple[str, str]:
        for x in (intensity, recurrence_hint, machine_solvable, verifiable):
            if not 0 <= x <= 1:
                raise ValueError("scores must be 0..1")
        key = problem_key(text)
        with self.db.tx(immediate=True) as con:
            obs = con.execute(
                "SELECT source_family FROM observations WHERE observation_id=?", (observation_id,)
            ).fetchone()
            if not obs:
                raise KeyError(observation_id)
            cluster = con.execute(
                "SELECT cluster_id FROM pain_clusters WHERE problem_key=?", (key,)
            ).fetchone()
            if cluster:
                cluster_id = cluster["cluster_id"]
            else:
                cluster_id = new_id("paincluster")
                con.execute(
                    """INSERT INTO pain_clusters(cluster_id,problem_key,title,summary,created_at,updated_at)
                    VALUES(?,?,?,?,?,?)""",
                    (cluster_id, key, key, text[:240], utc_now(), utc_now()),
                )
            pid = new_id("pain")
            con.execute(
                """INSERT INTO pain_observations(pain_id,observation_id,text,normalized_text,fingerprint,
                intensity,recurrence_hint,workaround,willingness_to_pay,machine_solvable,verifiable,cluster_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (pid, observation_id, text, " ".join(_tokens(text)),
                 hash_object({"text": text.lower().strip()}),
                 intensity, recurrence_hint, workaround, willingness_to_pay,
                 machine_solvable, verifiable, cluster_id, utc_now()),
            )
        self._recompute(cluster_id)
        self.ledger.append("pain.ingested", "pain", pid, {"cluster_id": cluster_id, "problem_key": key})
        return pid, cluster_id

    def _recompute(self, cluster_id: str) -> None:
        with self.db.tx(immediate=True) as con:
            rows = con.execute(
                """SELECT p.*,o.source_family FROM pain_observations p
                JOIN observations o ON o.observation_id=p.observation_id WHERE p.cluster_id=?""",
                (cluster_id,),
            ).fetchall()
            if not rows:
                return
            n = len(rows)
            families = len({r["source_family"] for r in rows})
            def avg(k):
                return sum(float(r[k]) for r in rows) / n
            confidence = min(1.0, 0.15 * n + 0.15 * families)
            con.execute(
                """UPDATE pain_clusters SET mention_count=?,source_family_count=?,recurrence=?,intensity=?,
                solvability=?,verifiability=?,confidence=?,updated_at=? WHERE cluster_id=?""",
                (n, families, avg("recurrence_hint"), avg("intensity"), avg("machine_solvable"),
                 avg("verifiable"), confidence, utc_now(), cluster_id),
            )

    def cluster(self, cluster_id: str) -> dict:
        with self.db.connect() as con:
            r = con.execute("SELECT * FROM pain_clusters WHERE cluster_id=?", (cluster_id,)).fetchone()
            if not r:
                raise KeyError(cluster_id)
            return dict(r)

    def top(self, limit: int = 20) -> list[dict]:
        with self.db.connect() as con:
            rows = con.execute(
                """SELECT * FROM pain_clusters WHERE status='ACTIVE'
                ORDER BY (mention_count*confidence*recurrence*intensity*solvability*verifiability) DESC
                LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

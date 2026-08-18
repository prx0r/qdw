"""WorkGraph store — atomic claims, leases, recovery, dependency ordering."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from qdw.core import canonical_json, hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class WorkGraphStore:
    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def create_graph(
        self, factory_run_id: str | None = None, graph_id: str | None = None
    ) -> str:
        graph_id = graph_id or new_id("graph")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO work_graphs(graph_id, factory_run_id, status, created_at)
                VALUES(?,?,?,?)""",
                (graph_id, factory_run_id, "OPEN", utc_now()),
            )
        self.ledger.append("graph.created", "work_graph", graph_id, {"factory_run_id": factory_run_id})
        return graph_id

    def add_node(
        self,
        graph_id: str,
        kind: str,
        title: str,
        payload: dict[str, Any],
        *,
        priority: float = 0,
        expected_value: float | None = None,
        expected_cost: float | None = None,
        quality_floor: float | None = None,
        max_retries: int = 2,
        idempotency_key: str | None = None,
        node_id: str | None = None,
    ) -> str:
        node_id = node_id or new_id("node")
        now = utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO work_nodes(
                    node_id, graph_id, kind, title, state, priority,
                    expected_value, expected_cost, quality_floor,
                    max_retries, idempotency_key, payload_json, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (node_id, graph_id, kind, title, "PENDING", priority,
                 expected_value, expected_cost, quality_floor,
                 max_retries, idempotency_key, canonical_json(payload).decode(), now, now),
            )
        self.ledger.append("node.created", "work_node", node_id, {"graph_id": graph_id, "kind": kind, "title": title})
        return node_id

    def add_edge(self, graph_id: str, from_node: str, to_node: str, relation: str = "blocks") -> None:
        if from_node == to_node:
            raise ValueError("self dependency")
        with self.db.tx(immediate=True) as con:
            con.execute(
                "INSERT OR IGNORE INTO work_edges(graph_id, from_node, to_node, relation) VALUES(?,?,?,?)",
                (graph_id, from_node, to_node, relation),
            )
        cycles = self.validate_dag(graph_id)
        if cycles:
            raise ValueError(f"adding edge creates cycle: {cycles[0]}")
        self.ledger.append(
            "edge.created", "work_graph", graph_id,
            {"from_node": from_node, "to_node": to_node, "relation": relation},
        )

    def refresh_ready(self, graph_id: str) -> int:
        now = utc_now()
        with self.db.tx(immediate=True) as con:
            rows = con.execute(
                """SELECT n.node_id FROM work_nodes n
                WHERE n.graph_id=? AND n.state IN ('PENDING', 'RETRY_WAIT')
                AND NOT EXISTS (
                    SELECT 1 FROM work_edges e
                    JOIN work_nodes blocker ON blocker.node_id=e.from_node
                    WHERE e.graph_id=n.graph_id AND e.to_node=n.node_id
                        AND e.relation='blocks' AND blocker.state!='SUCCEEDED'
                )""",
                (graph_id,),
            ).fetchall()
            for r in rows:
                con.execute(
                    "UPDATE work_nodes SET state='READY', updated_at=? WHERE node_id=?",
                    (now, r["node_id"]),
                )
        for r in rows:
            self.ledger.append("node.ready", "work_node", r["node_id"], {"graph_id": graph_id})
        return len(rows)

    def reclaim_stale(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        now_s = now.isoformat().replace("+00:00", "Z")
        # Collect first, then commit, then ledger (avoid nested transactions)
        to_reclaim: list[tuple[str, bool, dict]] = []
        with self.db.tx(immediate=True) as con:
            rows = con.execute(
                """SELECT node_id, attempt_count, max_retries FROM work_nodes
                WHERE state IN ('LEASED', 'RUNNING') AND lease_until IS NOT NULL AND lease_until < ?""",
                (now_s,),
            ).fetchall()
            for r in rows:
                if r["attempt_count"] >= r["max_retries"]:
                    con.execute(
                        """UPDATE work_nodes SET state='FAILED', lease_owner=NULL, lease_until=NULL, updated_at=?
                        WHERE node_id=?""",
                        (now_s, r["node_id"]),
                    )
                    to_reclaim.append((r["node_id"], True, {
                        "attempt_count": r["attempt_count"], "max_retries": r["max_retries"],
                    }))
                else:
                    con.execute(
                        """UPDATE work_nodes SET state='READY', lease_owner=NULL, lease_until=NULL, updated_at=?
                        WHERE node_id=?""",
                        (now_s, r["node_id"]),
                    )
                    to_reclaim.append((r["node_id"], False, {}))
        # Ledger appends happen AFTER the state transaction commits
        for node_id, failed, payload in to_reclaim:
            if failed:
                self.ledger.append("node.lease_expired_failed", "work_node", node_id, payload)
            else:
                self.ledger.append("node.lease_reclaimed", "work_node", node_id, payload)
        return len(to_reclaim)

    def validate_dag(self, graph_id: str) -> list[str]:
        """Check for cycles in the dependency graph. Returns list of cycle descriptions."""
        with self.db.connect() as con:
            edges = con.execute(
                "SELECT from_node, to_node FROM work_edges WHERE graph_id=?",
                (graph_id,),
            ).fetchall()
            nodes = {r["node_id"] for r in con.execute(
                "SELECT node_id FROM work_nodes WHERE graph_id=?", (graph_id,),
            ).fetchall()}

        # Build adjacency list
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for e in edges:
            if e["from_node"] in adj:
                adj[e["from_node"]].append(e["to_node"])

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in nodes}
        parent = {n: None for n in nodes}
        cycles = []

        def dfs(u: str) -> None:
            color[u] = GRAY
            for v in adj.get(u, []):
                if v not in color:
                    continue
                if color[v] == GRAY:
                    # Found cycle — reconstruct
                    cycle = [v, u]
                    p = parent[u]
                    while p != v and p is not None:
                        cycle.append(p)
                        p = parent[p]
                    cycle.append(v)
                    cycles.append(" → ".join(reversed(cycle)))
                elif color[v] == WHITE:
                    parent[v] = u
                    dfs(v)
            color[u] = BLACK

        for n in nodes:
            if color[n] == WHITE:
                dfs(n)

        return cycles

    def claim_ready(self, worker_id: str, lease_seconds: int = 900, graph_id: str | None = None):
        """Claim the highest-priority READY node using the economic scheduler.

        Selection is delegated to EconomicScheduler, not embedded SQL ranking.
        UNKNOWN cost is preserved as unknown, never coerced to zero.
        """
        from qdw.core.graph.scheduler import Candidate, choose

        now = datetime.now(UTC)
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat().replace("+00:00", "Z")
        now_s = now.isoformat().replace("+00:00", "Z")

        # Collect inside a single transaction, then ledger after commit

        # 1. Fetch all READY nodes
        with self.db.connect() as con:
            params: list[Any] = []
            where = "state='READY'"
            if graph_id:
                where += " AND graph_id=?"
                params.append(graph_id)
            rows = con.execute(
                f"SELECT * FROM work_nodes WHERE {where} ORDER BY created_at",
                params,
            ).fetchall()

        if not rows:
            return None

        # 2. Build candidates for economic scheduler
        candidates = []
        node_map = {}
        for r in rows:
            nv = r["expected_value"]
            nc = r["expected_cost"]
            # UNKNOWN values remain unknown in the candidate.
            # The scheduler handles None-aware ranking.
            candidate = Candidate(
                node_id=r["node_id"],
                expected_value=nv,
                expected_cost=nc,
                confidence=1.0,
                urgency=0.0,
                risk=0.0,
            )
            candidates.append(candidate)
            node_map[r["node_id"]] = r

        # 3. Let scheduler pick the best
        chosen = choose(candidates)
        if chosen is None:
            return None

        # 4. Atomic claim
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                """UPDATE work_nodes SET state='LEASED', lease_owner=?, lease_until=?,
                attempt_count=attempt_count+1, updated_at=? WHERE node_id=? AND state='READY'""",
                (worker_id, lease_until, now_s, chosen.node_id),
            ).rowcount
            if changed != 1:
                return None
            claimed = dict(con.execute(
                "SELECT * FROM work_nodes WHERE node_id=?", (chosen.node_id,)
            ).fetchone())
        # Ledger append happens AFTER the state transaction commits
        self.ledger.append(
            "node.claimed", "work_node", claimed["node_id"],
            {"worker_id": worker_id, "lease_until": lease_until},
        )
        claimed["payload"] = json.loads(claimed.pop("payload_json"))
        return claimed

    def start(self, node_id: str, worker_id: str) -> None:
        with self.db.tx(immediate=True) as con:
            n = con.execute(
                "SELECT lease_owner, state FROM work_nodes WHERE node_id=?", (node_id,)
            ).fetchone()
            if not n or n["state"] != "LEASED" or n["lease_owner"] != worker_id:
                raise RuntimeError("invalid lease")
            con.execute(
                "UPDATE work_nodes SET state='RUNNING', updated_at=? WHERE node_id=?",
                (utc_now(), node_id),
            )
        self.ledger.append("node.started", "work_node", node_id, {"worker_id": worker_id})

    def verifying(self, node_id: str) -> None:
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                """UPDATE work_nodes SET state='VERIFYING', updated_at=?
                WHERE node_id=? AND state='RUNNING'""",
                (utc_now(), node_id),
            ).rowcount
            if changed != 1:
                raise RuntimeError("node not RUNNING")
        self.ledger.append("node.verifying", "work_node", node_id, {})

    def complete(self, node_id: str, result: dict[str, Any]) -> None:
        with self.db.tx(immediate=True) as con:
            changed = con.execute(
                """UPDATE work_nodes SET state='SUCCEEDED', result_json=?,
                lease_owner=NULL, lease_until=NULL, updated_at=? WHERE node_id=? AND state='VERIFYING'""",
                (canonical_json(result).decode(), utc_now(), node_id),
            ).rowcount
            if changed != 1:
                raise RuntimeError("node not VERIFYING")
        self.ledger.append("node.succeeded", "work_node", node_id, {"result_hash": hash_object(result)})

    def fail(self, node_id: str, failure: dict[str, Any], retryable: bool) -> str:
        with self.db.tx(immediate=True) as con:
            n = con.execute(
                "SELECT attempt_count, max_retries FROM work_nodes WHERE node_id=?", (node_id,)
            ).fetchone()
            if not n:
                raise KeyError(node_id)
            state = "FAILED" if n["attempt_count"] >= n["max_retries"] else ("RETRY_WAIT" if retryable else "FAILED")
            con.execute(
                """UPDATE work_nodes SET state=?, result_json=?, lease_owner=NULL, lease_until=NULL, updated_at=?
                WHERE node_id=?""",
                (state, canonical_json(failure).decode(), utc_now(), node_id),
            )
        self.ledger.append(
            "node.failed", "work_node", node_id,
            {"state": state, "failure_hash": hash_object(failure), "retryable": retryable},
        )
        return state

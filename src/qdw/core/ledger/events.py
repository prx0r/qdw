"""Append-only event ledger — hash-chained, with Merkle epochs."""

from __future__ import annotations

from typing import Any

from qdw.core import canonical_json, hash_object, new_id, sha256_hex, utc_now
from qdw.core.db import Database

from .merkle import inclusion_path, merkle_root


class Ledger:
    def __init__(self, db: Database):
        self.db = db

    def append(
        self,
        kind: str,
        subject_type: str,
        subject_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload_json = canonical_json(payload).decode()
        payload_hash = sha256_hex(payload_json.encode())
        with self.db.tx(immediate=True) as con:
            prev = con.execute(
                "SELECT event_hash FROM ledger_events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev["event_hash"] if prev else None
            event_id = new_id("evt")
            occurred_at = utc_now()
            body = {
                "event_id": event_id,
                "occurred_at": occurred_at,
                "kind": kind,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "payload_hash": payload_hash,
                "prev_event_hash": prev_hash,
            }
            event_hash = hash_object(body)
            cur = con.execute(
                """INSERT INTO ledger_events(
                    event_id, occurred_at, kind, subject_type, subject_id,
                    payload_json, payload_hash, prev_event_hash, event_hash
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (event_id, occurred_at, kind, subject_type, subject_id,
                 payload_json, payload_hash, prev_hash, event_hash),
            )
            seq = cur.lastrowid
        return {**body, "event_hash": event_hash, "seq": seq, "payload": payload}

    def verify_chain(self) -> tuple[bool, int | None, str | None]:
        """Verify the entire event chain. Returns (ok, bad_seq, reason)."""
        prev_hash = None
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT * FROM ledger_events ORDER BY seq"
            ).fetchall()
        for row in rows:
            if sha256_hex(row["payload_json"].encode()) != row["payload_hash"]:
                return False, row["seq"], "payload_hash"
            body = {
                "event_id": row["event_id"],
                "occurred_at": row["occurred_at"],
                "kind": row["kind"],
                "subject_type": row["subject_type"],
                "subject_id": row["subject_id"],
                "payload_hash": row["payload_hash"],
                "prev_event_hash": row["prev_event_hash"],
            }
            if row["prev_event_hash"] != prev_hash or hash_object(body) != row["event_hash"]:
                return False, row["seq"], "chain"
            prev_hash = row["event_hash"]
        return True, None, None

    def seal_epoch(self, start_seq: int, end_seq: int) -> dict:
        if end_seq < start_seq:
            raise ValueError("end before start")
        with self.db.tx(immediate=True) as con:
            rows = con.execute(
                "SELECT seq, event_hash FROM ledger_events WHERE seq BETWEEN ? AND ? ORDER BY seq",
                (start_seq, end_seq),
            ).fetchall()
            if (not rows or rows[0]["seq"] != start_seq
                    or rows[-1]["seq"] != end_seq
                    or len(rows) != (end_seq - start_seq + 1)):
                raise ValueError("epoch range is not fully present")
            leaves = [bytes.fromhex(r["event_hash"]) for r in rows]
            root = merkle_root(leaves).hex()
            epoch_id = f"epoch_{start_seq}_{end_seq}_{root[:16]}"
            created_at = utc_now()
            con.execute(
                """INSERT OR IGNORE INTO ledger_epochs(
                    epoch_id, start_seq, end_seq, leaf_count, merkle_root, created_at
                ) VALUES(?,?,?,?,?,?)""",
                (epoch_id, start_seq, end_seq, len(leaves), root, created_at),
            )
        return {
            "epoch_id": epoch_id,
            "start_seq": start_seq,
            "end_seq": end_seq,
            "leaf_count": len(leaves),
            "merkle_root": root,
            "created_at": created_at,
        }

    def proof_for_seq(self, epoch_id: str, seq: int) -> dict:
        with self.db.connect() as con:
            e = con.execute(
                "SELECT * FROM ledger_epochs WHERE epoch_id=?", (epoch_id,)
            ).fetchone()
            if not e:
                raise KeyError(epoch_id)
            rows = con.execute(
                "SELECT seq, event_hash FROM ledger_events WHERE seq BETWEEN ? AND ? ORDER BY seq",
                (e["start_seq"], e["end_seq"]),
            ).fetchall()
        index = seq - e["start_seq"]
        if index < 0 or index >= len(rows):
            raise ValueError("seq outside epoch")
        leaves = [bytes.fromhex(r["event_hash"]) for r in rows]
        return {
            "seq": seq,
            "index": index,
            "tree_size": len(leaves),
            "event_hash": rows[index]["event_hash"],
            "audit_path": [x.hex() for x in inclusion_path(leaves, index)],
            "merkle_root": e["merkle_root"],
        }

"""Tests for QDW event ledger — append-only, hash chain, Merkle epochs."""

from pathlib import Path

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


class TestLedger:
    def _make_ledger(self, tmp_path: Path) -> Ledger:
        db = Database(tmp_path / "test.db")
        db.migrate()
        return Ledger(db)

    def test_append_creates_event(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        result = ledger.append("test.created", "test", "t1", {"key": "value"})
        assert result["kind"] == "test.created"
        assert result["subject_id"] == "t1"
        assert result["seq"] == 1
        assert result["event_hash"] != ""

    def test_chain_integrity(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        for i in range(5):
            ledger.append(f"event.{i}", "test", f"t{i}", {"i": i})
        ok, bad_seq, reason = ledger.verify_chain()
        assert ok is True
        assert bad_seq is None
        assert reason is None

    def test_chain_detects_tamper(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        for i in range(3):
            ledger.append(f"event.{i}", "test", f"t{i}", {"i": i})
        # Tamper with payload directly
        with ledger.db.connect() as con:
            con.execute("UPDATE ledger_events SET payload_json='TAMPERED' WHERE seq=2")
        ok, bad_seq, reason = ledger.verify_chain()
        assert ok is False
        assert bad_seq == 2
        assert reason == "payload_hash"

    def test_seal_epoch_and_proof(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        for i in range(10):
            ledger.append(f"event.{i}", "test", f"t{i}", {"i": i})
        epoch = ledger.seal_epoch(1, 10)
        assert epoch["leaf_count"] == 10
        assert epoch["merkle_root"] != ""
        proof = ledger.proof_for_seq(epoch["epoch_id"], 5)
        assert proof["seq"] == 5
        assert len(proof["audit_path"]) > 0

    def test_prev_event_hash_linked(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        r1 = ledger.append("a", "test", "t1", {})
        r2 = ledger.append("b", "test", "t2", {})
        assert r2["prev_event_hash"] == r1["event_hash"]

    def test_first_event_has_no_prev(self, tmp_path: Path) -> None:
        ledger = self._make_ledger(tmp_path)
        r1 = ledger.append("a", "test", "t1", {})
        assert r1["prev_event_hash"] is None

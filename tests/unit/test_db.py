"""Tests for QDW database — migration, transactions."""

from pathlib import Path

import pytest

from qdw.core.db import Database


class TestDatabase:
    def test_migrate_creates_tables(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        with db.connect() as con:
            tables = [r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert "ledger_events" in tables
        assert "work_graphs" in tables
        assert "work_nodes" in tables
        assert "factory_definitions" in tables
        assert "cost_events" in tables
        assert "certificates" in tables
        assert "schedules" in tables
        assert "factory_stats" in tables

    def test_migrate_idempotent(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        db.migrate()  # second call should not fail

    def test_tx_commit(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        with db.tx() as con:
            con.execute(
                "INSERT INTO ledger_events(event_id, occurred_at, kind, subject_type, "
                "subject_id, payload_json, payload_hash, event_hash) VALUES(?,?,?,?,?,?,?,?)",
                ("evt_001", "2026-01-01T00:00:00Z", "test", "test", "test", "{}", "abc", "def"),
            )
        with db.connect() as con:
            r = con.execute("SELECT COUNT(*) FROM ledger_events").fetchone()
            assert r[0] == 1

    def test_tx_rollback(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        with pytest.raises(ValueError):
            with db.tx() as con:
                con.execute(
                    "INSERT INTO ledger_events(event_id, occurred_at, kind, subject_type, "
                    "subject_id, payload_json, payload_hash, event_hash) VALUES(?,?,?,?,?,?,?,?)",
                    ("evt_002", "2026-01-01T00:00:00Z", "test", "test", "test", "{}", "abc", "def"),
                )
                raise ValueError("rollback")
        with db.connect() as con:
            r = con.execute("SELECT COUNT(*) FROM ledger_events").fetchone()
            assert r[0] == 0

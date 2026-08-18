"""Tests for gitgoblin → QDW federation integration."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.federation.gitgoblin_adapter import GitGoblinFederationAdapter
from qdw.federation.contracts import ExternalStatus


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


class TestGitgoblinFederation:
    def test_normalize_valid_batch(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({
            "schema_version": "qdw-federation-observation/1",
            "observations": [{"entity_key": "repo_1", "metric": "technical_alpha", "value": 0.8}],
            "opportunity_proposals": [],
        })
        assert snap.status == ExternalStatus.OK
        assert len(snap.normalized["observations"]) == 1

    def test_normalize_empty_batch(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({
            "schema_version": "qdw-federation-observation/1",
            "observations": [],
            "opportunity_proposals": [],
        })
        assert snap.status == ExternalStatus.OK_EMPTY

    def test_normalize_wrong_schema(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({"schema_version": "wrong", "observations": []})
        assert snap.status == ExternalStatus.INCOMPATIBLE_PROTOCOL

    def test_to_source_result_success(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({
            "schema_version": "qdw-federation-observation/1",
            "observations": [{"entity_key": "r1", "metric": "alpha", "value": 0.8}],
        })
        result = adapter.to_source_result(snap)
        assert result.ok is True
        assert len(result.items) == 1

    def test_to_source_result_error(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({"schema_version": "wrong"})
        result = adapter.to_source_result(snap)
        assert result.ok is False
        assert result.items == ()

    def test_to_source_result_empty(self) -> None:
        adapter = GitGoblinFederationAdapter()
        snap = adapter.normalize({
            "schema_version": "qdw-federation-observation/1",
            "observations": [],
        })
        result = adapter.to_source_result(snap)
        assert result.ok is True
        assert result.items == ()

    def test_ingest_into_world_store(self, db: Database) -> None:
        """Full flow: normalize → to_source_result → WorldStore."""
        from qdw.world.store import WorldStore
        from qdw.core.ledger.events import Ledger

        ledger = Ledger(db)
        world = WorldStore(db, ledger)
        adapter = GitGoblinFederationAdapter()

        snap = adapter.normalize({
            "schema_version": "qdw-federation-observation/1",
            "observations": [{"entity_key": "repo_1", "metric": "alpha", "value": 0.8}],
        })
        result = adapter.to_source_result(snap)
        obs_ids = world.record_source_result(result)
        assert len(obs_ids) == 1

        with db.connect() as con:
            obs = con.execute("SELECT * FROM observations").fetchone()
            assert obs is not None
            assert obs["source_id"] == "federation:gitgoblin"

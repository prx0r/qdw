"""Tests for QDW API — real health checks, typed errors."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import qdw.interfaces.api as api_mod
    monkeypatch.setattr(api_mod, "_DB", str(tmp_path / "test.db"))
    from qdw.core.db import Database
    Database(str(tmp_path / "test.db")).migrate()
    return TestClient(api_mod.app)


class TestHealth:
    def test_health_returns_ok(self, client) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["ledger_ok"] is True
        assert data["db_tables"] > 0

    def test_health_has_timestamp(self, client) -> None:
        r = client.get("/health")
        assert "T" in r.json()["timestamp"]


class TestRoute:
    def test_route_with_no_routes(self, client) -> None:
        r = client.post("/route", json={"task_kind": "coding"})
        assert r.status_code == 200
        data = r.json()
        assert data["primary"] is None
        assert "NO_CANDIDATES" in data["reason_codes"]

    def test_route_with_free_route(self, client) -> None:
        r = client.post("/route", json={
            "task_kind": "coding",
            "quality": 0.3,
            "routes": [{
                "route_id": "free", "model_id": "m", "provider_id": "p",
                "free": True, "input_per_m": 0, "output_per_m": 0,
            }],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["primary"] is not None
        assert data["primary"]["route_id"] == "free"


class TestFactories:
    def test_list_factories_empty(self, client) -> None:
        r = client.get("/factories")
        assert r.status_code == 200
        assert r.json() == []


class TestGraph:
    def test_graph_not_found(self, client) -> None:
        r = client.get("/graph/nonexistent")
        assert r.status_code == 404

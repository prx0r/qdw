"""Tests for API factory fixture — real boot, real HTTP, real verification."""

from pathlib import Path

import pytest

from qdw.factories.fixtures.api import APIFactoryFixture


class TestAPIFactoryFixture:
    def test_generate_creates_files(self, tmp_path: Path) -> None:
        fixture = APIFactoryFixture()
        root = fixture.generate(tmp_path / "api")
        assert (root / "app.py").exists()
        assert (root / "fixture.json").exists()

    def test_verify_boots_server_and_hits_health(self, tmp_path: Path) -> None:
        """Real test: boots FastAPI, hits /health over HTTP."""
        fixture = APIFactoryFixture()
        root = fixture.generate(tmp_path / "api")
        result = fixture.verify(root)
        assert result.passed is True
        assert result.status_code == 200
        assert "ok" in result.body

    def test_broken_fixture_fails(self, tmp_path: Path) -> None:
        """Broken fixture: no /health endpoint."""
        fixture = APIFactoryFixture()
        root = fixture.generate(tmp_path / "api_broken", broken=True)
        result = fixture.verify(root)
        assert result.passed is False
        assert result.status_code != 200

    def test_artifact_hash_deterministic(self, tmp_path: Path) -> None:
        fixture = APIFactoryFixture()
        root = fixture.generate(tmp_path / "api")
        result = fixture.verify(root)
        # Same files produce same hash
        result2 = fixture.verify(root)
        assert result.artifact_hash == result2.artifact_hash

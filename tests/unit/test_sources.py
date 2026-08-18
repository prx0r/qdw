"""Tests for QDW typed source failure semantics."""

import pytest

from qdw.sources.protocol import SourceError, SourceResult


class TestSourceResult:
    def test_ok_result_is_truthy(self) -> None:
        r = SourceResult.success("test", "test_family", [{"name": "test"}])
        assert r.ok is True
        assert len(r.items) == 1

    def test_failed_result_is_falsy(self) -> None:
        r = SourceResult.failure("test", "test_family", "rate_limited")
        assert r.ok is False
        assert r.error == "rate_limited"

    def test_empty_ok_result(self) -> None:
        r = SourceResult.success("test", "test_family", [])
        assert r.ok is True
        assert len(r.items) == 0

    def test_source_failure_not_empty_results(self) -> None:
        """SOURCE FAILURE != ZERO RESULTS — the key invariant."""
        failed = SourceResult.failure("github", "repo", "timeout")
        empty = SourceResult.success("github", "repo", [])
        assert failed.ok is False
        assert empty.ok is True
        assert failed != empty

    def test_source_error_exception(self) -> None:
        with pytest.raises(SourceError):
            raise SourceError("network error")

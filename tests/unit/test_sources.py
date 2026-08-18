"""Tests for QDW typed source failure semantics."""

from qdw.sources import SearchResult, SourceUnavailable


class TestSearchResult:
    def test_ok_result_is_truthy(self) -> None:
        r = SearchResult(ok=True, items=[{"name": "test"}])
        assert bool(r) is True
        assert len(r.items) == 1

    def test_failed_result_is_falsy(self) -> None:
        r = SearchResult(ok=False, error="rate_limited")
        assert bool(r) is False
        assert r.error == "rate_limited"

    def test_empty_ok_result(self) -> None:
        r = SearchResult(ok=True, items=[])
        assert bool(r) is True
        assert r.items == []

    def test_source_failure_not_empty_results(self) -> None:
        """SOURCE FAILURE != ZERO RESULTS — the key invariant."""
        failed = SearchResult(ok=False, error="timeout", source="github")
        empty = SearchResult(ok=True, items=[], source="github")
        assert bool(failed) is False
        assert bool(empty) is True
        assert failed != empty

    def test_source_unavailable_exception(self) -> None:
        with __import__("pytest").raises(SourceUnavailable):
            raise SourceUnavailable("network error")

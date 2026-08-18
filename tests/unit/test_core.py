"""Tests for QDW core utilities."""

import json

from qdw.core import canonical_json, hash_object, new_id, sha256_hex, utc_now


class TestCoreUtils:
    def test_new_id_prefix(self) -> None:
        rid = new_id("node")
        assert rid.startswith("node_")
        assert len(rid) == 29  # "node_" + 24 hex chars

    def test_new_id_unique(self) -> None:
        ids = {new_id("x") for _ in range(100)}
        assert len(ids) == 100

    def test_canonical_json_deterministic(self) -> None:
        a = canonical_json({"b": 1, "a": 2})
        b = canonical_json({"a": 2, "b": 1})
        assert a == b
        assert json.loads(a) == {"a": 2, "b": 1}

    def test_sha256_hex(self) -> None:
        h = sha256_hex(b"hello")
        assert len(h) == 64
        assert h == sha256_hex(b"hello")

    def test_hash_object(self) -> None:
        h = hash_object({"x": 1})
        assert h == hash_object({"x": 1})
        assert h != hash_object({"x": 2})

    def test_utc_now_format(self) -> None:
        ts = utc_now()
        assert ts.endswith("Z")
        assert "T" in ts

"""Tests for QDW Merkle tree — RFC6962-style."""

from qdw.core.ledger.merkle import (
    inclusion_path,
    leaf_hash,
    merkle_root,
    node_hash,
    verify_inclusion,
)


class TestMerkle:
    def test_empty_root(self) -> None:
        root = merkle_root([])
        assert len(root) == 32

    def test_single_item(self) -> None:
        items = [b"hello"]
        root = merkle_root(items)
        assert root == leaf_hash(b"hello")

    def test_two_items(self) -> None:
        items = [b"a", b"b"]
        root = merkle_root(items)
        expected = node_hash(leaf_hash(b"a"), leaf_hash(b"b"))
        assert root == expected

    def test_inclusion_verify(self) -> None:
        items = [b"a", b"b", b"c", b"d"]
        root = merkle_root(items)
        for i in range(len(items)):
            path = inclusion_path(items, i)
            assert verify_inclusion(items[i], i, len(items), path, root)

    def test_inclusion_wrong_item_fails(self) -> None:
        items = [b"a", b"b", b"c", b"d"]
        root = merkle_root(items)
        path = inclusion_path(items, 0)
        assert not verify_inclusion(b"X", 0, len(items), path, root)

    def test_inclusion_wrong_index_fails(self) -> None:
        items = [b"a", b"b", b"c", b"d"]
        root = merkle_root(items)
        path = inclusion_path(items, 0)
        assert not verify_inclusion(items[0], 1, len(items), path, root)

    def test_inclusion_out_of_range(self) -> None:
        items = [b"a", b"b"]
        root = merkle_root(items)
        path = inclusion_path(items, 0)
        assert not verify_inclusion(items[0], 0, 0, path, root)  # tree_size=0
        assert not verify_inclusion(items[0], -1, len(items), path, root)

    def test_large_tree(self) -> None:
        items = [f"item_{i}".encode() for i in range(100)]
        root = merkle_root(items)
        for i in [0, 50, 99]:
            path = inclusion_path(items, i)
            assert verify_inclusion(items[i], i, len(items), path, root)

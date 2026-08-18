"""Merkle tree — RFC6962-style with sha256."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(data: bytes) -> bytes:
    return _h(b"\x00" + data)


def node_hash(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


def merkle_root(items: Sequence[bytes]) -> bytes:
    if not items:
        return _h(b"")
    if len(items) == 1:
        return leaf_hash(items[0])
    k = 1 << ((len(items) - 1).bit_length() - 1)
    return node_hash(merkle_root(items[:k]), merkle_root(items[k:]))


def inclusion_path(items: Sequence[bytes], index: int) -> list[bytes]:
    if index < 0 or index >= len(items):
        raise IndexError(index)
    if len(items) <= 1:
        return []
    k = 1 << ((len(items) - 1).bit_length() - 1)
    if index < k:
        return inclusion_path(items[:k], index) + [merkle_root(items[k:])]
    return inclusion_path(items[k:], index - k) + [merkle_root(items[:k])]


def verify_inclusion(
    item: bytes,
    index: int,
    tree_size: int,
    path: Sequence[bytes],
    expected_root: bytes,
) -> bool:
    if tree_size <= 0 or index < 0 or index >= tree_size:
        return False
    h = leaf_hash(item)
    fn = index
    sn = tree_size - 1
    for p in path:
        h = node_hash(p, h) if fn % 2 == 1 or fn == sn else node_hash(h, p)
        fn //= 2
        sn //= 2
    return h == expected_root

"""QDW core utilities — IDs, hashing, canonical JSON, timestamps."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_object(value: Any) -> str:
    return sha256_hex(canonical_json(value))


@dataclass(frozen=True)
class ContentRef:
    sha256: str
    media_type: str = "application/octet-stream"
    size_bytes: int | None = None

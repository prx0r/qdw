"""Production certificate — links artifacts, gates, ledger root, source commit."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from qdw.core import hash_object, new_id, utc_now


@dataclass(frozen=True)
class Certificate:
    certificate_id: str
    factory_run_id: str
    artifact_hashes: tuple[str, ...]
    gate_hashes: tuple[str, ...]
    ledger_root: str
    issued_at: str
    source_commit: str | None = None
    signature: str | None = None


def issue(
    factory_run_id: str,
    artifact_hashes: list[str],
    gate_hashes: list[str],
    ledger_root: str,
    source_commit: str | None = None,
) -> tuple[Certificate, str]:
    if not artifact_hashes:
        raise ValueError("no artifacts")
    if not gate_hashes:
        raise ValueError("no gates")
    c = Certificate(
        new_id("cert"),
        factory_run_id,
        tuple(sorted(artifact_hashes)),
        tuple(sorted(gate_hashes)),
        ledger_root,
        utc_now(),
        source_commit,
    )
    return c, hash_object(asdict(c))

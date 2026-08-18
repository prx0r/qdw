"""Forge client — capability execution through QDW.

Forge owns capability assets, leases, and invocations.
QDW uses Forge as an executor (like Hermes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdw.core import hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.executors.protocol import ExecutionRequest, ExecutionResult


@dataclass(frozen=True)
class ForgeLease:
    lease_id: str
    asset_id: str
    version: str
    capability: str
    token: str
    max_spend_usd: float | None
    created_at: str


class ForgeClient:
    """Client for Forge capability execution.

    In production, this would make HTTP calls to Forge's API.
    For now, it simulates Forge execution.
    """

    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def lease(self, request: dict) -> dict:
        """Request a lease for a capability asset."""
        lease_id = new_id("lease")
        token = f"tok_{hash_object(request)[:16]}"
        lease = {
            "lease_id": lease_id,
            "asset_id": request.get("asset_id", "unknown"),
            "version": request.get("version", "1"),
            "capability": request.get("capability", "unknown"),
            "token": token,
            "max_spend_usd": request.get("max_spend_usd"),
            "created_at": utc_now(),
        }
        # Persist lease
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO forge_leases(lease_id, asset_id, version, capability,
                token, max_spend_usd, created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (lease_id, lease["asset_id"], lease["version"], lease["capability"],
                 token, lease["max_spend_usd"], lease["created_at"]),
            )
        self.ledger.append("forge.lease", "forge_lease", lease_id, {
            "asset_id": lease["asset_id"], "capability": lease["capability"],
        })
        return lease

    def invoke(self, request: dict) -> dict:
        """Invoke a capability through a lease."""
        invocation_id = new_id("inv")
        # Simulate execution
        output = {"status": "ok", "result": f"Executed {request.get('capability', 'unknown')}"}
        cost = 0.01
        return {
            "invocation_id": invocation_id,
            "asset_id": request.get("asset_id", "unknown"),
            "version": request.get("version", "1"),
            "status": "SUCCEEDED_UNVERIFIED",
            "output": output,
            "output_hash": hash_object(output),
            "cost_usd": cost,
        }

    def bind_certificate(self, invocation_id: str, certificate: dict) -> None:
        """Bind a verification certificate to an invocation."""
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO forge_invocation_certs(invocation_id, certificate_id,
                certificate_hash, status, created_at)
                VALUES(?,?,?,?,?)""",
                (invocation_id, certificate.get("certificate_id", ""),
                 hash_object(certificate), "BOUND", utc_now()),
            )
        self.ledger.append("forge.certificate_bound", "forge_invocation", invocation_id, {
            "certificate_id": certificate.get("certificate_id"),
        })

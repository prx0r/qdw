"""Mechanism extraction — identify technical patterns in QDW codebase.

Ported from gitgoblin/mechanisms.py. Identifies patterns like
Event Sourcing, CAS Coordination, Differential Testing etc.
and maps them to QDW modules for review verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Mechanism:
    mechanism_id: str
    name: str
    description: str
    category: str
    evidence_files: tuple[str, ...] = ()
    evidence_snippets: tuple[str, ...] = ()
    confidence: float = 0.0
    targets: tuple[str, ...] = ()
    hypothesis: str = ""


MECHANISM_RULES: dict[str, list[dict[str, Any]]] = {
    "validation": [
        {"keywords": ["differential", "oracle", "reference impl", "cross-check"],
         "name": "Differential Testing", "description": "Validate against reference implementation"},
        {"keywords": ["fault injection", "chaos", "deliberately broken", "adversarial"],
         "name": "Fault Injection", "description": "Deliberately break to test resilience"},
        {"keywords": ["mutation testing", "checker of checker", "seeded defective"],
         "name": "Mutation Testing", "description": "Test suite must catch seeded defects"},
        {"keywords": ["deterministic", "reproducible", "seed", "fixed"],
         "name": "Deterministic Testing", "description": "Reproducible test execution"},
        {"keywords": ["adversarial", "fuzz", "property-based", "hypothesis"],
         "name": "Adversarial Testing", "description": "Systematic adversarial input generation"},
    ],
    "state": [
        {"keywords": ["compare-and-swap", "cas", "optimistic concurrency", "atomic"],
         "name": "CAS Coordination", "description": "Compare-and-swap coordination"},
        {"keywords": ["durable", "persistent", "crash-recoverable", "write-ahead", "wal"],
         "name": "Durable State", "description": "Crash-recoverable persistent state"},
        {"keywords": ["event sourced", "append-only", "event log", "immutable", "hash chain"],
         "name": "Event Sourcing", "description": "Append-only event log with projections"},
    ],
    "routing": [
        {"keywords": ["cost-aware", "budget", "spend limit", "expected_completion_cost"],
         "name": "Cost-Aware Routing", "description": "Route by cost constraints"},
        {"keywords": ["fallback", "cascade", "retry", "recovery"],
         "name": "Cascade Fallback", "description": "Ordered fallback routing"},
    ],
    "verification": [
        {"keywords": ["certificate", "receipt", "proof", "attestation", "content-hash"],
         "name": "Verifiable Receipt", "description": "Cryptographic proof of execution"},
        {"keywords": ["independent verifier", "separate verification"],
         "name": "Independent Verification", "description": "Verifier separate from executor"},
    ],
    "data": [
        {"keywords": ["content-addressed", "hash store", "cas", "sha256"],
         "name": "Content-Addressed Storage", "description": "Store by content hash"},
        {"keywords": ["merkle", "tree hash", "inclusion proof"],
         "name": "Merkle Tree", "description": "Merkle tree for integrity proofs"},
    ],
}

# Map mechanism categories to QDW modules
MODULE_TARGETS = {
    "validation": ["tests/", "adversarial/"],
    "state": ["core/graph/", "core/ledger/", "hotswap/"],
    "routing": ["hotswap/", "federation/"],
    "verification": ["proof/", "review/"],
    "data": ["core/ledger/merkle.py", "core/graph/"],
}


def extract_mechanisms(
    repo_root: str | Path,
    *,
    max_mechanisms: int = 20,
) -> list[Mechanism]:
    """Extract mechanisms from a codebase."""
    root = Path(repo_root)
    mechanisms: list[Mechanism] = []
    seen = set()

    for py_file in sorted(root.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        content_lower = content.lower()
        rel_path = str(py_file.relative_to(root))

        for category, rules in MECHANISM_RULES.items():
            for rule in rules:
                matches = [kw for kw in rule["keywords"] if kw in content_lower]
                if len(matches) >= 2:  # Need at least 2 keyword matches
                    mid = f"{category}:{rule['name']}"
                    if mid in seen:
                        continue
                    seen.add(mid)

                    # Find which QDW modules this targets
                    targets = []
                    for target_pattern in MODULE_TARGETS.get(category, []):
                        if target_pattern in rel_path:
                            targets.append(rel_path)

                    confidence = min(1.0, len(matches) / 3.0)
                    mechanisms.append(Mechanism(
                        mechanism_id=mid,
                        name=rule["name"],
                        description=rule["description"],
                        category=category,
                        evidence_files=(rel_path,),
                        evidence_snippets=tuple(matches[:3]),
                        confidence=confidence,
                        targets=tuple(targets),
                        hypothesis=f"Code uses {rule['name']} pattern ({', '.join(matches[:3])})",
                    ))

                    if len(mechanisms) >= max_mechanisms:
                        return mechanisms

    return sorted(mechanisms, key=lambda m: -m.confidence)

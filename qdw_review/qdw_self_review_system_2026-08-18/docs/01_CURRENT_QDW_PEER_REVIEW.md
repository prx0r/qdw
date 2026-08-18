# Current QDW peer review

Reviewed: `prx0r/qdw@c1ab1e46c41587c85253278ed5e012b0f757a551`

## Verdict

The architecture is materially better than the legacy VentureLab and the global infrastructure is now
present, but QDW still has a gap between its **proof/immutability doctrine** and actual enforcement.

Current findings: **5 critical, 12 high, 11 medium, 1 info**.

The next work should not add another large feature layer. It should make the trust/evidence spine real,
then integrate self-review as a normal QDW contractor formula.

## Critical blockers

### QDW-CUR-001 — Release certificate script is still vacuous

**Evidence:** `scripts/build_certificate.py` — Uses acceptance_spec_hash='manual_review', required_commands=[], required_negative_tests=[]; unrelated latest receipt can seed PROVEN.

**Fix:** Make release certificate consume a frozen non-empty AcceptanceSpec and exact mandatory receipts.

### QDW-CUR-003 — Factory activation is vulnerable to evidence substitution

**Evidence:** `src/qdw/factories/registry.py` — fixture_certificate_id is looked up in gate_results and only passed is checked; no factory/version/fixture/artifact binding.

**Fix:** Use a true fixture certificate bound to exact factory_id/version/fixture_id/artifacts/acceptance.

### QDW-CUR-004 — Product release accepts arbitrary certificate ID

**Evidence:** `src/qdw/products/registry.py` — release writes certificate_id without validating certificate existence or subject/run binding.

**Fix:** Resolve and fully verify release certificate before status transition.

### QDW-CUR-009 — Migration 0002 was edited after being introduced

**Evidence:** `migrations/0002_global.sql` — Persistent HotSwap tables were appended to existing migration 0002; DBs that already recorded version 2 will skip them.

**Fix:** Restore locked 0002 and create 0003+ migration for new tables.

### QDW-CUR-010 — Migration versions have no checksum lock

**Evidence:** `src/qdw/core/migrations.py` — schema_versions stores only version; migration content drift is undetectable.

**Fix:** Store and verify SHA-256 for every applied migration.

## High-priority structural findings

- **QDW-CUR-002 Certificate verifier does not revalidate bound evidence** — `src/qdw/proof/certificate.py`. Implement full certificate evidence verification and optionally signature/anchor verification.
- **QDW-CUR-005 Contractor versions are mutable** — `src/qdw/contractors/registry.py`. Reject hash changes for existing version; require version bump.
- **QDW-CUR-006 Contractor activation has no fixture/certificate gate** — `src/qdw/contractors/registry.py`. Require bound contractor fixture certificate.
- **QDW-CUR-007 State and ledger events are still separate commits** — `src/qdw/core/graph/store.py`. Write event in same DB transaction or durable outbox.
- **QDW-CUR-008 UNKNOWN graph economics are still fabricated** — `src/qdw/core/graph/store.py`. Represent unknown explicitly and route to block/information/prior policy.
- **QDW-CUR-011 Migration execution/version recording not proven atomic** — `src/qdw/core/migrations.py`. Implement and adversarially test all-or-nothing migration application.
- **QDW-CUR-013 Route definitions do not survive QDWSystem restart** — `src/qdw/system.py`. Create persistent RouteRegistry and load active routes.
- **QDW-CUR-014 Persistent posterior update can lose concurrent observations** — `src/qdw/hotswap/persistent.py`. Use atomic SQL increments or one BEGIN IMMEDIATE read/update.
- **QDW-CUR-016 QDWSystem is not yet the claimed single composition root** — `src/qdw/system.py`. Compose all canonical services and make E2E/interfaces use QDWSystem.
- **QDW-CUR-017 Current E2E bypasses the factory execution spine** — `tests/integration/test_e2e.py`. Build one true V10 exemplar through the entire Factory OS.
- **QDW-CUR-018 Docker installation order is structurally wrong** — `Dockerfile`. Copy/build source first or build wheel in builder stage, then boot and health-smoke container.
- **QDW-CUR-021 Global lineage tables largely lack foreign keys** — `migrations/0002_global.sql`. Add new migration rebuilding stable relations with FKs/CHECKs and run foreign_key_check.

## Medium / follow-up

- **QDW-CUR-012 Database.migrate ignores migrations_dir parameter** — Forward custom migration directory and test contract.
- **QDW-CUR-015 Quota state remains process-local** — Persist durable quota/reservations or explicitly model refreshable snapshots.
- **QDW-CUR-019 Docker is built but not booted in CI** — Add clean container runtime smoke with bounded health polling.
- **QDW-CUR-020 Pyright is configured but not run in CI** — Add pyright gate and receipt.
- **QDW-CUR-022 Cemetery history is overwritten** — Store append-only burial episodes; derive current status separately.
- **QDW-CUR-023 Idea review still trusts passed=True** — Bind important review stages to ReviewDecision/ReviewCertificate evidence IDs.
- **QDW-CUR-024 Human approval lacks required actor identity** — Bind irreversible decisions to explicit actor identity/decision source.
- **QDW-CUR-025 Factory-produced product lineage is optional** — Separate factory-created products from explicitly imported external products.
- **QDW-CUR-026 Outcome authority is not typed** — Type fixture/manual/estimated/measured outcomes and gate production learning.
- **QDW-CUR-027 DAG validator is not an execution gate** — Add graph DRAFT→VALIDATED/FROZEN lifecycle; only frozen graphs executable.
- **QDW-CUR-028 Retry ceiling semantics differ by failure path** — Define max_attempts/retries once and centralize state transition policy.

## Recommended sequence

1. Freeze current migration bytes and introduce migration digests.
2. Repair release/factory/contractor certificate subject binding.
3. Make state+ledger provenance atomic.
4. Remove UNKNOWN economic fabrication.
5. Make RouteRegistry/posterior/quota semantics durable and concurrency-correct.
6. Make QDWSystem the actual composition root for global infrastructure.
7. Replace pseudo-E2E with a real FactoryRun/WorkGraph/executor/artifact/certificate/release exemplar.
8. Fix clean Docker build and add runtime health smoke.
9. Add QDW Self-Review as normal WorkGraph/Contractor infrastructure.
10. Only after the new review formula certifies the exact SHA should QDW call a release REVIEW_CERTIFIED.

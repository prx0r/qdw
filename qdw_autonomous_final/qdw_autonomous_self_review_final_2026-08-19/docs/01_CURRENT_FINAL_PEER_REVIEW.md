# Final peer review of current QDW

Reviewed head: `ab809c8e6b829374199eb49dc71cd6f499e4f7fb`

The latest push materially improved QDW, but the **claim that all 29 prior findings are closed is not
supported yet**. The current final review finds **9 critical, 12 high,
8 medium and 1 low** structural issues.

## Most important corrections

### QDW-FINAL-001 — Two verification runners own incompatible receipt formats

`src/qdw/core/verification/runner.py + src/qdw/proof/runner.py`

CLI writes core VerificationRunner run directories; BuildCertificateBuilder reads proof/runner receipts.jsonl. They are separate sources of verification truth.

**Required:** Collapse to one canonical VerificationService and keep compatibility wrappers only.

### QDW-FINAL-002 — CI Build Certificate is not bound to the pytest/lint/type-check gates

`.github/workflows/ci.yml + scripts/build_certificate.py`

CI executes pytest/ruff/pyright directly, then runs one CLI smoke through the other verification runner. build_certificate.py reads qdw.proof receipts, so the preceding gates are not the certificate's mandatory receipt set.

**Required:** Execute a frozen release VerificationPlan through one VerificationService and issue from that run ID.

### QDW-FINAL-003 — Build certificate derives its requirements from whatever receipts happened to exist

`scripts/build_certificate.py`

The script chooses the most common task_id, converts observed receipt argv into required_commands, and uses acceptance_spec_hash='ci_pipeline'. The acceptance criteria are therefore not frozen before execution.

**Required:** Require an explicit VerificationPlan/AcceptanceSpec path and content hash. Required commands come from the plan, never from observed receipts.

### QDW-FINAL-004 — Negative-test semantics are inverted

`src/qdw/proof/certificate.py`

required_negative_tests are considered successful only when the process exits nonzero. A proper pytest adversarial test should exit 0 while asserting that malicious input was rejected.

**Required:** Model attacks separately: the test command must PASS and the AttackResult records that the bad action was rejected for the expected reason.

### QDW-FINAL-005 — Certificate issuance does not enforce one clean exact Git subject across receipts

`src/qdw/proof/certificate.py`

Receipt lookup is by argv/task_id; certificate git_sha comes from receipts[0]. It does not reject mixed SHAs, dirty receipts, or different working directories/environments.

**Required:** Bind VerificationRun to one subject SHA/dirty=false; every mandatory receipt must match run_id, SHA, cwd and plan hash.

### QDW-FINAL-006 — Certificate revalidation reruns changed code instead of validating the original evidence set

`src/qdw/proof/certificate.py`

verify_certificate re-executes commands in cert.get('cwd','.'), but cwd is not stored in the certificate. It does not validate the actual acceptance-spec file and can verify a later checkout rather than the certified subject.

**Required:** Separate evidence verification from optional replay. Verify immutable receipts/artifacts/spec/SHA first; replay only in a checkout proven to match the certified SHA.

### QDW-FINAL-007 — Factory activation still uses a gate_result as a certificate

`src/qdw/factories/registry.py`

Activation checks passed + detail_json.factory_id and an optional factory_version. It does not bind fixture_id, factory definition hash, artifact digests, acceptance plan, build run or independent certifier.

**Required:** Use a dedicated FixtureCertificate subject tuple and require exact factory_id/version/definition_hash/fixture_id/artifacts/run/acceptance bindings.

### QDW-FINAL-008 — Contractor activation still uses a gate_result as a certificate

`src/qdw/contractors/registry.py`

Contractor activation mirrors the weak gate_result pattern and allows missing contractor_version.

**Required:** Use a dedicated ContractorFixtureCertificate bound to exact contractor definition hash/version/fixture and independent reviewer.

### QDW-FINAL-009 — Product release still uses gate_results instead of a release certificate

`src/qdw/products/registry.py`

Release checks detail_json.product_id but not build_run_id, certified artifact set, factory definition, build certificate, review certificate or release policy.

**Required:** Require ReleaseAuthorization built from BuildCertificate + optional ReviewCertificate and exact product/build/artifact subject.

### QDW-FINAL-010 — Atomic provenance was fixed only for create_graph

`src/qdw/core/graph/store.py`

add_node, add_edge, refresh_ready, reclaim_stale, claim_ready, start, verifying, complete and fail still commit canonical state before ledger.append.

**Required:** Use ledger.append_in_tx for every transition or a transactional outbox. Add crash injection per transition.

### QDW-FINAL-011 — Cycle rejection occurs after the edge has already committed

`src/qdw/core/graph/store.py`

add_edge inserts/commits an edge, then validate_dag raises if cyclic. The invalid cyclic edge remains in canonical state.

**Required:** Validate the tentative edge inside one transaction before commit, or insert + validate + rollback on failure.

### QDW-FINAL-012 — WorkGraphs have no enforced freeze boundary

`src/qdw/core/graph/store.py`

Nodes/edges can be modified while a graph is executable; DAG validation is not tied to a DRAFT→FROZEN lifecycle/hash.

**Required:** Add graph DRAFT→FROZEN→RUNNING→terminal state, structure hash, and reject mutation after freeze.

### QDW-FINAL-013 — Migration application and version/hash recording are not atomic

`src/qdw/core/migrations.py`

executescript(sql) is followed by schema_versions INSERT without an explicit tested transaction covering both. A halfway failure can leave partial schema with no applied-version row.

**Required:** Implement one all-or-nothing migration transaction strategy and test a deliberately failing multi-statement migration.

### QDW-FINAL-014 — Legacy applied migrations with NULL content_hash remain outside drift protection

`src/qdw/core/migrations.py`

_check_drift only rejects when stored content_hash is non-null; legacy version rows are not securely backfilled.

**Required:** Add an explicit migration baseline process: compare schema fingerprint, record accepted historical hashes once, then require non-null digest for every applied version.

### QDW-FINAL-015 — Migration 0004 is a destructive table-rebuild without upgrade/failure parity proof

`migrations/0004_foreign_keys.sql`

It rebuilds and drops many global tables. CI only checks versions 1 and 2 and does not prove populated 1→2→3→4 upgrade parity, row preservation, indexes, or rollback on failure.

**Required:** Add populated upgrade fixtures, row-count/content hashes, schema fingerprint parity, foreign_key_check and injected mid-migration failure.

### QDW-FINAL-016 — Route persistence is lossy

`src/qdw/hotswap/persistent.py + src/qdw/hotswap/types.py`

save/load persists only a subset of Route: endpoint_id, account_id, prior_success, prior_confidence, breaker_open, quota_pressure and evidence_ids are lost on restart.

**Required:** Persist the complete route snapshot or split immutable RouteDefinition from evidenced dynamic RouteObservation.

### QDW-FINAL-018 — First-use posterior initialization can overwrite concurrent learning

`src/qdw/hotswap/persistent.py`

get() calls _upsert with ON CONFLICT DO UPDATE. A concurrent initializer can replace a posterior that another worker just updated.

**Required:** Initialize with INSERT OR IGNORE; never overwrite an existing posterior from a prior-read path.

### QDW-FINAL-019 — The API factory fixture is still simulated, not an API fixture

`tests/factories/test_api_factory.py`

The fixture never generates files or boots HTTP. It manually completes nodes with status_code=200 and feeds {'ok': True} into a lambda gate.

**Required:** Generate a real temporary API artifact, boot it, call /health over HTTP, hash the artifact, and prove a broken variant fails the same verifier.

### QDW-FINAL-020 — Integration E2E still bypasses execution/certification

`tests/integration/test_e2e.py`

The flow connects world/intelligence/ideas/product services but does not prove FactoryRun→WorkGraph→HotSwap→Executor→Artifact→independent contractor→BuildCertificate→release.

**Required:** Add one canonical V10 exemplar through the real execution spine.

### QDW-FINAL-021 — The self-review system is stored as an imported artifact, not integrated as QDW runtime

`qdw_review/qdw_self_review_system_2026-08-18 + missing src/qdw/review`

The previous review pack and ZIP are committed, but no native src/qdw/review service exists. QDW cannot autonomously invoke or persist review runs.

**Required:** Integrate this final pack as native review tables/services/manifests and then remove/archive the stale nested artifact.

### QDW-FINAL-022 — CI migration gate does not test the current migration set

`.github/workflows/ci.yml`

The migration step only asserts versions 1 and 2; current repository has migrations 3 and 4.

**Required:** Assert exact expected migration sequence/checksums and run fresh + populated upgrade + drift tests.


## Direction

Do not restart the architecture. Preserve the current QDW substrate and harden the evidence/execution spine.
The major final change is to make review itself a first-class QDW service and use it to prove the remaining
fixes automatically.

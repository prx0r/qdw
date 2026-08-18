# MASTER IMPLEMENTATION PROMPT — QDW SELF-REVIEW SYSTEM

Target starting review: `prx0r/qdw@c1ab1e46c41587c85253278ed5e012b0f757a551`.

You are not being asked merely to "fix findings". You are installing a permanent peer-review capability so
future QDW work can review itself.

## Mission

1. repair the current trust/provenance/migration defects in `docs/01_CURRENT_QDW_PEER_REVIEW.md`;
2. integrate deterministic `qdw-review` scanning;
3. add reviewer contractors to the existing Contractor/WorkGraph substrate;
4. add adversarial Red Team execution with real receipts;
5. add persistent finding history;
6. add independent Review Certificates;
7. expose peer review through QDW CLI/API/MCP;
8. make one full QDW self-review run against the resulting exact Git SHA.

## Non-negotiable anti-cheat rule

Never change a frozen acceptance test merely because production code fails it.

The sequence is:

```text
freeze acceptance bytes/hash
→ run against current code
→ retain FAIL receipt
→ change production code
→ rerun exact same test bytes
→ retain PASS receipt
```

If a required tool is unavailable, status is UNVERIFIED/BLOCKED.

## Phase 0 — establish donor state

Record:
- exact current Git SHA;
- git status;
- migration file hashes;
- test collection count;
- current deterministic test results;
- current branch/CI status if available.

Create `.qdw/review/baseline/`.

Do NOT edit 0001/0002 further.

## Phase 1 — migration immutability first

Current defect:
persistent HotSwap tables were added to existing `0002_global.sql`.

Required repair:
- decide and document canonical locked bytes for already-shipped migrations;
- new schema change becomes `0003_*` or later;
- `schema_versions`/new digest table records SHA-256 + filename;
- startup recomputes applied migration hashes and fails on drift;
- fresh DB and sequentially-upgraded DB schema fingerprints match;
- half-failing migration proves atomicity;
- `Database.migrate(custom_dir)` actually honors custom_dir.

Do not fake compatibility by deleting schema_versions rows.

## Phase 2 — proof boundary

Repair:
- `scripts/build_certificate.py` may not provide empty mandatory command sets;
- release acceptance specs are frozen files and content-hashed;
- certificate verifier revalidates artifacts, receipts, logs, spec and ledger binding;
- distinction between local envelope hash and cryptographic signature is explicit;
- test the verifier by mutating each subject.

Important negative-test semantics:
for pytest-based adversarial tests the pytest process should normally PASS while asserting bad behavior is rejected.
Do not require "negative test process exits nonzero" as a blanket rule.

## Phase 3 — evidence binding

Repair:
- FactoryRegistry activation uses a true fixture certificate bound to exact factory/version/fixture/artifacts.
- ProductRegistry.release verifies certificate existence/status/subject/run/artifacts.
- ContractorRegistry same-version mutation rejected.
- Contractor activation requires its own fixture certificate.
- Idea BUILD_READY consumes reviewer evidence or explicit typed human override rather than unbound bool.
- Human irreversible decisions bind actor/source.

Run supplied overlay trust tests unchanged.

## Phase 4 — atomic provenance

Current state transitions and ledger events are split transactions.

Implement one of:
A. `Ledger.append(..., con=existing_connection)`; or
B. durable transactional outbox written alongside canonical state.

Every canonical state mutation that requires provenance must satisfy:
state + event/outbox commit together.

Run injected-failure tests against graph, product, human, idea, contractor and review transitions.

## Phase 5 — WorkGraph hardening

- graph lifecycle DRAFT→VALIDATED/FROZEN→RUNNING;
- DAG validation required before execution;
- graph structure immutable after freeze;
- one documented max_attempts/retries meaning;
- durable attempt identities;
- unknown economics remain explicit;
- scheduler policy decides block/info/prior treatment;
- exactly-one claims under concurrency;
- terminal transition races rejected.

## Phase 6 — HotSwap durability

- persistent RouteRegistry uses route_definitions;
- QDWSystem reloads active routes;
- posterior updates atomic under concurrency;
- quota semantics explicitly durable or refreshable snapshot;
- route price/capability/freshness observations evidential;
- restart tests.

Do not merely persist the bandit while losing the candidate set.

## Phase 7 — real composition root

QDWSystem must compose the canonical global services that already exist:
WorldStore, intelligence services, OpportunityStore, Ideas, HumanQueue, ContractorRegistry, ProductRegistry,
Watch, Catalog, proof/review services, route registry, factories, graphs, economics.

Interfaces delegate to this system.

Update the canonical E2E fixture so it obtains services through QDWSystem, not hand-instantiated islands.

## Phase 8 — real V10 exemplar

Build one deterministic gold-standard factory example.

Required path:

```text
SourceResult
→ Observation
→ Pain/Capability signal
→ Opportunity
→ Idea
→ evidence-backed reviews
→ FactoryRun
→ validated/frozen WorkGraph
→ HotSwap route
→ executor
→ real artifact
→ independent contractor gates
→ BuildCertificate
→ Product
→ release
→ Product Passport
→ typed Outcome
```

For an API factory, actually generate/boot/call HTTP. Feeding `ok=True` into a gate is not a factory fixture.

Run artifact mutation and unrelated-certificate attacks.

## Phase 9 — install deterministic self-review

Port/vendor `reference/src/qdw_review`.

Commands must work:

```bash
qdw-review modules
qdw-review scan . --profile quick --out .qdw/review
qdw-review report .qdw/review/latest.json --html .qdw/review/report.html
qdw-review sarif .qdw/review/latest.json --out .qdw/review/review.sarif
```

Static reviewers are deterministic; no network or LLM is required.

## Phase 10 — canonical ReviewService

Apply `integration/migrations/0003_review_system.sql` as a NEW migration adjusted to final numbering.

Compose:
- ReviewerRegistry
- ReviewService

Persist:
- review runs;
- module runs;
- findings/evidence;
- attacks;
- suppressions;
- certificates.

Reviewer definitions are immutable by version.

## Phase 11 — reviewer contractors

Register all `manifests/reviewers/*.json`.

Use existing WorkGraph/Contractor machinery.

Implement:
- `review.full`
- `review.change-aware`

Do not create a second scheduler/orchestrator.

## Phase 12 — Red Team

Load `attacks/ATTACK_CATALOG.json`.

Each required attack must have:
- attack ID;
- exact subject SHA;
- command/test identity;
- result;
- receipt;
- expected rejection reason.

Start with supplied overlay tests. Add real tests for missing campaigns.

## Phase 13 — claim consistency

Implement/dogfood `review.claim-consistency`.

It specifically challenges terms:
atomic, transactional, immutable, persistent, real, E2E, official protocol, single composition root, PROVEN.

A docstring is never accepted as proof of its own claim.

## Phase 14 — runtime/CI

Fix Docker build order.

Release CI should prove as appropriate:
- compileall;
- ruff;
- pyright;
- tests;
- zero mandatory skips;
- migration fresh/upgrade/drift;
- concurrency;
- adversarial;
- real factory fixture;
- wheel build + fresh install;
- Docker clean build + run + /health;
- actual MCP client list/call;
- certificate/artifact/ledger mutation;
- qdw-review release profile;
- Review Certificate.

Record remote workflow evidence separately from local receipts.

## Phase 15 — QDW reviews itself

Run full review against the exact final SHA.

You may not issue `REVIEW_CERTIFIED` if:
- repo dirty;
- mandatory module absent;
- HIGH/CRITICAL unsuppressed finding remains;
- mandatory attack missing;
- required receipt missing;
- producer == certifier where independence policy forbids it.

## Required final output

Produce:
- exact final SHA;
- migration hashes;
- current test counts;
- failing-before / passing-after receipts for supplied regressions;
- review report JSON;
- interactive HTML;
- SARIF;
- Build Certificate;
- Review Certificate;
- unresolved findings, if any;
- remote CI evidence, if available.

Use `BLOCKED` instead of inventing evidence.

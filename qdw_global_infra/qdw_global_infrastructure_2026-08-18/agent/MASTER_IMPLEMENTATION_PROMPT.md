# MASTER IMPLEMENTATION PROMPT — QDW Global Infrastructure

Build this pack into the real QDW repository as one coherent global intelligence and product layer.

Canonical chain:

```text
SourceResult
→ Observation / Entity / Claim / Relation
→ Pain / Startup / Capability intelligence
→ Opportunity
→ Idea Genome / reviews / cemetery
→ Factory OS WorkGraph
→ Contractors + HumanQueue
→ Product / Product Passport / Factory Genome
→ Domain / Publication
→ Outcome
→ Portfolio learning
```

Gitgoblin is a sibling product being built separately. Implement only the supplied Gitgoblin client
contract/adaptor boundary. Do not rewrite Gitgoblin.

## Rule zero

No task is DONE because code exists, Markdown says PASS, or an agent claims a command ran.

For every task:
1. freeze and hash acceptance criteria before implementation;
2. implement the smallest complete slice;
3. run required commands through QDW VerificationRunner;
4. retain raw stdout/stderr and hashes;
5. run negative/adversarial tests;
6. run the regression suite;
7. generate a certificate only from successful process receipts.

If a command did not execute, status is UNVERIFIED or BLOCKED, never PASS.

## Canonical state

One transactional QDW DB owns identity and workflow state. Never introduce canonical `painfinder.db`,
`ideas.db`, `products.db`, `stackoracle.db`, or contractor-specific DBs.

External search/index/analytics systems may be read models only.

## Build order

### G0 Verification first
Install `qdw.proof.runner`, `qdw.proof.certificate`, `qdw.proof.test_guard`.

Prove:
- real zero exit -> PASS receipt;
- nonzero -> FAIL;
- timeout -> FAIL;
- certificate rejects missing/failed receipt;
- fake `assert True` test detected;
- stdout/stderr hashes recompute.

Run `python -m compileall` across all source/test code.

### G1 Unified schema
Add the global tables to the existing Factory OS migration system. Do not drop old tables.

Prove:
- empty database migration;
- second migration is idempotent;
- `PRAGMA foreign_key_check` empty;
- old Factory OS tests still pass.

### G2 World state
Install SourceResult and WorldStore.

Persist distinct states:
`ERROR != OK_EMPTY != OK`.

Never convert rate limit, auth error, timeout, parse error or server failure into zero results.

### G3 Intelligence
Install PainFinder, StartupRadar, StackOracle, AlternativeAPI and Opportunity synthesis.

Add source adapters incrementally:
Hacker News → YC OSS → APIs.guru → MCP Registry → Gitgoblin client → analytics/provider collectors.

Each adapter gets:
- deterministic mocked contract test;
- explicit failure test;
- separately-labelled optional live smoke.

### G4 Ideas
Install IdeaService, IdeaLibrary, IdeaReviewPipeline, IdeaDossier and WatchService.

Enforce:
`DISCOVERY → EVIDENCE_REVIEW → ADVERSARIAL_REVIEW → PORTFOLIO_REVIEW → ARCHITECTURE_REVIEW → BUILD_READY`.

Idea identity is problem + solution + customer + product form, not title/domain.

Never delete rejected ideas. Cemetery stores assumptions and revisit triggers.
Watch triggers only request re-evaluation; they do not silently revive/build.

### G5 Contractors
Load immutable contractor manifests. Contractor runs are ordinary WorkGraph nodes.

Changing a gate requires a version bump.
A producer cannot satisfy an independent certification gate when policy requires independence.

### G6 HumanQueue
Use strict idempotent approval states for domains, credentials, account terms, paid budgets and
other irreversible/account-bound operations.

Agents cannot self-approve.

### G7 Products
Install ProductRegistry, FactoryGenome, Product Passport and OutcomeEvents.

A released product retains idea, factory/run and certificate lineage.

### G8 Publishing
Load DistributionRegistry manifests.

Domain path:
search → authoritative check → HumanQueue approval → purchase adapter → DNS/deploy → external smoke.

The deterministic fixture must never spend money.

Generate docs and portfolio views from Product Registry data.

### G9 Outcomes
Ingest raw real usage/cost/revenue/health events through provider-neutral adapters.
Never invent metrics.

### G10 Gold-standard exemplar
Run one full product through the entire system. Recommended: AlternativeAPI.

## OSS reuse policy

Borrow mechanisms, not every dependency:
- Backstage: catalog/template ergonomics.
- OpenLineage: optional lineage export.
- in-toto: attestation compatibility.
- Rekor: optional external anchor.
- OpenCoven Feedback: Painfinder product patterns.
- APIs.guru / MCP Registry: source adapters.
- LiteLLM: provider adapter; HotSwap remains policy.
- PostHog/Plausible: optional outcome adapters.
- MkDocs Material: generated docs.
- Cloudflare: optional domain/deploy adapters.
- sqlite-vec: optional semantic retrieval after deterministic identity.
- DuckDB: optional analytics read model.

Do not import Temporal, Backstage, Marquez, graph DBs or extra agent frameworks merely to make the
architecture look advanced.

## Anti-cheat rules

Never:
- use `assert True`;
- weaken/delete a failing acceptance test to close a task;
- add skip/xfail around a required gate;
- fabricate command output, hashes, costs, network results, CI state or certificates;
- manually author PASS receipts;
- hide source errors;
- claim Docker/CI/live integrations passed without executing them.

A transparent BLOCKED or UNVERIFIED state is correct.

## Phase command pattern

Run these via VerificationRunner and record receipts:

```text
python -m compileall -q src/qdw tests
pytest <focused tests>
pytest
qdw doctor
qdw ledger verify
```

When present, additionally prove:
- Docker clean build + health smoke;
- real in-process MCP call;
- fresh wheel install.

## Final build certificate

Must include exact Git SHA/dirty state, dependency-lock hash, acceptance hashes, command receipts,
test artifacts, fixture results, artifact hashes, ledger root and negative-test results.

Overall status is PROVEN only when all mandatory receipts really exist and pass.

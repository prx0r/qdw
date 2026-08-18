# MASTER RECONCILIATION PROMPT — QDW FEDERATION

You are reconciling five repositories:

```text
prx0r/qdw
prx0r/qdw-forge
prx0r/qdw-sandbox
prx0r/gitgoblin
prx0r/dell
```

Use exact starting pins in `pins/REPOS.json`.

This is a **federated architecture**, not a monorepo consolidation exercise.

Your final system has exactly one cross-domain economic/lifecycle authority: **QDW**.

---

# 0. Non-negotiable ownership

## QDW owns
- portfolio decisions;
- opportunity/factory allocation;
- canonical WorkGraph and node lifecycle;
- scheduler;
- final cross-domain execution route;
- cost ledger;
- QDW verification/review;
- factory/product release;
- business outcomes/learning;
- human irreversible-action policy.

## GitGoblin owns
- its raw source observations;
- source cursors;
- expertise/attention graph;
- technical/frontier signals;
- its own standalone product/API.

It exports observations/proposals. It never sets QDW portfolio decisions.

## Dell owns
- provider/model/deal evidence;
- claims/assertions/offers;
- source freshness/health;
- provider-specific source adapters;
- Dell's own public recommendation product.

It emits resource candidate snapshots + `ADVISORY` recommendations. QDW HotSwap remains final authority.

## QDW Forge owns
- CapabilityAsset / FactoryCapsule registry;
- asset activation;
- capability leases;
- invocation transport;
- invocation records;
- asset-local verified performance.

QDW pins `asset_id@version`; Forge must execute exactly that lease. QDW verifies the result.

## QDW Sandbox owns
- experiments.

Production EstateRouter / EstateVerificationService / duplicate schedulers are retired as authorities.
Useful contracts/algorithms graduate into the appropriate owner.

If an implementation conflicts with this table, stop and correct architecture rather than creating a bridge
between two competing truths.

---

# 1. Clone + freeze evidence

Run:

```bash
bash scripts/clone_pinned.sh worktrees
python scripts/verify_pins.py --root worktrees
python scripts/federation_inventory.py --root worktrees > baseline-inventory.json
```

Record for every repo:
- starting SHA;
- dirty state;
- Python version;
- dependency resolution;
- test collection count;
- test result;
- branch;
- current migrations/schema version if applicable.

Run each repository's original mandatory tests BEFORE applying any integration patch.

Store receipts.

If any source repo is red at its pin, classify `DONOR_BASELINE_FAILED`; do not attribute failure to integration.

Create integration branches with `scripts/create_integration_branch.sh`.

---

# 2. Freeze contract tests before implementation

Run the pack's independent reference suite first.

Copy/freeze each repository-specific contract test from `cross_repo_patches/*/tests`.

Create hashes and do not weaken them to reach green.

For real QDW, add `tests/federation/` containing at least:
- authority matrix;
- GitGoblin ingest;
- Dell advisory snapshot;
- Forge lease-pinned invocation;
- certificate-subject binding;
- external failure semantics;
- stale resource semantics;
- route finality;
- double-learning separation;
- protocol compatibility;
- full V10/V11 flow.

A contract test failing is expected before integration. Preserve the failure receipt.

---

# 3. Introduce federation contracts in QDW

Apply/adapt:

```text
native/qdw/src/qdw/federation/
native/qdw/migrations/0010_federation.sql
```

Use the next genuinely unused migration number.

Do not create a new database.

Do not make a package dependency on this ZIP's `qdw_federation` reference module. The reference module exists to
prove the model; production types live under `qdw.federation`.

Core types:
- FederatedRef
- ExternalStatus
- ExternalSnapshot
- DecisionAdvisory
- CapabilityExecutionRequest
- ExternalInvocationOutcome
- VerificationCertificateRef

Every external object remains externally identified. QDW uses local IDs plus FederatedRef mappings.

---

# 4. External-system registry

Register:

```text
gitgoblin  ORACLE
dell       ORACLE
forge      CAPABILITY_EXCHANGE
sandbox    INCUBATOR
```

Store:
- protocol version;
- base URL;
- enabled;
- trust policy;
- freshness policy;
- health events.

Configuration may come from environment/settings. Credentials never enter WorkNode payloads or review logs.

No external repo may connect directly to QDW's SQLite database.

---

# 5. GitGoblin integration

GitGoblin already has a VentureLab/Cuntgoblin exporter.

Add the QDW federation exporter in:

```text
cross_repo_patches/gitgoblin/gitgoblin/integrations/qdw.py
```

and expose:

```text
GET /v1/export/qdw
```

The transfer is:

```text
GitGoblin source observations
→ FrontierSignal
→ versioned ObservationBatch
→ QDW SourceResult
→ QDW WorldStore observations
```

Preserve:
- original observation ID;
- evidence digest;
- detected/observed time;
- source family;
- sector;
- confidence;
- source revision;
- batch digest;
- cursor.

GitGoblin `Opportunity` objects become `OpportunityProposal`, not QDW Opportunity/Decision rows.

### Acceptance

1. same batch twice -> no duplicated observation semantics;
2. collector/server failure -> QDW ERROR/UNAVAILABLE, never OK_EMPTY;
3. successful empty export -> OK_EMPTY;
4. proposal BUILD/WATCH/RESEARCH does not mutate QDW portfolio state;
5. evidence hash remains traceable.

---

# 6. Dell integration

Do not duplicate Dell's provider scrapers/source-health/evidence pipeline inside QDW.

Add `app/federation.py` and expose a dedicated candidate/advisory endpoint using Dell's DecisionService.

Desired wire endpoint:

```text
POST /v1/federation/resolve
```

Input is Dell's ResolveRequest-compatible workload/constraints/preferences/evidence policy.

Output explicitly declares:

```json
{
  "schema_version": "qdw-federation-resource/1",
  "authority": "ADVISORY",
  "recommended": ...,
  "alternatives": ...,
  "excluded": ...,
  "decision": ...
}
```

### Critical mapping rule

Do **not** map:

```text
Dell score → QDW p_success
Dell confidence → QDW p_success
Dell evidence coverage → QDW quality
```

They are separate fields.

Dell should ideally expose all feasible assessed candidates eventually. For MVP, recommended + alternatives +
excluded is acceptable if the limitation is explicit.

QDW stores the raw response as a content-addressed external snapshot and a normalized snapshot.

### Failure semantics

- Dell resolves zero candidates normally -> OK_EMPTY.
- timeout/HTTP 5xx -> UNAVAILABLE.
- stale evidence outside policy -> STALE/POLICY_BLOCKED.
- protocol mismatch -> INCOMPATIBLE_PROTOCOL.

Never turn network failure into `[]`.

---

# 7. QDW final route composition

Keep QDW's existing `HotSwapRouter` as final route authority.

Build a candidate collector:

```text
local QDW routes
+ Dell resource snapshot
+ Forge certified assets
+ optional graduated Estate feature policies
          ↓
QDW HotSwap
```

The production adapter must preserve route provenance:
- Dell snapshot digest;
- Dell advisory ID;
- Forge asset manifest/certificate;
- task spec;
- route policy/version;
- QDW final decision digest.

### Estate algorithms

Freeze tests for historical/cluster/cascade behavior from Sandbox.

Port useful algorithmic behavior as:
- pure scoring/features;
- QDW HotSwap policy plugin;
- no DB ownership;
- no independent route lifecycle.

Do not call EstateRouter as the final production route service.

---

# 8. Forge capability exchange

Apply the Forge federation patch.

QDW flow:

1. discover ACTIVE certified Forge assets;
2. QDW HotSwap selects `forge:<asset>@<version>`;
3. QDW creates a lease **pinned to exact asset/version**;
4. invoke with a unique QDW idempotency/request ID;
5. Forge returns `SUCCEEDED_UNVERIFIED` or `FAILED`;
6. QDW stores invocation provenance/cost;
7. QDW independently verifies;
8. QDW emits VerificationCertificateRef;
9. Forge resolves/verifies it;
10. Forge updates invocation + asset-local profile.

### Anti-substitution

If QDW selected:

```text
asset=A version=1
```

and Forge returns:

```text
asset=B
```

the adapter must fail with a substitution error.

### Verification API

Remove QDW use of:

```json
{"certificate_id":"...", "passed":true}
```

The caller must not choose verification status.

Use:

```json
{"certificate": { ... signed/content-hashed reference ... }}
```

Forge resolves/validates:
- issuer allowlist;
- certificate hash/signature;
- invocation ID;
- asset/version if included;
- output hash;
- policy hash;
- certificate status.

Legacy `passed` endpoint may survive only behind a compatibility flag and is forbidden for QDW federation mode.

---

# 9. FactoryCapsules

Forge `FactoryCapsule` is a high-value bridge.

Model a capsule as a routable capability:

```text
capability = factory.api.build
asset = factory-capsule-api@version
```

QDW does not automatically import another scheduler from the capsule.

Default mode:
- invoke capsule as service;
- receive artifact refs/output;
- independently verify under QDW's FactoryRun acceptance.

Optional future mode:
- capsule explicitly exports a QDW WorkGraph template;
- QDW imports/validates/freezes it;
- QDW remains scheduler.

This enables factories-as-services / Moltwork-style work exchange without dual graph truth.

---

# 10. Sandbox graduation

Do not "integrate Sandbox" as a live production service wholesale.

For each Estate feature:

```text
feature
→ target owner
→ frozen donor fixture
→ target implementation
→ equivalence/adversarial tests
→ production cutover
→ old authority disabled
```

### Graduate to federation contracts
- CapabilityRequest
- ExecutionConstraints
- ResourceDescriptor
- ExecutorConfiguration
- ResourceProfile

### Graduate to QDW
- ContextPack/context assembly
- execution episode observability concepts
- historical/cluster/cascade policy algorithms
- HumanOracle mapped to Contractor/HumanQueue
- Bounty mapped to Opportunity/Contractor work
- canonical data-rights constraints
- any artifact-CAS improvements better than current QDW ArtifactStore

### Disable as production authority
- EstateRouter
- EstateVerificationService
- EstateScheduler
- duplicate lifecycle DB
- bundled `_review_system`
- bundled `_lifegit` runtime copies

Sandbox remains alive as an incubator after graduation.

---

# 11. Verification and certificate trust

External execution is not QDW success.

Canonical sequence:

```text
external invocation
→ SUCCEEDED_UNVERIFIED
→ QDW verification
→ QDW certificate
→ QDW WorkNode transition
```

Forge's own VERIFIED state is a local projection based on the QDW certificate.

A valid certificate from invocation X cannot verify Y.

Certificate references bind:
- issuer;
- certificate ID/hash/signature;
- exact external subject ID;
- output digest;
- verification policy digest;
- status.

Add substitution attacks.

---

# 12. Learning separation

Explicitly document/implement four different learning scopes.

## Dell
Learns facts/evidence about external inference resources.

## Forge
Learns:
`P(asset succeeds | capability)` and asset-local invocation cost.

## QDW HotSwap
Learns:
`P(route succeeds | QDW task cell)` plus QDW request/cost outcomes.

## QDW FactoryLearning
Learns:
factory/product/business outcomes.

Do not copy one system's alpha/beta row into another system.

A foreign posterior is a versioned source feature with:
- source;
- sample count;
- as-of;
- confidence;
- digest.

---

# 13. Costs

Every external invocation produces a QDW CostEvent.

Store at least:
- expected cost at route decision;
- lease max spend;
- Forge reported actual cost;
- provider/model nested cost if available;
- currency;
- source;
- unknown vs observed;
- external invocation ref.

Do not treat free/zero as equivalent to unknown.

---

# 14. Failure / health layer

Add federation doctor and health.

QDW should report independently:

```text
GitGoblin: OK/STALE/UNAVAILABLE
Dell:      OK/STALE/UNAVAILABLE
Forge:     OK/DEGRADED/UNAVAILABLE
Sandbox:   INCUBATOR/DISABLED
```

QDW itself can stay healthy when one oracle is unavailable, but route/opportunity decisions must carry degraded
reason codes.

Policy decides whether cached stale snapshots are usable.

---

# 15. Real protocol tests

After cloning and patching, do not stop at direct Python calls.

Run actual:
- HTTP TestClient/localhost API for GitGoblin export;
- HTTP Dell federation resolve;
- HTTP Forge asset/lease/invoke/cert flow;
- QDW API/MCP surface if federation is exposed there.

Use `respx` or local ASGI transports for deterministic offline integration where possible.

At least one V11 fixture may start all local services in subprocesses/containers.

---

# 16. V10/V11 gold flow

Build this exact fixture:

```text
GitGoblin source fixture
     ↓
frontier export
     ↓
QDW World observation
     ↓
QDW Opportunity/Idea fixture
     ↓
QDW WorkGraph WorkNode
     ↓
Dell candidate advisory
     ↓
Forge capability assets
     ↓
QDW HotSwap final route chooses Forge
     ↓
Forge pinned lease
     ↓
Forge invocation
     ↓
SUCCEEDED_UNVERIFIED
     ↓
QDW artifact/output verifier
     ↓
QDW certificate
     ↓
Forge certificate bind
     ↓
QDW node SUCCEEDED
     ↓
CostEvent + provenance + outcome
```

Assertions:
- exact source/advisory snapshot digests persist;
- no external service changes QDW state directly;
- chosen asset cannot be substituted;
- valid unrelated certificate fails;
- external outage is not zero candidates;
- cost is not invented;
- all state transitions have receipts/provenance.

---

# 17. Multi-repo CI

Each repo retains independent CI.

QDW adds federation CI:
- clone exact protocol pins;
- run own repo suites;
- run repo patch contracts;
- run QDW federation contracts;
- run V10 local;
- optionally V11 service/container;
- upload integration proof artifacts.

Do not use moving `main` during a certified release.

---

# 18. Pin upgrade bot/workflow

Once stable, automate discovery of new repo heads.

The updater:
1. fetches candidate head;
2. compares protocol/API changes;
3. checks changelog/commits;
4. creates temporary worktree;
5. runs full federation suite;
6. generates compatibility report;
7. if PASS, proposes pin update.

It never updates production pins simply because a newer SHA exists.

---

# 19. Repo-level commit plan

Make bounded commits, ideally:

### qdw
1. federation contracts/schema
2. external snapshot store
3. GitGoblin adapter
4. Dell adapter/candidate collector
5. Forge execution adapter
6. HotSwap federation integration
7. certificate binding
8. tests/V10
9. interfaces/doctor
10. federation CI

### qdw-forge
1. CertificateReference contract
2. resolver + verification v2
3. pinned-invocation assertion
4. API change + compatibility flag
5. contract tests

### gitgoblin
1. QDW exporter
2. endpoint
3. contract tests/docs

### dell
1. federation response module
2. API endpoint
3. contract tests
4. endpoint/candidate expansion if needed

### qdw-sandbox
1. federation/graduation adapter
2. donor behavior fixtures
3. disable production authority path
4. graduation documentation

Never mix a broad refactor with protocol integration unless required by a frozen test.

---

# 20. Self-review integration

QDW's native peer-review system must review the federation changes.

Add/change-aware reviewers for:
- authority duplication;
- cross-service trust;
- failure semantics;
- external freshness;
- evidence substitution;
- cost provenance;
- protocol compatibility;
- pin drift;
- side-effect permissions.

A federation ReviewCertificate should bind all five pin SHAs.

---

# Final exit evidence

Return a machine-readable report containing:

```text
source pins before
source pins after
final branch SHAs
repo test counts/results
federation contract results
protocol versions
migration hashes
external snapshot fixture hashes
V10/V11 receipt IDs
attack results
QDW ReviewCertificate
unverified/live-only items
```

No claim of "integrated" until `acceptance/INTEGRATION_EXIT_GATE.json` passes.

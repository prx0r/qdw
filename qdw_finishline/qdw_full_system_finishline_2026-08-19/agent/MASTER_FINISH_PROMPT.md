# MASTER FINISH PROMPT — COMPLETE THE CURRENT QDW FEDERATION

You are finishing the system from the exact reviewed heads in `CURRENT_HEADS.json`.

This is not a greenfield architecture task. The current repositories already contain useful working code. Your job
is to reconcile, repair and prove the real runtime without creating parallel infrastructure.

## Canonical roles

```text
QDW         = economic/lifecycle authority
GitGoblin   = repository/frontier intelligence oracle
Dell        = model/provider/deal oracle
QDW Forge   = capability lease/invocation exchange
Forgejo     = source repository host/provenance boundary used by Forge
Sandbox     = incubator/donor only
```

If code violates this authority split, fix the ownership problem rather than writing synchronization between two
authoritative copies.

---

# Phase 0 — freeze current truth

Run:

```bash
bash scripts/clone_reviewed_heads.sh worktrees
python scripts/verify_reviewed_heads.py --root worktrees
```

Record exact:
- SHA;
- branch/default branch;
- dirty state;
- Python version;
- resolved environment;
- pytest collection count;
- native test output;
- schema/migration state.

Use a separate virtual environment for every repository.

Do not modify a source checkout before baseline receipts exist.

The commit-message test counts in `CURRENT_HEADS.json` are context only, never proof.

---

# Phase 1 — prove known defects first

Set:

```bash
export QDW_WORKTREES="$PWD/worktrees"
```

Run the independent source regression suite before applying patches.

It should fail against the reviewed heads on the defects listed in:

`lab/EXPECTED_BASELINE_FAILURES.json`

Store those failures. They are valuable evidence.

Never:
- delete the external gate;
- weaken an assertion;
- mark it skipped;
- replace it with an existence test;
- alter the expected-baseline list to hide a defect.

---

# Phase 2 — create bounded integration branches

```bash
bash scripts/create_finishline_branches.sh worktrees
```

One repository, one branch.

Do not create a monorepo.

---

# Phase 3 — apply reviewed overlays

Preview:

```bash
python scripts/apply_overlays.py --pack-root . --worktrees worktrees
```

Then:

```bash
python scripts/apply_overlays.py --pack-root . --worktrees worktrees --apply
python scripts/apply_semantic_edits.py --root worktrees
```

Review every diff before running formatting or broad refactors.

The semantic patcher deliberately fails if current source anchors have drifted. Do not bypass that failure by fuzzy
global replacement. Inspect the changed upstream code and adapt deliberately.

---

# Phase 4 — QDW: make the federation actually live

The current QDW has federation objects but its composition root creates no real external clients.

Implement:

```text
QDWSystem
  └ FederationConfig
     ├ GitGoblinHTTPClient
     ├ DellHTTPClient
     └ ForgeHTTPClient
```

and expose:

```text
federation_store
federation
federation_certificates
federation_verification_policies
federation_runtime
```

A missing URL means unconfigured, not a successful empty source.

Delete production `qdw.federation.forge_client`. Test doubles belong only under tests.

---

# Phase 5 — QDW migration 0011

Do not edit applied migration 0010.

0011 must:
- add `route_definitions.fixed_request_cost_usd`;
- retire `forge_leases`;
- retire `forge_invocation_certs`;
- preserve only non-secret historical receipt facts;
- create durable federation attempts;
- create QDW external certificates;
- create unique cost/learning effect records;
- create protocol pin/sync records.

After migration, scan the entire QDW DB file and source tree for leaked Forge lease tokens.

A reusable Forge token must not exist in QDW persistence, logs, certificates or public result payloads.

---

# Phase 6 — HotSwap restart correctness

Current `Route.fixed_request_cost_usd` is lost by persistent route roundtrip.

Fix both write and read.

Required real test:

```text
save Forge route at $0.012/call
destroy QDWSystem
construct QDWSystem from same DB
route cost remains exactly $0.012
```

No fake token price may be synthesized.

Dell token pricing and Forge per-call pricing are different canonical price shapes and both must remain lossless.

---

# Phase 7 — GitGoblin wire contract

Current QDW calls `/v1/export/qdw`; current GitGoblin does not expose it.

Implement:

```http
GET /v1/export/qdw
```

Schema:

`qdw-federation-observation/1`

Response must contain:
- source system;
- source build revision;
- cursor;
- deterministic batch digest;
- observations;
- opportunity proposals.

Observation identity/evidence stays GitGoblin-owned.

Opportunity proposal authority is always `ADVISORY`.

QDW persists the proposal as external evidence. It may create a QDW Opportunity only through QDW scoring/evidence
policy. Never copy GitGoblin's external BUILD/WATCH decision into QDW portfolio truth.

Repeated export with no underlying change must have the same batch digest even if generated timestamp differs.

---

# Phase 8 — Dell wire contract

Repair Dell's cost invariant first:

If output tokens are nonzero and output price is unknown, workload cost is unknown.

Do not coerce it to zero.

Expose:

```http
POST /v1/federation/resolve
```

Schema:

`qdw-federation-resource/1`

Return:
- all eligible candidates;
- all excluded candidates and reasons;
- complete endpoint/model/provider facts;
- estimated workload cost;
- Dell score/confidence/coverage;
- recommendation;
- `authority=ADVISORY`.

QDW stores Dell score as Dell score. It is not QDW `p_success`.

Turn the current passing “known issue: recommended cost is lost” test into a strict regression.

---

# Phase 9 — Forge authentication and idempotency

This is mandatory security work.

Current bug:
`client_request_id` replay is queried before the lease token is checked.

Correct order:

```text
authenticate caller identity
→ verify signed lease token
→ compare lease client identity
→ compare capability
→ enforce operation
→ compare asset/version
→ then query client-scoped idempotency
→ exact input/route digest match
→ replay or execute
```

Required attack:

1. valid client performs request ID `r1`;
2. attacker sends invalid lease token with `r1`;
3. attacker receives no prior invocation data.

Idempotency key scope:

`authenticated_client_id + client_request_id`

Same key with changed arguments is a conflict.

Same key with another pinned route is a conflict.

Concurrent duplicates execute once.

---

# Phase 10 — Forge lease authorization

`allowed_operations` must be real policy, not metadata.

A lease without `invoke` cannot invoke.

Token claims and DB state must agree on:
- lease ID;
- client ID;
- capability;
- asset ID;
- version;
- operations;
- expiry.

Mismatch fails closed.

---

# Phase 11 — Forge immutable asset identity

Current activation changes `manifest_hash` because status/certificate live inside the hashed object.

Repair it.

Immutable definition includes:
- asset/version;
- kind/name;
- capabilities;
- transport;
- repository definition;
- pricing;
- declared quality;
- rights;
- I/O schemas;
- definition metadata.

Mutable state includes:
- candidate/active/paused/retired;
- activation certificate;
- activation time.

`asset_id@version` definition digest never changes after registration.

If the definition changes, bump version.

Migrate legacy hashes with explicit old→new mapping.

---

# Phase 12 — Forge verification trust

Remove caller-authored verification boolean.

Wire:

```json
{
  "certificate": {
    "issuer_system":"qdw",
    "certificate_id":"...",
    "certificate_hash":"...",
    "subject": {...},
    "subject_output_digest":"...",
    "policy_hash":"...",
    "status":"VERIFIED",
    "verification_url":"..."
  }
}
```

Forge resolves the certificate from its allowlisted QDW authority or verifies a configured signature.

Match:
- issuer;
- certificate hash;
- invocation ID;
- output hash;
- policy hash;
- status.

One certificate may affect one invocation exactly once.

Exact replay is idempotent.

A certificate from another invocation is rejected.

---

# Phase 13 — Forge costs

Distinguish:

```text
quoted cost
actual cost
billable cost
pricing violation
```

The lease budget authorizes the quote.

If actual < quote:
- refund delta.

If actual > quote:
- never silently charge beyond authorization;
- cap billable to quote;
- mark pricing violation;
- feed the discrepancy into asset/provider quality review.

Dispatcher failure without a trusted cost receipt is not automatically billed at quote.

QDW CostEvent uses the Forge billable/accepted external cost receipt, not a guessed request estimate.

---

# Phase 14 — Forge migrations

Keep legacy bootstrap only as V1 baseline compatibility.

Every new schema change is:
- numbered;
- immutable;
- content hashed;
- applied once;
- drift checked.

Test fresh DB and upgraded V1 DB.

Test migration interruption/transactionality.

---

# Phase 15 — Forgejo integration

This is the other half of the “git/Fujin” lane.

The old Forgejo sync stops at 50 repos and reads moving default refs.

Finish it:

```text
paginate org repos
→ resolve default branch/ref to commit SHA
→ fetch qdw.yaml at exact SHA
→ validate schema
→ digest exact manifest content
→ register immutable asset definition
→ bind repo URI + commit + manifest digest
→ write per-repo sync receipt
```

Required tests:
- 61 repos all seen;
- manifest read at commit, never `main`;
- same version changed definition rejected;
- repeat unchanged sync idempotent;
- one malformed repo does not erase successful receipts for others;
- typed error preserved.

Do not store Forgejo access token in sync receipts.

---

# Phase 16 — QDW final route authority

Candidate inputs:

```text
local QDW routes
Dell resource candidates
Forge certified capability assets
```

QDW HotSwap is the sole final route authority.

Forge's local route decision is nested provenance.

Dell recommendation is advisory.

Sandbox Estate routing may contribute pure features/policies but is not a final router.

Persist exact route binding:
- external ref;
- version;
- digest;
- external snapshot/advisory;
- foreign profile metadata.

---

# Phase 17 — durable cross-service attempt

Implement the QDW attempt state machine in the overlay.

Required states:

```text
DISCOVERING
CANDIDATES_READY
ROUTED
RUNNING
SUCCEEDED_UNVERIFIED
VERIFYING
VERIFIED
COMMITTED
FAILED
```

Only `COMMITTED` is terminal success.

Crash recovery:

### Before external invocation
Retry safely with same QDW attempt ID.

### During invocation
Acquire a fresh Forge lease if the secret was lost; use the same stable client request ID. Forge returns the
idempotent invocation if it already executed.

### After `SUCCEEDED_UNVERIFIED`
Do not invoke again; use persisted invocation/output refs and independently verify.

### After verification
Unique effect rows prevent duplicate cost/posterior changes.

---

# Phase 18 — QDW verification

Do not build another verifier.

Use existing `VerificationService`.

Every externally executable capability requires a registered verification policy.

Unknown policy → fail closed.

The fixture policy in this pack is only for the test capability.

FactoryCapsules and real capabilities must bind their own existing factory acceptance plans.

Verification command receipts and artifacts must survive restart.

---

# Phase 19 — WorkGraph integration

For a real WorkNode:

```text
node RUNNING
external invocation finishes
node remains non-success
QDW verifier runs
certificate VERIFIED
node -> VERIFYING -> SUCCEEDED
federation attempt -> COMMITTED
```

A Forge status cannot directly transition the node.

Producer cannot certify itself.

---

# Phase 20 — cost and learning exactly once

One federation attempt creates at most:
- one canonical CostEvent;
- one QDW route-learning effect.

Use unique attempt-linked effect records.

Forge profile and QDW HotSwap posterior remain different statistical populations.

Do not copy Forge alpha/beta into QDW.

A Forge profile may become a sourced prior feature with sample count and digest.

---

# Phase 21 — Sandbox

Do not connect Sandbox as another live production service.

Keep:
- donor tests;
- experimental Estate/LifeGit work;
- pure algorithm/reference code.

Block:
- EstateRouter as QDW final route;
- EstateVerificationService as QDW verifier;
- EstateScheduler as WorkGraph authority.

Graduate useful work through behavior-equivalence tests.

---

# Phase 22 — independent test lab

The external `lab/` package is mandatory precisely because in-repo tests previously passed against a fake Forge.

Run:

```bash
export QDW_WORKTREES="$PWD/worktrees"
pytest lab/tests/source -q
```

Then start real patched services and run:

```bash
pytest lab/tests/contract -q
pytest lab/tests/e2e -q
bash lab/scripts/v11_restart.sh
```

The lab must never:
- import qdw-forge into QDW;
- read a sibling service DB;
- patch process internals;
- bypass HTTP authentication.

---

# Phase 23 — adversarial matrix

Mandatory attacks:
- guessed idempotency key with invalid lease;
- changed payload replay;
- changed route replay;
- disallowed operation;
- expired lease;
- asset substitution;
- certificate wrong issuer;
- certificate wrong invocation;
- certificate wrong output;
- certificate replay;
- duplicate concurrent invoke;
- route restart losing fixed cost;
- QDW restart after invoke;
- Dell outage represented as empty;
- unknown Dell output price represented as zero;
- Forgejo branch moves after commit resolution;
- same asset version changes manifest;
- external proposal escalates itself to QDW decision;
- duplicate CostEvent;
- duplicate posterior effect;
- secret-token scan.

Each attack needs an executable negative test.

---

# Phase 24 — multi-repo CI

Each repository keeps its own native CI.

Add a QDW federation workflow that:
1. checks exact protocol pins;
2. installs each repo in isolated environment;
3. runs each native suite;
4. runs independent source gates;
5. starts sibling services;
6. runs protocol contracts;
7. runs V11;
8. runs restart;
9. exports receipts;
10. runs QDW native self-review.

Do not certify a moving `main/master`.

---

# Phase 25 — branch protection and release

The reviewed default branches are currently unprotected.

After federation CI is stable, require:
- native repo test check;
- federation source gate;
- protocol contract;
- V11;
- QDW review certificate.

Do not enable protection until check names are stable, but do not call the system release-ready without it.

---

# Completion report

Return machine-readable evidence:

```text
starting SHA per repo
ending SHA per repo
native tests before/after
independent source-gate before/after
protocol contracts
V11
restart V11
migration fresh/upgrade
security attacks
secret scan
route restart
CostEvent replay
posterior replay
QDW review certificate
unverified external/live conditions
```

The word `complete` is forbidden in the report unless every requirement in `acceptance/FINISH_LINE.json` is proven.

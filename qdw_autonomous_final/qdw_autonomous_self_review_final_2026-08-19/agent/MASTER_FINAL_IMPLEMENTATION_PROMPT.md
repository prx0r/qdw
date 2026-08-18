# MASTER FINAL IMPLEMENTATION PROMPT — QDW AUTONOMOUS SELF-REVIEW

Starting subject:
`prx0r/qdw@ab809c8e6b829374199eb49dc71cd6f499e4f7fb`

This is the final hardening/integration pass. Do not rewrite QDW. Preserve its current Factory OS, World,
Idea, Human, Product and HotSwap work. The objective is to finish the trust/execution spine and make peer
review a native autonomous QDW capability.

## What the latest peer review found

The latest commit claims all prior findings were addressed, but exact source review still found blocking
issues including:

- two incompatible VerificationRunner receipt systems;
- BuildCertificate requirements inferred from observed receipts rather than a pre-frozen plan;
- CI gates not bound to the certificate receipt set;
- negative-test semantics treating nonzero process exit as desired evidence;
- factory/contractor/product authorization still based on generic gate_results;
- most WorkGraph state/event transitions still separate transactions;
- add_edge can persist a cyclic edge before raising;
- no graph freeze boundary;
- migration body/version recording not failure-proven atomic;
- legacy NULL migration hashes bypass drift enforcement;
- destructive migration 0004 lacks populated upgrade parity proof;
- Route persistence remains lossy and initializer races remain possible;
- API factory fixture remains simulated;
- current E2E still bypasses executor/artifact/certificate/release;
- self-review is committed as a nested pack, not native runtime.

Do not close any of these because a commit message says they are fixed.

## Fundamental rule

**Evidence, not assertions.**

Never accept:
- `passed=True`
- `verified=True`
- `certified=True`
- a generic passing gate ID
- a test count written in a commit
- an LLM saying "review passed"

as authorization.

Transitions consume typed evidence bound to the exact:
subject → version → definition hash → run → artifact set → acceptance policy.

## P0 — Freeze current baseline before editing

Record:
- exact starting SHA;
- git status;
- all migration file SHA-256 values;
- schema_versions rows;
- current DB schema fingerprint if a persistent DB exists;
- test collection;
- current deterministic test run;
- current CI/branch evidence if accessible.

Store under `.qdw/final-baseline/`.

Copy the supplied adversarial acceptance tests into the repo and HASH THEM BEFORE production fixes.
Do not change their bytes when a test exposes a bug.

## P1 — Migration trust first

Install the strict migration replacement.

Critical migration rule:
**never silently backfill an old NULL migration hash from whatever file is currently on disk.**

For existing DBs:
1. obtain a trusted known-good historical schema fingerprint;
2. run explicit `adopt_legacy_baseline(...)` with actor + note;
3. only then permit new migrations.

Prove:
- applied migration drift rejected;
- NULL digest blocks until explicit baseline;
- migration SQL + version/hash row apply atomically;
- intentionally broken migration leaves no partial table or version row;
- fresh DB and populated sequential upgrade DB have identical schema fingerprint;
- 0004 row counts/content survive;
- `PRAGMA foreign_key_check` empty.

Only then apply NEW migrations 0005, 0006, 0007, 0008 from this pack. Never edit old migration bytes again.

## P2 — One canonical VerificationService

Delete the dual truth, not necessarily compatibility import paths.

Canonical implementation:
`qdw.proof.verification_service.VerificationService`

Compatibility `qdw.core.verification.runner` / `qdw.proof.runner` may only re-export/adapt the same service.
They may not compute PASS independently.

Install `VerificationPlan` v2.

Requirements:
- plan/version immutable;
- plan hash exists before first command;
- run binds exact subject SHA, dirty state, cwd and environment hash;
- every receipt binds run ID + command ID;
- artifact snapshot is stored at run completion;
- required commands cannot be inferred from receipts;
- test process PASS is separate from AttackResult semantics.

Run the exact supplied verification attacks.

## P3 — BuildCertificate v2

Certificate issuance takes one `verification_run_id`.

It must refuse:
- missing/failed required command;
- dirty subject;
- subject changed after verification;
- plan mutation;
- log mutation;
- artifact mutation between verification and issuance;
- stored artifact-set tampering;
- mixed subject evidence.

Certificate verification checks immutable evidence first.
Optional replay is a separate operation and only happens in a checkout independently proven to equal the
certificate subject SHA.

Replace `scripts/build_certificate.py`; it must require explicit `--run-id`.

## P4 — WorkGraph v2

Install/merge the supplied WorkGraph replacement.

Required state:
`DRAFT → FROZEN → RUNNING → SUCCEEDED|FAILED`

Rules:
- node/edge mutation only DRAFT;
- tentative cyclic edge is rejected before commit;
- freeze computes deterministic structure hash;
- non-frozen graph cannot execute;
- every attempt has an attempt ID;
- exactly-one atomic claim;
- all state + semantic ledger event transitions use SAME transaction or a transactional outbox;
- retry/attempt ceiling defined once;
- terminal graph status/event is atomic.

Run every crash/race test unchanged.

## P5 — Typed subject certificates

Install:
- FixtureCertificateService
- ReleaseAuthorizationService

Factory activation requires exact:
factory ID + version + definition hash + fixture ID + artifact-set hash + acceptance plan.

Contractor activation has the same structure.

Product release requires ReleaseAuthorization bound to:
product + factory build run + artifact set + BuildCertificate + policy + ReviewCertificate where policy
requires it.

Remove generic `gate_results` from these authorization boundaries.

## P6 — Human / Product / Idea history

HumanQueue:
- strict transitions;
- actor identity;
- request payload hash;
- approval replay only for exact payload;
- atomic provenance.

Product:
- separate factory-created vs external-import constructors;
- factory product requires valid run lineage;
- outcomes typed FIXTURE/MANUAL/ESTIMATED/MEASURED;
- only measured evidence may be learning-eligible by default;
- atomic provenance.

Ideas:
- append-only cemetery episodes;
- idea decisions consume typed IdeaReviewEvidence;
- no naked `passed=True`;
- reviewer evidence bound to exact idea/stage/artifact.

## P7 — HotSwap durability

Install RouteRegistry + lossless persistence.

Prove:
- every routing-relevant Route field survives save/restart/load;
- repeated route ID yields one active candidate;
- first-use prior initialization never overwrites concurrent learning;
- concurrent updates lose zero observations;
- restart preserves routes/posteriors;
- quota semantics are explicitly durable or explicitly refreshed observations.

## P8 — Real factory fixture and V10

Replace simulated API fixture.

Success fixture:
- generate actual FastAPI artifact;
- boot real Uvicorn localhost;
- call `/health`;
- verify response;
- content-hash generated artifacts.

Failure fixture:
- generate broken variant;
- SAME verifier rejects.

Then implement the supplied V10 exemplar:
HotSwap → FactoryRun → frozen WorkGraph → builder Executor → real artifact → independent verifier Executor
→ VerificationPlan → BuildCertificate → FixtureCertificate → factory activation → Product →
ReleaseAuthorization → release → measured outcome → Product Passport.

No external internet required.

## P9 — Native review subsystem

Do NOT commit another nested ZIP/source pack as the implementation.

Install `src/qdw/review/` plus migrations 0005–0008 and compose it in QDWSystem.

Canonical review objects:
- ReviewRun / Round
- ModuleRun
- Finding / Evidence
- frozen AcceptanceSpec
- AttackResult
- Suppression
- ReviewCertificate
- PackExport

Review is WorkGraph-based. It has NO private scheduler.

## P10 — Reviewer contractors

Copy all reviewer manifests/prompts.

Every reviewer is a normal versioned global Contractor:
`review.architecture@2.0.0`, etc.

Before use:
- register manifest;
- run deterministic reviewer-contract fixture;
- BuildCertificate exact prompt+manifest artifacts;
- FixtureCertificate;
- activate contractor.

Required reviewer inactive → review BLOCKED, never silently skipped.

Do not execute `review.release-certifier` as a semantic reviewer worker. Actual certification is the
privileged independent aggregation service.

## P11 — Acceptance ownership

Blocking HIGH/CRITICAL findings MUST arrive with executable frozen acceptance specs.

Supported:
- existing command;
- complete inline pytest code;
- named attack;
- deterministic static-rule recheck.

ReviewStore freezes/hash-stores acceptance before the producer/fix worker sees the task.

If a blocking reviewer cannot produce acceptance:
`BLOCKER_WITHOUT_FROZEN_ACCEPTANCE`
and the review is BLOCKED.

Fixing worker cannot author/change the standard that closes its own finding.

## P12 — Autonomous convergence

Use `AutonomousReviewController`.

Each bounded round:
1. exact subject snapshot;
2. deterministic static rules;
3. change-aware semantic reviewer WorkGraph;
4. policy attack set;
5. claim-consistency;
6. blockers?
7. if none: independent certificate;
8. otherwise create normal `review_fix` WorkGraph;
9. workers repair using frozen acceptance;
10. they commit to a NEW SHA;
11. same acceptance re-executed;
12. review new SHA.

Stop honestly:
- REVIEW_CERTIFIED
- BLOCKED
- NO_PROGRESS
- BUDGET_EXHAUSTED
- MAX_ROUNDS
- FIXES_NOT_COMMITTED
- NO_NEW_SUBJECT_SHA

Never run an infinite self-fix loop.

## P13 — Reviewer self-review

Changes under:
`src/qdw/review/**`, reviewer manifests/prompts, proof, migrations or certifier
trigger self-review policy.

Reviewers may find findings, but:
- cannot close findings;
- cannot certify own work;
- cannot modify acceptance after freeze;
- cannot suppress their own blockers without an authorized suppression path.

Certifier worker must differ from producer and semantic reviewer workers for release certification.

## P14 — PackBuilder

Dogfood the same handoff format currently used externally.

`ReviewService.export_pack()` must produce an integrity-checked ZIP containing:
- interactive REPORT.html;
- REVIEW.json;
- SARIF;
- findings;
- evidence;
- frozen acceptance;
- fix plan;
- reviewer runs;
- attack results;
- verification runs/receipts/logs;
- certificates;
- SHA-256 MANIFEST.

`verify_pack()` must detect member mutation.

This is an export/read-model. Canonical truth remains DB + ledger.

## P15 — CLI / MCP / API

CLI:
- `qdw verify-plan`
- `qdw build-certificate`
- `qdw review-static`
- native review start/status/findings/pack commands.

MCP/API should expose thin adapters to `QDWSystem.review` and `review_controller`.
Do not construct another DB/router/review service.

Actual MCP contract uses official in-process Client to list/call tools.

## P16 — CI/runtime

Replace CI with one canonical frozen release VerificationPlan.

That plan executes:
compile, ruff, pyright, test guard, unit, contract, factories, adversarial, integration, runtime,
wheel build and deterministic review.

Do not run gates separately and infer proof later.

Prove:
- clean wheel;
- clean Docker build;
- Docker boot + `/health`;
- real MCP protocol;
- fresh/upgrade migration tests;
- all release attacks;
- no mandatory skips;
- BuildCertificate v2.

Remote CI/branch protection is V12 evidence and remains separate from local proof.
Do not claim it if unavailable.

## P17 — First real QDW self-review

After implementation:
1. bootstrap/certify reviewer contractors;
2. run full QDW self-review on exact clean SHA;
3. let autonomous controller create/fix blockers if any;
4. run same frozen acceptance after each fix;
5. require independent ReviewCertificate;
6. export the final QDW review ZIP through QDW's own PackBuilder.

If branch protection/remote evidence is unavailable, local status is not V12. Report the manual action.

## P18 — Cleanup

Once native review is PROVEN:
- archive/remove `qdw_review/qdw_self_review_system_2026-08-18/`
- remove committed old review ZIP from normal source tree
- keep immutable provenance/hash in docs/ledger, not duplicate executable source.

## Final output requirements

Return exact:
- final Git SHA and dirty=false;
- applied migration versions/hashes;
- failing-before and passing-after receipts for supplied regressions;
- test collection and zero mandatory skips;
- real API fixture result;
- V10 result;
- BuildCertificate v2;
- ReviewCertificate;
- review pack ZIP hash/integrity;
- remote CI/branch evidence if actually verified;
- unresolved BLOCKED/UNVERIFIED items.

Do not summarize a missing gate as success.

# QDW final autonomous-review exit gate

## Migration / state
- [ ] historical migration digests explicitly baselined
- [ ] no applied migration drift
- [ ] fresh and populated upgrade schema fingerprints match
- [ ] `PRAGMA foreign_key_check` empty
- [ ] migrations 0005/0006/0007/0008 applied as new immutable migrations

## Proof
- [ ] one canonical VerificationService
- [ ] release VerificationPlan frozen/hash before execution
- [ ] every mandatory command receipt belongs to same run/SHA
- [ ] artifact snapshot stored at run finish
- [ ] BuildCertificate v2 rejects plan/log/artifact/SHA mutation

## WorkGraph
- [ ] DRAFT→FROZEN→RUNNING lifecycle
- [ ] rejected cycle leaves no edge
- [ ] node/edge immutable after freeze
- [ ] exactly one claim in 32-way race
- [ ] attempts durable
- [ ] every state/event transition crash-atomic

## Trust boundaries
- [ ] factory activation consumes typed FixtureCertificate
- [ ] contractor activation consumes typed FixtureCertificate
- [ ] product release consumes ReleaseAuthorization
- [ ] stale human approval payload rejected
- [ ] idea decisions consume IdeaReviewEvidence

## HotSwap
- [ ] complete Route roundtrip
- [ ] duplicate route IDs dedupe
- [ ] routes survive restart
- [ ] concurrent posterior updates lose zero observations
- [ ] initializer cannot overwrite learned state

## Real execution
- [ ] API factory fixture performs actual HTTP
- [ ] broken API rejected by same verifier
- [ ] V10 crosses route→FactoryRun→WorkGraph→Executor→Artifact→BuildCert→Release

## Native self-review
- [ ] `src/qdw/review` exists and is composed
- [ ] reviewer contractors fixture-certified before activation
- [ ] blockers require frozen executable acceptance
- [ ] fix worker cannot close its own finding
- [ ] acceptance mutation detected
- [ ] attacks recorded from real command receipts
- [ ] certifier differs from producer/reviewer workers
- [ ] NO_PROGRESS/BUDGET/MAX_ROUNDS enforced
- [ ] ReviewCertificate exact subject/policy/reviewer/attack set
- [ ] PackBuilder interactive ZIP verifies all member hashes

## Runtime / CI
- [ ] actual MCP Client protocol test
- [ ] clean wheel build/install
- [ ] Docker build + run + `/health`
- [ ] canonical CI VerificationPlan passes
- [ ] BuildCertificate v2 self-verifies
- [ ] QDW full self-review certifies its own final SHA

## V12
- [ ] remote workflow run for exact final SHA confirmed
- [ ] main protected with required checks
- [ ] if unavailable, status remains explicit V12 BLOCKED/UNVERIFIED

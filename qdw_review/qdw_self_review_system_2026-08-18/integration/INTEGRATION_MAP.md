# Integrating self-review into QDW

## 1. Fix current trust defects first

Do not let the review subsystem certify the current broken release boundaries. Apply the current-review
remediations in `docs/01_CURRENT_QDW_PEER_REVIEW.md`.

## 2. Add migration as NEW 0003

Copy `integration/migrations/0003_review_system.sql` to `migrations/0003_review_system.sql`.

Also enhance the migration runner to lock hashes. Do not modify `0001` or `0002` again.

## 3. Install standalone scanner as an internal library

Either vendor `reference/src/qdw_review` as `src/qdw/review/scannerlib` or keep it as a small package dependency.
It must remain deterministic and not own canonical state.

## 4. Add canonical ReviewService

Use `integration/overlay/src/qdw/review/` as design reference.

Compose in QDWSystem:

```text
self.reviewer_registry
self.review
```

and inject existing:
DB, Ledger, WorkGraphStore, ContractorRegistry, proof/receipt subsystem.

## 5. Register reviewer contractors

Load `manifests/reviewers/*.json` using immutable contractor/reviewer version semantics.

## 6. WorkGraph execution

`review.full` expands into a WorkGraph. Reviewers can run in parallel. The certifier depends on all
mandatory reviewer nodes and red-team attacks.

## 7. Interfaces

Expose:
- `qdw_peer_review`
- `qdw_review_status`
- `qdw_review_findings`
- `qdw_red_team`

through existing MCP/API/CLI adapters. They delegate to `QDWSystem.review`.

## 8. Release policy

Release may require a `review_certificate_id` bound to:
- exact Git SHA;
- exact review policy hash;
- required reviewer definition hashes;
- required attack set;
- zero blockers.

Producer cannot issue this certificate.

## 9. Continuous use

Change-aware review runs after meaningful commits. Full review runs before product/factory release and
before activation of reviewer/contractor/factory versions.

Findings persist across runs by stable fingerprint:
OPEN → FIXED → REGRESSION is visible history.

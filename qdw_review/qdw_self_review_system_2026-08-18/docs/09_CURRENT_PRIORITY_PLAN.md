# Current Priority Plan for c1ab1e4

## Gate A — proof cannot lie
Fix CUR-001..004.

No release/factory activation should accept an unbound pass token.

## Gate B — immutable history
Fix CUR-005, CUR-009, CUR-010, CUR-022.

Contractor/migration/cemetery history must not be rewritten.

## Gate C — crash/concurrency/economics
Fix CUR-007, CUR-008, CUR-014, CUR-027, CUR-028.

Run the supplied adversarial tests unchanged before and after.

## Gate D — wire the actual system
Fix CUR-013, CUR-016, CUR-017.

Global infra should live behind QDWSystem and the real E2E must cross execution/certification.

## Gate E — clean runtime proof
Fix Docker/CI, actual MCP protocol, migration upgrade/fresh parity.

## Gate F — install self-review
Add migration 0003, reviewer registry/service, manifests, WorkGraph formula and Review Certificate.

Then run QDW's first self-review against its own implementation.

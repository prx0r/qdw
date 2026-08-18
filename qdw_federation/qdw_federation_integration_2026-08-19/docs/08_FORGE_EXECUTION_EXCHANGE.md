# QDW Forge as execution exchange

Forge is the cleanest execution boundary in the stack.

## QDW-facing contract

Discovery:
`list certified CapabilityAssets`

Lease:
`asset_id@version + calls + spend + TTL`

Invoke:
`lease token + capability + arguments + idempotency key`

Outcome:
`SUCCEEDED_UNVERIFIED | FAILED`

Verify:
`VerificationCertificateRef`

## Canonical QDW mode

A QDW lease is always pinned to the asset/version selected by QDW.

Forge's current invocation service already asks the local router with the lease's asset/version. Preserve this
and add a contract test that returned invocation asset/version equals the lease.

## Nested route provenance

Keep Forge `RouteDecision` because it is useful provenance, but in pinned mode it should show that policy was
constrained to the selected asset rather than imply Forge independently decided the global route.

## FactoryCapsule

This is especially useful for QDW:

A certified FactoryCapsule can be represented in QDW as an external factory capability, allowing:
- QDW factories to call reusable sub-factories;
- Moltwork-style factories-as-services later;
- benchmarked production recipes to become routable capabilities.

Do not import the Forge factory's internal WorkGraph into QDW unless the capsule explicitly exports a QDW
workflow template. Treat it like a service invocation by default.

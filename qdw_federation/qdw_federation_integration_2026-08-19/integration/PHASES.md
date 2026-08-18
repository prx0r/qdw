# Integration phases

## Phase 0 — evidence freeze
Clone exact pins, record dirty state, run original tests.

## Phase 1 — protocol foundation
Add QDW federation schema/contracts/store. No behavior changes to route selection yet.

## Phase 2 — oracle adapters
GitGoblin observation exporter + QDW ingest.
Dell candidate/advisory endpoint + QDW snapshot adapter.

## Phase 3 — execution exchange
Forge CertificateReference, pinned asset contract, QDW Forge execution adapter.

## Phase 4 — routing unification
Generalize QDW Route for fixed per-call costs. Collect Dell/Forge candidates. QDW HotSwap final selection only.

## Phase 5 — trust/proof
QDW verifies external invocation. Forge resolves the exact certificate. Add evidence-substitution attacks.

## Phase 6 — Sandbox graduation
Freeze donor behavior, port pure contracts/policies/context/human/data-rights features, disable duplicate authorities.

## Phase 7 — factory capsules
Treat Forge FactoryCapsule as routable sub-factory capability with QDW verification.

## Phase 8 — learning/cost
Keep Dell/Forge/QDW/Factory posteriors separate. Record external actual costs.

## Phase 9 — real protocols
Actual HTTP/API/MCP tests, not direct functions.

## Phase 10 — gold E2E
GitGoblin→QDW→Dell/Forge→HotSwap→Forge invoke→QDW verify→certificate/outcome.

## Phase 11 — federation CI
Pinned sibling repos, independent donor tests, cross-repo contracts, uploaded proof.

## Phase 12 — self-review
Run QDW's native federation reviewers and issue ReviewCertificate over exact multi-repo pins.

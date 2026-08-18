# QDW Federation Integration Pack

This pack reconciles five independently useful repositories into one **federated QDW system** without
creating a monorepo or competing canonical schedulers/databases.

Pinned review inputs:

```text
QDW         cccf6e3ca5f4704eb1c047965d3a3716dec8870b
Forge       2037cdb93458278bdc4807be8e84111cce72fb10
Sandbox     5e4278c8eeed008bcf11deff288b19110379ece0
GitGoblin   f7bf8963ee2600d9377a196ff0fd2f32ce5905b3
Dell        8aacd297fff0f0c7f48b36ac85ac415deaa7bd68
```

## Read first

1. `agent/MASTER_RECONCILIATION_PROMPT.md`
2. `docs/00_FEDERATED_ARCHITECTURE.md`
3. `docs/01_AUTHORITY_MATRIX.md`
4. `docs/02_REUSE_GRADUATE_RETIRE_MATRIX.md`
5. `integration/PHASES.md`
6. `acceptance/INTEGRATION_EXIT_GATE.json`

## Transport limitation during this review

The execution container could not resolve `github.com`, so native shell `git clone` could not be used.
The repositories were inspected at the exact pinned SHAs through the GitHub connector, including repository
trees and key source files. The reference federation code and tests in this pack were then executed locally.

The implementation agent should clone the real repositories normally and must verify that each checkout
matches `pins/REPOS.json` before making changes.

## Final ownership rule

```text
QDW
  owns decisions about WHAT work runs, WHEN, WHY, budget, canonical lifecycle,
  verification/review, products and outcomes.

GitGoblin
  owns technical/frontier collection and its source-specific attention graph.

Dell
  owns evidence/claims/offers about external models/providers/deals and produces ADVISORIES.

QDW Forge
  owns capability asset registry, leases, invocation transport and asset-local verified performance.

QDW Sandbox
  is an INCUBATOR. Useful components graduate into QDW/Forge/shared contracts;
  its Estate scheduler/router/verifier must not become a second production authority.
```

Everything else follows from this boundary.

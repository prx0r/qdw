# Test environments

## Environment A — independent semantic reference

Package: `reference_finishline/`

No source repo imports.

Purpose:
- prove intended state-machine/trust/cost semantics independently;
- prevent implementation details from defining their own acceptance criteria.

Current pack result: 61 tests passing.

## Environment B — exact-head native baselines

Five isolated virtual environments:

```text
.finishline-venvs/qdw
.finishline-venvs/qdw-forge
.finishline-venvs/qdw-sandbox
.finishline-venvs/gitgoblin
.finishline-venvs/dell
```

Purpose:
- catch dependency collisions;
- prove each donor repo independently before integration;
- keep native failures attributable.

## Environment C — independent source regression

Package: `lab/tests/source`.

It imports no source module. It inspects the cloned source tree using `QDW_WORKTREES`.

Purpose:
- catch false-green tests;
- ensure production fake Forge disappears;
- ensure required real endpoints/migrations exist;
- ensure duplicate authority does not reappear.

It is expected red on reviewed heads and mandatory green after integration.

## Environment D — deterministic black-box protocol lab

Real patched GitGoblin, Dell and QDW Forge applications, plus deterministic:
- Forgejo HTTP fixture with 61 repositories;
- HTTP capability fixture;
- isolated QDW/Forge databases.

Purpose:
- public protocol behavior;
- no network/API billing;
- reproducible auth, pagination, invocation and certificate tests.

## Environment E — sibling-service V11

Processes:

```text
QDW        :8910
Forge      :8911
GitGoblin  :8912
Dell       :8913
Echo       :8914
Forgejo    :8915
```

QDW and Forge run in isolated state directories. GitGoblin and Dell are the actual patched repo apps.

Tests use HTTP only.

## Environment F — process restart V11

QDW is killed after `SUCCEEDED_UNVERIFIED`, restarted against the same database, then `/resume` must reach
`COMMITTED` without another external invocation or duplicate cost/learning effect.

## Environment G — native QDW self-review

Run QDW's own review infrastructure last, using `review/FEDERATION_REVIEWERS.json`.

This does not replace independent tests. It provides architecture/security/change-aware review over the exact
post-integration SHAs.

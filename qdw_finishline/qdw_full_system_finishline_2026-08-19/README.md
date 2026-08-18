# QDW Full-System Finish-Line Pack — 2026-08-19

This pack is a **fresh peer review of the current repository heads**, not a replay of the previous federation design.

## Exact reviewed heads

```text
QDW          46920f2547e552b7f1c0e019169a350fe44cb4c1
QDW Forge    2037cdb93458278bdc4807be8e84111cce72fb10
QDW Sandbox  5e4278c8eeed008bcf11deff288b19110379ece0
GitGoblin    c129f801b601af8e088d6fe908f01f769a62b0ee
Dell         f29ed2a9621d307d301c628aa6f00de9d356d5ce
```

## The finish-line

```text
GitGoblin + Dell + Forgejo
          |
          v
    evidence/capabilities
          |
          v
         QDW
  canonical WorkGraph
  canonical final route
  canonical verification
          |
          v
       QDW Forge
  exact asset@version lease
  authorized invocation
          |
          v
 SUCCEEDED_UNVERIFIED
          |
          v
 QDW verifies + certifies
          |
          v
 Forge records local verified state
          |
          v
 QDW CostEvent + route learning
```

`qdw-sandbox` remains an incubator. Estate algorithms already absorbed into QDW may remain there as donor/reference,
but Sandbox must not regain production route/verification authority.

## What changed since the prior pack

The federation substrate has been copied into current QDW, but the real integration is not finished:

- QDW's composition root constructs an unconfigured federation service.
- QDW's current Forge "integration" test uses a local simulator rather than qdw-forge.
- QDW calls a GitGoblin endpoint that current GitGoblin does not expose.
- qdw-forge still has the old `passed: bool` verification boundary.
- QDW does not persist Forge fixed per-call route costs across restart.
- QDW migration 0010 contains duplicate Forge lease/certificate tables.
- no test currently proves the full sibling-service federation path.

This pack turns those into mandatory failing-before/fixed-after tests.

## Start here

1. `agent/MASTER_FINISH_PROMPT.md`
2. `peer_review/RECENT_PROGRESS.md`
3. `peer_review/FINDINGS.json`
4. `architecture/FINAL_RUNTIME.md`
5. `lab/README.md`
6. `acceptance/FINISH_LINE.json`

## Test philosophy

There are three layers:

```text
A. Independent reference lab       — executable inside this ZIP
B. Source/worktree regression lab  — scans/tests the cloned exact heads
C. Real sibling-service V10/V11    — public HTTP/ASGI boundaries only
```

A test named "Forge integration" is forbidden from importing a fake Forge client from QDW.

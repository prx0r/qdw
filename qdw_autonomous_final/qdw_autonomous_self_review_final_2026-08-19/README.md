# QDW Autonomous Self-Review — Final Integration Pack

Reviewed starting point: `prx0r/qdw@ab809c8e6b829374199eb49dc71cd6f499e4f7fb`

This is the final handoff for making peer review a **native QDW capability**, rather than a ZIP stored
inside the repository or an external ChatGPT loop.

The target autonomous lifecycle is:

```text
commit / factory change / release request / scheduled audit
                         |
                         v
                 SUBJECT SNAPSHOT
                  exact Git SHA
                         |
                         v
              DETERMINISTIC SCANNERS
                         |
                         v
             CHANGE-AWARE REVIEW PLAN
                         |
        +----------------+----------------+
        |                                 |
        v                                 v
 semantic reviewer contractors       dynamic attacks
 via normal QDW WorkGraph/HotSwap     process receipts
        |                                 |
        +----------------+----------------+
                         v
                   TYPED FINDINGS
                         |
              +----------+----------+
              |                     |
              v                     v
         no blockers            blockers exist
              |                     |
              v                     v
      independent certifier      FIX PLANNER
                                    |
                                    v
                              frozen fix graph
                                    |
                                    v
                             normal QDW workers
                                    |
                                    v
                         rerun SAME acceptance
                                    |
                                    v
                              new exact SHA
                                    |
                                    +-----> review again
```

The convergence loop stops only when:
- policy passes and an independent Review Certificate is issued;
- max rounds / budget / deadline is reached;
- a required human action blocks progress;
- required evidence cannot be produced.

## What is in this pack

- fresh peer review of the current head;
- native `src/qdw/review/` implementation overlay;
- canonical review database migration;
- canonical VerificationPlan/VerificationService design eliminating the two-runner split;
- strict Build Certificate v2;
- evidence-binding service for factory/contractor/product authorization;
- WorkGraph atomicity/freeze hardening design + regression tests;
- migration hardening;
- 26 reviewer contractor modules;
- 48 adversarial attack definitions;
- change-aware reviewer routing;
- autonomous fix/review convergence controller;
- interactive HTML + SARIF report generation;
- Review Certificate;
- **Review Pack Builder** which autonomously exports the same sort of self-contained ZIP this handoff provides;
- CI/release integration;
- CLI/API/MCP integration stubs;
- fully runnable standalone reference implementation and tests.

## First file for the implementation agent

`agent/MASTER_FINAL_IMPLEMENTATION_PROMPT.md`

Do not copy this entire pack under `qdw_review/` again. Integrate the native modules, then remove/archive the
old imported review pack from the repository once the new self-review is proven.

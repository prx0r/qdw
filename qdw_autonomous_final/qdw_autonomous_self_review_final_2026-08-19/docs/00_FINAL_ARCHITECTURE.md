# Final autonomous self-review architecture

Review is now a normal QDW control loop, not a special agent conversation.

```text
TRIGGER
 commit | PR | release | factory activation | contractor activation
 migration | scheduled audit | manual request
                         |
                         v
                  SubjectSnapshot
            git SHA + dirty + changed paths
                         |
                         v
                 ReviewService.start()
                         |
              +----------+----------+
              |                     |
              v                     v
       StaticRuleEngine       ChangeAwareRouter
              |                     |
              |              reviewer contractors
              |               through WorkGraph
              |                     |
              +----------+----------+
                         v
                    FindingStore
                         |
                    blocker gate
                  /               \
                 /                 \
              clean              blockers
                |                   |
                v                   v
       AttackRunner/policy       FixPlanner
                |                   |
                v                   v
       ClaimConsistency       Fix WorkGraph
                |                   |
                v                   v
       IndependentCertifier   normal QDW workers
                |                   |
                |              frozen acceptance
                |                   |
                |              exact new Git SHA
                |                   |
                +<------------------+
                         |
                         v
                 ReviewCertificate
                         |
                         v
                    PackBuilder
       JSON + HTML + SARIF + tasks + evidence + ZIP
```

## One truth owner

Canonical review lifecycle lives in QDW's normal SQLite DB.

Reviewers do not own status. Executors do not own status. Prompt output does not own status.
`ReviewService` transitions state based on persisted evidence and policy.

## Review does not invent another scheduler

Semantic reviewers and fix tasks are ordinary WorkGraph nodes.

HotSwap chooses the execution route. QDW executors run them. Review output is independently parsed and stored.

## Static before semantic

Anything detectable deterministically is checked locally first:
- proof-plan vacuity;
- dual verification systems;
- split state/ledger transactions;
- migration drift/unsafe patterns;
- missing review integration;
- fake factory fixtures;
- missing protocol tests;
- CI/runtime gaps;
- comments contradicting code.

Semantic reviewer calls are reserved for architecture, threat modeling, domain reasoning and cross-file critique.

## Review closure

A finding cannot close because an agent returns `"fixed": true`.

Closure requires:
1. the finding fingerprint;
2. the frozen acceptance specification hash;
3. a verification run on a later exact Git SHA;
4. all required commands/attacks PASS;
5. the deterministic rule no longer fires where applicable.

## Autonomous convergence

`ConvergenceController` runs bounded rounds:

```text
review SHA_n
→ blockers?
→ create fix graph
→ workers execute
→ verify frozen tests
→ snapshot SHA_n+1
→ review again
```

Stopping conditions:
- review certified;
- max rounds;
- cost budget;
- deadline;
- unresolved human action;
- no progress (same blocker fingerprint set);
- required executor/evidence unavailable.

The system records the stop reason instead of pretending completion.

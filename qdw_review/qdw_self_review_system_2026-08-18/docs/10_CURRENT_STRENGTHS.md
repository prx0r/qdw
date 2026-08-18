# What to preserve in current QDW

The peer review is intentionally aggressive, but the repo should not be rewritten.

Preserve:

- clean `src/qdw` package layout;
- canonical SQLite/WAL direction;
- hash-chained ledger + Merkle primitives;
- WorkGraph states, dependency edges, lease ownership and atomic claim update;
- typed source failure semantics;
- HotSwap Pareto/cost-quality policy;
- persistent posterior direction;
- global World/Pain/Stack/Idea/Human/Product modules;
- stable idea fingerprint concept;
- staged idea review ordering;
- HumanQueue state machine/idempotency concept;
- Product Passport / Factory Genome direction;
- anti-cheat TestGuard concept;
- process-backed VerificationRunner;
- separate deterministic vs semantic review thinking;
- Docker/CI intent;
- current commit discipline: fixes are landing as bounded commits.

The task is now to make **bindings, immutability, crash consistency and actual execution proof** as strong as
the architecture claims.

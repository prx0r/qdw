# Implementation order

Do not parallelize changes that alter the same trust boundary.

Recommended lanes:

```text
Lane A: GitGoblin endpoint ───────┐
Lane B: Dell cost/API ────────────┼─> QDW candidate layer
Lane C: Forge migrations/auth ────┤
Lane D: Forge identity/certs ─────┤
Lane E: Forgejo provenance ───────┘
                                      |
                                      v
                           QDW federation runtime
                                      |
                                      v
                          WorkGraph/proof/cost/learn
                                      |
                                      v
                              V11 + restart
```

Forge order is strict:

```text
migrations
→ identity split
→ client auth
→ lease authorization
→ idempotency
→ cost settlement
→ certificate resolver/replay
→ Forgejo provenance
→ API
```

Do not implement the QDW external execution state machine against the old unsafe Forge API.

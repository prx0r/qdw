# Failure semantics

Cross-service ambiguity is dangerous.

Use:

```text
OK
OK_EMPTY
DEGRADED
STALE
UNAVAILABLE
INCOMPATIBLE_PROTOCOL
UNAUTHORIZED
BUDGET_BLOCKED
POLICY_BLOCKED
FAILED
```

Never collapse:
- timeout -> []
- HTTP 500 -> no candidates
- stale Dell snapshot -> fresh price
- Forge lease failure -> zero assets
- GitGoblin collector failure -> zero frontier activity

QDW decides whether degraded/stale inputs are usable under the specific WorkNode policy.

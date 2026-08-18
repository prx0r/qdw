# AGENTS.md — QDW

*How agents work here. Read this first.*

---

## THE ONE RULE

> **Nothing is DONE because code exists or because you say a test passed.**
> It is PROVEN only when a recorded verification run shows every required gate passed.

---

## DEFINITIONS

- **PROVEN**: verification run recorded, all gates passed, artifacts hashed
- **IMPLEMENTED_UNVERIFIED**: code exists but no verification run proves it
- **UNVERIFIED**: command could not run
- **BLOCKED**: prerequisite not met
- **FAIL**: recorded command returned non-zero or artifact check failed

There is no state called: `probably_passes`, `looks_good`, `should_work`, `done`.

---

## ANTI-CHEAT RULES

### Forbidden test patterns

- `assert True`
- Tests containing no meaningful assertion
- Swallowing an exception and calling the test successful
- Mocking the function under test to return the expected result
- Replacing production logic with a fake inside the test
- Deleting a failing test to make CI green
- Weakening an assertion without documenting a changed requirement
- Marking a failing test `xfail`/`skip` to complete a task
- Network-dependent unit tests (use `respx` mocks)
- Asserting only that an object/file exists when behavior is the requirement
- Replacing a real certificate with fixture text saying "valid"

### Changing a frozen acceptance test

Requires its own logged event:

```
TEST_SPEC_CHANGED
reason: <reason>
old_hash: <sha256>
new_hash: <sha256>
```

### Source failure invariant

```
SOURCE FAILURE != ZERO RESULTS
```

A failed source returns `SearchResult(ok=False, ...)` or raises `SourceUnavailable`.
An empty result set returns `SearchResult(ok=True, items=[])`.
These must never be conlated.

### Economic inputs

```
BROKEN DATABASE != ZERO OPPORTUNITIES
UNKNOWN SHIPPING COST != ZERO COST
```

Expose degraded health or typed errors. Never silently substitute zeros.

---

## VERIFICATION LADDER

| Gate | What it proves |
|---|---|
| V0 Compile | Every tracked Python module parses |
| V1 Static | Formatting/lint/type/import boundaries |
| V2 Unit | Local deterministic behavior |
| V3 Property | Invariants across many generated cases |
| V4 Integration | Modules work together |
| V5 Contract | API/MCP/manifests conform |
| V6 Concurrency | leases/idempotency/claims survive races |
| V7 Adversarial | mutation/failure/corruption is detected |
| V8 Factory fixture | actual factory produces expected artifact |
| V9 Docker | clean environment boots |
| V10 E2E | opportunity → factory → graph → work → verify |
| V11 Live | optional real Hermes/API/provider tests |
| V12 CI | clean remote environment independently reruns gates |

The agent must say **exactly which level is proven**.

---

## PROCESS MANAGEMENT

### Background jobs

```bash
setsid nohup python3 script.py > output.log 2>&1 &
echo "PID $!"
# ...do real work...
tail /tmp/output.log   # check on it later
```

### Kill by PID (never pkill)

```bash
ps -eo pid,etime,cmd | grep python | grep task
kill <PID>
```

### RAM budget

```bash
free -h | head -2 && uptime
```

- SAFE (avail >= 1GiB): OK to start
- CAUTION (avail < 1GiB): light work only
- CRITICAL (avail < 400MiB): STOP heavy work

---

## FILE CONVENTIONS

| Thing | Location |
|---|---|
| Acceptance spec | `spec/acceptance/<task_id>.yaml` |
| Verification run | `.qdw/runs/<run_id>/` |
| Migrations | `migrations/<NNNN>_<name>.sql` |
| Schemas | `schemas/` |
| Factory manifests | `manifests/factories/` |
| Team manifests | `manifests/teams/` |

---

## DEFINITION OF DONE

The agent is not allowed to close a task unless the OS can produce:

```json
{
  "task_id": "...",
  "implementation_commit": "...",
  "acceptance_spec_hash": "sha256:...",
  "verification_run": "...",
  "commands_executed": N,
  "commands_failed": 0,
  "tests": {
    "collected": N,
    "passed": N,
    "failed": 0,
    "skipped": 0
  },
  "negative_tests": { "...": true },
  "artifacts": [{ "sha256": "...", "type": "..." }],
  "status": "PROVEN"
}
```

Anything less is `IMPLEMENTED_UNVERIFIED`, not `DONE`.

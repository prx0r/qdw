# Verification and Anti-Cheat

## Rule

An agent never gets to assert `PASS`.

The verification runner executes a real process and computes:

```text
exit_code == 0 → PASS
otherwise      → FAIL
timeout        → FAIL (124)
```

It records:

- task ID
- exact argv
- cwd
- UTC start/end
- duration
- exit code
- stdout/stderr files
- stdout/stderr SHA-256
- git SHA
- dirty state

## Build certificates

A BuildCertificate requires all frozen commands to have matching successful receipts.
Missing receipts, failed receipts or missing artifacts refuse certification.

## Test guard

The reference flags:

- `assert True`
- runtime `pytest.skip/xfail`
- skip/xfail decorators
- empty test functions
- syntax-invalid test files

This is not a replacement for code review. It is a tripwire against obvious fake-green behavior.

## Required negative tests

Every important subsystem must prove rejection, not just success:

- source failure != empty
- unknown resource cost fails a hard max-cost requirement
- invalid HumanQueue transition rejected
- contractor manifest mutation without version bump rejected
- idea stage skipping rejected
- unauthorised domain registration state transition rejected
- failed command cannot appear in BuildCertificate
- test guard detects fake tests
- old Factory OS ledger mutation tests still pass
- WorkGraph exactly-one-claim tests still pass

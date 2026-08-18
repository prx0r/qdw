# Proof model v2

The current QDW has two VerificationRunner implementations. Final QDW must have one canonical
`VerificationService`.

## Frozen plan

A release/build/review starts from a `VerificationPlan`:

```json
{
  "plan_id": "qdw-release",
  "version": "1.0.0",
  "commands": [
    {"id":"compile","argv":["python","-m","compileall","-q","src/qdw","tests"]},
    {"id":"unit","argv":["pytest","tests/unit","-q"]},
    {"id":"adversarial","argv":["pytest","tests/adversarial","-q"]}
  ],
  "attacks": ["A01","A02"],
  "artifacts": ["dist/*.whl"],
  "max_mandatory_skips": 0
}
```

The plan is content-hashed before execution.

Required commands are never inferred from whatever receipts happen to exist.

## Receipts

Every command receipt binds:
- verification run ID;
- plan hash;
- command ID;
- argv;
- cwd;
- environment fingerprint;
- exact Git SHA;
- dirty state;
- start/end;
- exit code;
- stdout/stderr digests.

All mandatory receipts in a certificate must belong to the same exact subject SHA and run.

## Adversarial tests

A negative behavior test is not "process must fail".

For pytest:

```text
pytest command exits 0
AND
AttackResult.status == REJECTED_AS_EXPECTED
AND
reason_code matches policy
```

A test-runner crash is not a successful attack.

## Evidence verification vs replay

Certificate verification first checks immutable evidence:
- plan file/hash;
- receipt envelope and log hashes;
- exact Git subject;
- artifact hashes;
- attack results;
- ledger root.

Optional replay is a separate operation and only runs inside a checkout verified to equal the certificate SHA.

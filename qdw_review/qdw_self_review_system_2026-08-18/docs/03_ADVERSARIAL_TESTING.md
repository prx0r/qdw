# Adversarial Testing

Red Team must test rejection paths, not only successful execution.

The canonical attack catalog is `attacks/ATTACK_CATALOG.json`.

## Attack classes

### Evidence substitution
Use valid evidence for the wrong subject/version/run/artifact.

This catches weak checks of the form:

```text
ID exists
AND passed == true
therefore authorized
```

Correct checks bind:

```text
evidence subject
+ version
+ run
+ fixture
+ artifact digests
+ acceptance policy
```

### Crash consistency
Inject failure between state transition and provenance. Any window that leaves impossible state is a defect.

### Concurrency
Synchronize workers so races happen on demand rather than hoping they occur.

Examples:
- exactly-one WorkGraph claim;
- posterior lost-update race;
- idempotent human action creation;
- terminal state race.

### Mutation
Change already-certified things:
- artifact bytes;
- acceptance spec;
- migration bytes;
- contractor manifest same version;
- ledger payload;
- certificate envelope.

### Fake-green
Try to certify from:
- no required commands;
- only trivial receipt;
- direct Python function instead of protocol;
- fixture values inserted directly into verifier;
- source failure represented by [];
- fake outcome telemetry.

## Rule for "negative tests"

For in-process pytest tests, the **pytest command itself should normally exit 0** while asserting that bad
input was rejected. Do not model all negative tests as "the process must exit nonzero"; that can accidentally
reward a crashed test runner. The Review Certificate stores the attack result separately from command success.

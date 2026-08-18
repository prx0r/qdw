# review.verification

Audit frozen plans, receipts, exact Git subjects, artifact evidence, attack semantics and certificate verification.

## Required review behavior

Inspect the exact Git subject and changed surface, but follow transitive invariants into other modules.
Actively search for counterexamples, subject/version mismatches, crash windows, stale state, false-green tests,
and documentation claims that outrun mechanics.

For HIGH/CRITICAL findings, provide an executable frozen acceptance specification whenever possible.
The fixing worker must not have to invent the test that will judge its own fix.


## Output contract

Return a typed `review_result`, not prose-only PASS/FAIL. Every finding must include:
`rule_id`, severity, invariant, evidence, remediation, and acceptance.

Where a deterministic executable acceptance can be written, include `acceptance_specs`. Prefer:
- `inline_pytest` with complete frozen test code;
- a concrete existing command;
- a named attack;
- a deterministic static-rule recheck.

Do not mark a finding fixed. The independent acceptance/review loop owns closure.
A code comment, commit message, previous test count, or agent statement is a claim—not evidence.


## Mandatory verification attacks
- prove there is one canonical PASS computation path;
- trace every release command from frozen VerificationPlan → run → receipt → BuildCertificate;
- reject post-hoc requirements derived from observed receipts;
- distinguish pytest negative-behavior PASS from process failure;
- mutate plan, stdout/stderr log, artifact and certificate;
- test exact SHA/dirty/cwd/environment bindings;
- separate immutable evidence verification from optional replay.

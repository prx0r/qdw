# review.redteam

Execute policy-selected evidence substitution, crash, mutation, concurrency and fake-green attacks.

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


## Mandatory campaigns
Treat the attack catalog as executable policy, not inspiration. Prioritize evidence substitution,
crash consistency, synchronized races, migration mutation, artifact mutation, fake factory fixtures,
protocol-vs-function tests, and reviewer self-certification. A crashed attack runner is FAIL, not a
successful rejection. Never invent actual reason codes; frozen tests must assert them.

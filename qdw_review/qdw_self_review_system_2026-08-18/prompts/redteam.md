# QDW Red Team

Your job is to make QDW reject bad states. Do not merely inspect happy paths.

Execute or generate adversarial tests across these campaigns:

## A. Evidence substitution
1. Create a valid gate for an unrelated run; attempt factory activation.
2. Create a valid certificate for product/run A; attempt release of product B.
3. Use certificate for factory v1 to activate v2.
4. Use an old HumanAction approval for a changed domain/price payload.

## B. Crash consistency
5. Inject failure after DB mutation but before semantic ledger append.
6. Inject failure while appending ledger event.
7. Kill/restart between LEASED/RUNNING/VERIFYING transitions.
Expected: state+provenance remain reconcilable.

## C. Graph/race
8. 32 workers race for one READY node: exactly one winner.
9. Create dependency cycle: no graph may enter executable state.
10. Expire lease at retry ceiling.
11. Duplicate idempotency key under concurrent insertion.
12. Two workers complete/fail same node concurrently.

## D. Economics
13. Unknown cost vs known cost: unknown must not silently become zero.
14. Unknown expected value must not become optimistic constant.
15. Concurrent bandit updates: no lost observations.
16. Restart: routes, posteriors and economically relevant quota state retain intended semantics.
17. Failure/timeout updates route reliability without poisoning unrelated task cells.

## E. Proof
18. Run only trivial command then try release certificate.
19. Delete one mandatory receipt.
20. Mutate certified artifact.
21. Modify frozen acceptance spec.
22. Recompute local certificate envelope hash after tampering.
23. Modify an already-applied migration.
24. Tamper ledger payload/event chain/Merkle proof.

## F. Product/factory
25. Activate contractor without fixture.
26. Change contractor manifest without version bump.
27. Fake API fixture by feeding verifier `ok=True` without booting HTTP.
28. Create product with missing factory lineage under factory-created mode.
29. Record fixture outcome and try to update production portfolio learning.

## G. Interfaces/runtime
30. Broken database must not become empty results.
31. Actual MCP client must discover/invoke tools.
32. Container must build from clean context, boot and pass /health.
33. Missing environment/config must fail explicitly.
34. Dependency/provider/source outage must remain typed failure.

A red-team PASS means required attacks executed and were rejected for the right reason.


## Evidence rules

You are a reviewer, not the producer.

Never return PASS from intuition. Every finding must contain:
- invariant;
- exact affected path/object;
- evidence;
- severity and confidence;
- reproduction or counterexample when possible;
- remediation;
- executable acceptance test.

A source comment/docstring/commit message is a claim, not evidence.

If you execute a command, attach its process receipt. If you did not execute it, label it UNVERIFIED.

Never weaken a frozen acceptance test to make the reviewed build green.

For trust boundaries, an ID existing is insufficient. Verify that the evidence is bound to the exact:
subject → version → run → artifact → policy/acceptance specification.

Output a single structured ReviewResult.

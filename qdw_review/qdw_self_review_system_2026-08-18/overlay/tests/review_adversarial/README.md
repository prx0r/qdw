# Adversarial regression overlay

These tests encode desired invariants discovered during peer review of `c1ab1e4`.

They are expected to expose current defects. Do not weaken/delete them to get green.

Integration workflow:

1. freeze each test's acceptance spec/hash;
2. copy into QDW's mandatory adversarial suite;
3. run and retain failing receipts at current head;
4. fix production code;
5. rerun exactly the same test bytes;
6. retain passing receipts;
7. only then close the finding.

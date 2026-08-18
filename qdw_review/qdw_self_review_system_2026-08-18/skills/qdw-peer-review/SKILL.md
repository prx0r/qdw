# QDW Peer Review Skill

Use when asked to review QDW, a QDW-produced project, a factory, or a major architectural change.

## Procedure

1. Resolve exact subject Git SHA and dirty state.
2. Freeze review policy hash.
3. Run deterministic scanner:
   `qdw-review scan . --profile quick --out .qdw/review/<sha>/`
4. Select change-aware reviewer contractors from `review.change-aware`.
5. Run required semantic reviewers as bounded WorkGraph nodes.
6. Persist typed findings/evidence.
7. Generate acceptance tests before fixing blocking findings.
8. For release/full review, run `review.redteam`.
9. Run claim-consistency reviewer after technical reviewers.
10. Independent certifier aggregates evidence.

## Never

- accept a caller `passed=True` as review evidence;
- call a build green because an LLM reviewer says so;
- remove/skip a failing frozen acceptance test;
- certify a dirty or different Git SHA;
- treat a valid-but-unrelated certificate/gate as authorization.

## Outputs

- ReviewReport JSON
- interactive HTML
- SARIF
- FixPlan
- ReviewCertificate or REVIEW_REJECTED

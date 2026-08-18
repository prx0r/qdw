# Reviewer Contractors

Reviewers use the same global contractor substrate as QA/Red Team/Publish rather than a new agent framework.

## Identity

```text
review.architecture@1.0.0
review.trust-boundary@1.0.0
review.redteam@1.0.0
...
```

A reviewer manifest is immutable. Changing its scope/gates requires a version bump.

## Output contract

Each semantic reviewer returns:

```json
{
  "reviewer_id": "review.factory",
  "version": "1.0.0",
  "status": "PASS|FAIL|UNVERIFIED|BLOCKED",
  "findings": [
    {
      "rule_id": "...",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "confidence": 0.0,
      "invariant": "...",
      "evidence": [],
      "remediation": "...",
      "acceptance_tests": []
    }
  ]
}
```

PASS is not a release authorization. The independent certifier checks the whole reviewer/evidence set.

## Change-aware routing

Do not run every expensive reviewer after every edit.

Examples:

```text
migrations/**        -> database + proof + redteam
core/graph/**        -> workgraph + database + redteam
hotswap/**           -> hotswap + redteam
factories/**         -> factory + trust + redteam
products/**          -> products + trust + redteam
interfaces/**        -> interfaces + security + redteam
docs/claims changes  -> claim-consistency
```

Architecture + claim consistency should run broadly because cross-module contradictions often arise from
otherwise local changes.

## Meta-review

`review.claim-consistency` exists to detect a particularly common agent failure mode:

> a commit message/docstring says the invariant was fixed, but the code only changed names/comments or
> introduced a superficially similar mechanism.

It treats claims like `atomic`, `transactional`, `persistent`, `E2E`, `single composition root` and `PROVEN`
as hypotheses to verify.

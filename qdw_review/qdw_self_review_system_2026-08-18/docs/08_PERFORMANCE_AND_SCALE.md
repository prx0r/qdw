# Scale / Performance Review

Self-review must not become a giant LLM tax.

Use three tiers:

## Quick
Pure deterministic local scans. Seconds-scale. Run frequently.

## Change-aware
Only reviewers implicated by changed paths + architecture/meta reviewer.

## Full release
All required reviewers + dynamic attacks + clean runtime gates.

Cache by:

```text
git blob hash + reviewer version + policy hash
```

A deterministic static finding for an unchanged blob does not need to be recomputed by an LLM.

Store semantic reviewer reports as content-addressed artifacts so reviewers can focus on diffs/regressions.

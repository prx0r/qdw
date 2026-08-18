# Self-review design principles

## 1. Evidence beats status
Never ask "is this passed?" before asking "what immutable evidence authorizes this exact transition?"

## 2. Bind exact subjects
Valid evidence for the wrong subject is invalid.

## 3. Reviewers are versioned production components
A red-team prompt changing is a behavior change. Version it.

## 4. Negative tests are first-class
A quality system is defined by what it refuses.

## 5. Separate discovery from certification
Reviewers discover findings. An independent certifier evaluates the policy.

## 6. Deterministic before LLM
If an invariant can be checked by code, do not spend model inference asking an agent.

## 7. Diff-aware but history-aware
Review the changed surface while retaining stable finding fingerprints across time.

## 8. Meta-review claims
Agentic coding systems often fix terminology faster than mechanics. Mechanically challenge strong claims.

## 9. Dogfood
QDW's own release should be the first serious customer of QDW Review.

## 10. Reviewer self-review
Changes to the reviewer/certifier/trust-boundary code trigger the strictest red-team policy.

# Calling the reviewers from an agent

## Fast local deterministic scan

```bash
qdw-review scan . --profile quick --out .qdw/review
```

## Ask QDW itself after integration

Conceptual MCP calls:

```text
qdw_peer_review(profile="quick")
qdw_review_status(review_run_id="review_...")
qdw_review_findings(review_run_id="review_...", min_severity="HIGH")
qdw_red_team(review_run_id="review_...")
```

## Hermes / contractor work node

The WorkNode payload references immutable definitions:

```json
{
  "kind": "contractor",
  "contractor_id": "review.trust-boundary",
  "contractor_version": "1.0.0",
  "subject_git_sha": "<sha>",
  "review_run_id": "<review>",
  "policy_hash": "<hash>",
  "changed_paths": ["src/qdw/factories/registry.py"]
}
```

The executor loads the registered reviewer prompt, produces a typed ReviewerOutput artifact, and
ReviewService stores findings. The worker cannot set the review run to CERTIFIED.

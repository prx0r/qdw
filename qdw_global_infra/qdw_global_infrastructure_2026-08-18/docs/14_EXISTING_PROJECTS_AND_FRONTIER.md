# Existing Projects / Frontier Notes

## Pain / feedback
- OpenCoven Feedback: strong OSS example of duplicate-aware feedback extraction and agent/MCP access.
- HN official API: reliable public Ask HN event source.

## Startup intelligence
- `yc-oss/api`: convenient structured derived YC feed.
- `yc-oss/open-source-companies`: useful GitHub linkage.
- ExploreYC / ycagent.ai: useful examples of semantic company comparison and evidence-backed research.
- DIALECTIC (arXiv 2603.12274): fact gathering → arguments for/against → critique/debate → score.

## Ideation
- "Using Large Language Models for Idea Generation in Innovation" (arXiv 2607.27553):
  useful evidence that LLM generation can produce high-rated ideas while also collapsing diversity.
  QDW therefore preserves diversity and historical/cemetery state instead of repeatedly sampling generic ideas.

## Catalog / templates
- Backstage catalog + Software Templates are the best mature reference for a plugin-driven entity catalog,
  standardized creation paths and docs. Borrow their manifest ergonomics; don't install a giant portal as the core.

## Lineage / provenance
- OpenLineage: extensible run/job/dataset event model.
- Marquez: optional graph visualization.
- in-toto: authenticated attestation shape.
- Rekor: optional transparency log.

## Human-in-loop
- Temporal Agent Harness: tool policy + durable approval.
- Weft: stored review requests / decision APIs.
- BlueKiwi: explicit workflow gates.
These validate the HumanQueue abstraction, but QDW does not need Temporal just to represent an approval.

## Stack/capability
- APIs.guru OpenAPI Directory
- MCP Registry
- LiteLLM
- sqlite-vec
- Zalando Tech Radar

## Outcome / publishing
- PostHog or Plausible for product telemetry.
- MkDocs Material for generated docs.
- Cloudflare Workers/Registrar for deploy/domain adapters.

# Reuse Matrix — What to steal, what not to import wholesale

The goal is mechanism reuse, not dependency collection.

| Project | What QDW should reuse | Integration decision |
|---|---|---|
| Backstage | entity catalog, relationships, software templates, paved/golden paths, docs/catalog thinking | **Pattern only initially.** QDW remains canonical. Optional future UI export. |
| Backstage software-templates | declarative template inputs/actions and dry-run testing | Use as inspiration for Factory/Contractor manifests. |
| OpenLineage | `Run`/`Job`/input/output lineage event semantics and extensible facets | Add optional OpenLineage exporter after QDW event model stabilizes. |
| Marquez | lineage graph/read-model ideas | Optional external visualization, never canonical DB. |
| in-toto Attestation | subject digest + authenticated predicate model | Map QDW certificates into in-toto-compatible attestations. |
| Sigstore Rekor | transparency-log inclusion/verification | Optional external anchor for release certificates. |
| Temporal Agent Harness / Weft / BlueKiwi | durable approvals, explicit human gates, resume after decision | Implement lightweight SQLite HumanQueue now; upgrade only if measured need appears. |
| OpenCoven Feedback | feedback ingestion, duplicate detection, AI summaries, MCP-accessible feedback | Strong pattern/source for Painfinder. |
| HackerNews official API | near-real-time Ask HN/problem observations | Direct source adapter. |
| yc-oss/api | structured public YC company dataset refreshed by Actions | Startup Radar seed source. |
| yc-oss/open-source-companies | YC + OSS repository linkage | Useful Startup Radar cross-signal. |
| ExploreYC / ycagent.ai | semantic company search, evidence-backed research dossiers | Product/research pattern; do not depend on implementation. |
| APIs.guru OpenAPI Directory | public machine-readable API catalog, provenance/update metadata | Direct AlternativeAPI/StackOracle source. |
| Official MCP Registry | machine-readable agent-server discovery, incremental updates | Direct StackOracle/AlternativeAPI source. |
| LiteLLM | provider normalization, spend tracking, gateway/router adapter surface | Bridge to HotSwap; do not replace HotSwap policy. |
| sqlite-vec | embedded semantic similarity inside SQLite | Optional dedupe/search accelerator after deterministic fingerprints; keep optional because pre-v1. |
| DuckDB | cheap embedded analytical queries over exported Parquet/JSON | Later analytics read-model; not transaction DB. |
| DVC | immutable experiment inputs/outputs/metrics and reproducibility mindset | Pattern for portfolio experiments/replay. |
| PostHog | event analytics, experiments, surveys, error/AI observability | Preferred rich Outcome adapter if a product uses it. |
| Plausible | lightweight privacy-focused web analytics | Simple website outcome adapter. |
| MkDocs Material | deterministic attractive docs from Markdown | Default docs contractor target. |
| Zalando Tech Radar | simple technology radar visualization | Future StackOracle public/internal view. |
| Cloudflare Workers SDK | repeatable serverless deploy CLI | Publish adapter option. |
| Cloudflare Registrar API | domain search/check/registration API | Search/check automated; registration remains HumanQueue-gated. |

## Why Backstage is not the QDW runtime

Backstage itself says the catalog is best treated as a high-level hub/read model and not necessarily
the ultimate dynamic source of truth. QDW needs finer-grained observations, claims, run events, costs,
certificates, idea lineage and outcome windows. Therefore QDW can export to a Backstage-like portal
without inheriting Backstage as its database or scheduler.

## Why no graph database yet

The relationships are graph-shaped, but SQLite is enough for current scale and makes transactions,
foreign keys, hashes and tests easy. Add `sqlite-vec` for optional semantic retrieval; add a graph/OLAP
read model only when query patterns prove it useful.

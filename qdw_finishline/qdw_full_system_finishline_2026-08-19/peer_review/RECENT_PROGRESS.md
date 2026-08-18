# Recent progress peer review

## QDW

The progress is substantial. QDW has absorbed:

- global world/intelligence/idea/product infrastructure;
- strict migration digests;
- persistent HotSwap;
- canonical verification and build/review certificates;
- self-review;
- GitGoblin/Dell adapters;
- LiteLLM model pricing;
- Estate routing algorithms;
- federation contracts and external snapshot/ref tables.

The remaining problem is **composition and proof**, not a lack of modules.

The latest 207-test state should not be interpreted as "the federation works." The current test suite still contains
a simulated Forge path, direct dictionary adapter tests, a known Dell-cost loss accepted by a passing test, and an
empty `tests/e2e` directory.

## QDW Forge

Forge's design is valuable and should remain separate:

- capability assets / FactoryCapsules;
- leases with token hashes;
- invocation records;
- local performance profiles;
- Forgejo discovery;
- Repo2Bench historical task generation;
- frontier watcher;
- Vana hooks;
- REST/MCP.

It has barely advanced since QDW absorbed the federation pack, so the two sides have drifted. The next work belongs
primarily here: trust-boundary repair, immutable asset activation, lease/idempotency authorization, spend settlement,
strict migrations, Forgejo provenance and full public contract tests.

## GitGoblin

GitGoblin has advanced quickly:

- source cursors and health;
- CAS/provenance/replay;
- source-specific rate limiting;
- mechanism extraction;
- agent-context mining;
- invariant/mutation tests;
- people-based frontier watchlist.

The architectural role is now even clearer: GitGoblin is the repository/frontier **sensor/oracle**, not another
opportunity allocator.

The missing piece is mundane but blocking: implement the current QDW federation wire endpoint and freeze the schema.

## Dell

Dell's data breadth has expanded significantly, including LiteLLM, free-API and MCP registry ingestion.

Two integration problems remain:
- QDW needs a stable federation candidate endpoint with complete candidate facts.
- Dell's cost function still treats unknown output-token price as zero when output tokens are nonzero.

## Sandbox / Estate

QDW has already absorbed the useful Estate routing algorithms. Keep Sandbox as the experimental source for LifeGit,
human/data-rights and new routing/context ideas. Do not connect its scheduler or verifier back into the production
QDW lifecycle.

# Peer-review verdict

**The pieces are good enough. Stop adding parallel infrastructure. Finish the real wires and prove them.**

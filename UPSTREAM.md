# UPSTREAM — Donor Audit

## Donor

- **Repository:** `prx0r/cuntgoblin` (venturelab)
- **Green donor SHA:** `705d0c4d8fbb0b9e7b1e6138b25e3584e5b39e52`
- **Tag:** `venturelab-legacy-final`
- **Audit date:** 2026-08-18

## Classification

### Verbatim transplant (altered only imports to `qdw.*`)

| Module | SHA-256 | Status |
|---|---|---|
| `factory/hotswap/bandit.py` | `ab93c8e2...` | VERBATIM |
| `factory/hotswap/failure.py` | `3df9e05c...` | VERBATIM |
| `factory/hotswap/policy.py` | `703fd4f6...` | VERBATIM |
| `factory/hotswap/quota.py` | `0f96042f...` | VERBATIM |
| `factory/hotswap/router.py` | `2ff496a1...` | VERBATIM |
| `factory/hotswap/stats.py` | `e7d737a9...` | VERBATIM |
| `factory/hotswap/test_hotswap.py` | `6bd6c656...` | VERBATIM |
| `factory/hotswap/types.py` | `04e8864a...` | VERBATIM |
| `factory/hotswap/accounts.py` | `a9fd7a4d...` | VERBATIM |
| `factory/market/market_algorithms.py` | `9c259925...` | VERBATIM |
| `factory/market/test_market_algorithms.py` | `c2a0405c...` | VERBATIM |
| `factory/scoring/engine.py` | `4384db8f...` | VERBATIM |
| `factory/sources/__init__.py` | `3ed8862b...` | VERBATIM |
| `factory/sources/github.py` | `016d98c0...` | VERBATIM |
| `factory/sources/arxiv.py` | `632c4721...` | VERBATIM |
| `factory/global_os/merkle.py` | `a8edd431...` | VERBATIM |
| `factory/global_os/graph.py` | `7187bd22...` | VERBATIM |
| `factory/global_os/queue.py` | `3fb1c4f7...` | VERBATIM |
| `factory/global_os/release.py` | `9784a14d...` | VERBATIM |
| `factory/global_os/scheduler.py` | `e18f312c...` | VERBATIM |
| `factory/global_os/state.py` | `97e5cc45...` | VERBATIM |
| `factory/global_os/identity.py` | `b680d774...` | VERBATIM |
| `factory/agenthub/kanban.py` | `24243225...` | VERBATIM |
| `factory/agenthub/resolver.py` | `8b8f3c33...` | VERBATIM |
| `factory/agenthub/types.py` | `c130b771...` | VERBATIM |
| `factory/agenthub/failures.py` | `1b4ae0f6...` | VERBATIM |
| `factory/agenthub/identity.py` | `756ce8da...` | VERBATIM |
| `factory/agenthub/lineage.py` | `14da5aae...` | VERBATIM |
| `factory/agenthub/metrics.py` | `5d591d15...` | VERBATIM |
| `factory/agenthub/promotion.py` | `5a0f720b...` | VERBATIM |
| `factory/agenthub/search.py` | `957b0ef2...` | VERBATIM |
| `factory/agenthub/simulator.py` | `742390ca...` | VERBATIM |
| `factory/agenthub/a2a.py` | `3743ca72...` | VERBATIM |
| `factory/agenthub/hermes.py` | `76ebd995...` | VERBATIM |
| `factory/domain/idea.py` | `90a0dd51...` | VERBATIM |
| `factory/domain/product.py` | `18ab9146...` | VERBATIM |
| `factory/domain/research.py` | `362f021c...` | VERBATIM |
| `factory/domain/score.py` | `1f048de4...` | VERBATIM |
| `factory/research/packet.py` | `56b94121...` | ADAPTED (imports from qdw.sources) |
| `factory/builders/builder.py` | `89eeab79...` | VERBATIM |
| `factory/certification/certifier.py` | `f5c74cd1...` | VERBATIM |
| `factory/intake/ingester.py` | `367f134a...` | VERBATIM |
| `factory/ideas/generators.py` | `ef0fa3cd...` | VERBATIM |
| `factory/tasks/taxonomy.py` | `d8586644...` | VERBATIM |

### Adapted (significant rewrites)

| Module | Reason |
|---|---|
| `factory/system.py` | Rewritten to use real HotSwapRouter |
| `factory/db/migrate.py` | Rewritten for numbered migrations |
| `api.py` | Rewritten with typed errors, lifespan migration |
| `mcp/server.py` | **REJECTED** — contains syntax error, false-green |

### Rejected

| Module | Reason |
|---|---|
| `mcp/server.py` | Syntax error (`global` after use), CI never tested it |
| `conftest.py` | sys.path hack — eliminated by src/ layout |
| `factory/hotswap/__init__.py` | Empty stub |
| `factory/hotswap/integration.py` | Thin wrapper, replaced by composition root |
| `factory/hotswap/litellm_plan.py` | Optional, not core |
| `factory/hotswap/hermes_plan.py` | Optional, not core |

## Known defects in donor

1. **MCP false-green:** `mcp/server.py` has `global _system` after first use. CI check imported from installed `mcp` package, not from project.
2. **DB migration not versioned:** `migrate()` applies `CREATE TABLE IF NOT EXISTS` but never inserts a version row.
3. **API hides failure:** `/ideas` catches `OperationalError` and returns `"count": 0` instead of typed error.
4. **No route registry:** `VentureLabSystem` defaults to empty routes.
5. **sys.path hacks:** Every module uses `sys.path.insert(0, ...)` for imports.

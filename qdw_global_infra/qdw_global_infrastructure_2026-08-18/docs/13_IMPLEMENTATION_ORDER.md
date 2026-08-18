# Integration Order Into Real QDW

Do not copy everything and then debug.

## G0 — Establish proof baseline
- add verification runner
- add test guard
- add frozen acceptance specs
- run existing QDW Factory OS suite
- commit only after proof receipts exist

## G1 — Unified schema
- append global tables to existing canonical DB migration
- run empty DB migration
- run migration twice
- `PRAGMA foreign_key_check`
- compile all

## G2 — World State
- SourceResult
- Source connectors
- WorldStore
- tests for ERROR / OK_EMPTY / OK

## G3 — Intelligence
- Painfinder
- StartupRadar
- StackOracle
- AlternativeAPI
- Gitgoblin interface only
- no live Gitgoblin rewrite

## G4 — Opportunities / ideas
- OpportunityStore
- Synthesizer
- IdeaService
- review stages
- library
- cemetery
- watch triggers
- dossiers

## G5 — Global execution
- HumanQueue
- ContractorRegistry
- load contractor manifests
- WorkGraph expansion

## G6 — Products
- ProductRegistry
- FactoryGenome
- ProductPassport
- OutcomeEvents

## G7 — Publishing
- DistributionRegistry
- DocsPublisher
- PortfolioPublisher
- DomainPlanner
- external adapters only after dry-run tests

## G8 — End-to-end fixture
One fixture must execute:

```text
source → world → pain → opportunity → idea reviews
→ factory graph → contractors → product → docs/portfolio
```

No external purchase or production deployment is needed for the fixture.

## G9 — External adapters
Add one at a time:
HN → YC OSS → APIs.guru → MCP Registry → Gitgoblin → analytics → Cloudflare.

Every adapter gets:
- recorded live smoke test
- mocked deterministic contract test
- explicit failure test
- freshness metadata

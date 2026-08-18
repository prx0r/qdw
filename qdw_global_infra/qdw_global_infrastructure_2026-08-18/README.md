# QDW Global Infrastructure Integration Pack

**Date:** 2026-08-18  
**Target:** clean `src/qdw/` QDW project built on the previous Factory OS pack.

This pack adds one coherent global intelligence/product layer on top of the existing Factory OS:

```text
Sources
  ↓
World State (entities + observations + claims + relations)
  ↓
Intelligence
  ├─ Painfinder
  ├─ Startup Radar
  ├─ Stack Oracle
  ├─ Alternative API
  └─ Gitgoblin adapter (interface only)
  ↓
Opportunity Synthesis
  ↓
Idea Genome / Cemetery / Transfers
  ↓
Factory OS WorkGraph
  ↓
Contractor Mesh + Human Action Queue
  ↓
Products / Product Passports / Factory Genomes
  ↓
Publish / Portfolio / Distribution
  ↓
Outcome Events
  ↓
Portfolio learning and re-evaluation
```

## Critical design decision

There is only one canonical database and one identity graph. Painfinder, AlternativeAPI,
StackOracle, product registry, idea history, contractors, human approvals and outcomes all use
the same IDs and foreign-keyed schema. They are not separate mini-products with unrelated models.

Gitgoblin is intentionally not implemented here. `qdw.sources.gitgoblin` defines the contract
that the in-progress Gitgoblin build can implement.

## Start here

1. `docs/00_ARCHITECTURE.md`
2. `docs/01_REUSE_MATRIX.md`
3. `docs/02_UNIFIED_SCHEMA.md`
4. `agent/MASTER_IMPLEMENTATION_PROMPT.md`
5. `tasks/IMPLEMENTATION_TASKS.json`
6. `reference/src/qdw/`
7. `reference/tests/`

The reference implementation is offline-testable and deliberately small. External integrations are
adapters, not hidden dependencies.

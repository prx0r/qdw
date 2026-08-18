# Federated identity and provenance

Do not make all repositories share one global primary-key format. Use QDW-local IDs plus `FederatedRef`.

Example:

```text
QDW entity: resource_01...
  ↔ dell:offer:offer_x@revision
  ↔ forge:asset:llm.runner@1.4.0
```

Mappings are append-only observations and may split/merge later.

Every imported snapshot stores:
- source repo/service
- schema/API version
- source object ID/version
- source content digest
- request digest
- fetched/observed time
- freshness deadline
- raw artifact digest
- adapter version
- QDW normalization digest

This lets adapters evolve without rewriting history.

# StackOracle + AlternativeAPI

These share the same capability/resource registry.

## StackOracle

```text
Capability
  TTS
  OCR
  search
  browser
  payments
  auth
  embeddings
  hosting
  email
  maps
  etc.

Resource
  provider/product/version
  attributes
  interface

ResourceMeasurement
  quality
  cost
  latency
  throughput
  reliability
  quota
  etc.
```

Never store only `best_score`.

Raw measurements remain inspectable. Recommendations are computed from a versioned policy and hard
constraints. If a mandatory constraint is unknown, the candidate does not magically pass it.

## AlternativeAPI

AlternativeAPI is a read/product surface over StackOracle:

```text
current service
      ↓
capability + requirements
      ↓
matching resources
      |
      +-- suitable substitute(s) → return migration candidates
      |
      └-- none satisfy constraints → API_GAP opportunity
                                      ↓
                                  API Factory
```

Sources should include APIs.guru, official MCP Registry, provider docs, Gitgoblin signals and
eventually product-specific benchmark collectors.

## LiteLLM relationship

LiteLLM is useful as an execution/provider-normalization adapter and already exposes spend/load-balancing
concepts. HotSwap remains QDW's economic policy layer rather than being replaced by an AI gateway.

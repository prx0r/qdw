# QDW Global Architecture

## One substrate, many products

Do not build Painfinder, AlternativeAPI, StackOracle, the Idea Cemetery, Egoic and contractor
teams as separate databases.

They are views and services over one canonical state machine:

```text
SOURCES
 Gitgoblin | HN | YC | APIs.guru | MCP Registry | product analytics | future adapters
       |
       v
WORLD STATE
 Entity ─ Observation ─ Claim ─ Relation
       |
       +-------------------+-------------------+
       |                   |                   |
       v                   v                   v
  PAINFINDER          STARTUP RADAR        STACK ORACLE
       |                   |                   |
       +-------------------+-------------------+
                           |
                           v
                  OPPORTUNITY SYNTHESIS
                           |
                           v
                    IDEA GENOME LIBRARY
                   /         |          \
            reviews      cemetery      transfers
                 \           |           /
                           v
                      FACTORY OS
                           |
                  WorkGraph + HotSwap
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
 CONTRACTOR MESH                      HUMAN QUEUE
          |                                 |
          +----------------+----------------+
                           v
                         PRODUCT
                           |
             Product Passport + Factory Genome
                           |
                publish / domains / docs
                           |
                           v
                       OUTCOMES
                           |
                           v
             portfolio + re-evaluation
```

## Invariants

1. An external source failure is never an empty successful result.
2. A successful empty query is itself persisted as evidence.
3. World observations are immutable/content-addressed.
4. Derived claims point backward to observations.
5. Opportunities freeze decision-time features and evidence hashes.
6. Ideas have stable fingerprints and cannot be silently regenerated.
7. Reimplementation is a relation, not a duplicate.
8. Rejected/dormant ideas remain queryable.
9. Watch triggers recommend re-evaluation; they never silently revive an idea.
10. Contractors are versioned manifests and use normal WorkGraph nodes.
11. Human/account/payment-bound work is a first-class queued action.
12. Agents may recommend a domain; purchase remains an explicit approval gate.
13. Products retain idea/factory/run/certificate lineage.
14. Outcome signals point to products and can update later portfolio learning.
15. Verification PASS can only be produced by a recorded process exit code and required artifacts.

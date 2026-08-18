# Final runtime architecture

```text
                       EXTERNAL SOURCES
                             |
              +--------------+-------------+
              |                            |
         GitGoblin                       Dell
  technical/frontier evidence      inference economics
  repo/person/mechanism graph      offers/endpoints/evidence
              |                            |
              +-----------+----------------+
                          |
                    ExternalSnapshot
                          |
                          v
                    QDW World State
                          |
                 Opportunity / Factory
                          |
                      WorkGraph
                          |
                          v
               FederatedCandidateCollector
                 /        |         \
             local       Dell       Forge
              |            |          |
              +------------+----------+
                           |
                           v
                    QDW HotSwap
                   FINAL AUTHORITY
                           |
                    ExecutionRoute
                           |
             +-------------+-------------+
             |                           |
         local/Hermes                 QDW Forge
                                    asset@version
                                         |
                                  scoped lease token
                                         |
                                    invocation
                                         |
                               SUCCEEDED_UNVERIFIED
                                         |
                                         v
                                 QDW Verification
                                         |
                                  certificate ref
                                         |
                          +--------------+-------------+
                          |                            |
                   QDW WorkNode success        Forge local profile
                   CostEvent + posterior       idempotent update
```

## Forgejo lane

```text
Forgejo org repositories
  -> paginate
  -> resolve repo default ref to immutable commit SHA
  -> fetch qdw.yaml at that SHA
  -> validate manifest schema
  -> provenance = repo URI + commit SHA + qdw.yaml digest
  -> Forge registers immutable CapabilityAsset manifest
  -> separate activation binding attaches verification certificate
```

The manifest digest cannot change when activation state changes.

## GitGoblin lane

```text
source collectors
 -> raw observations/CAS
 -> deterministic FrontierSignal
 -> /v1/export/qdw
 -> ObservationBatch(schema version, cursor, source revision, batch digest)
 -> QDW snapshot
 -> WorldStore observations
 -> proposal import as evidence
 -> QDW Opportunity synthesis
```

GitGoblin's BUILD/WATCH/RESEARCH opinion remains advisory.

## Durable federation attempt

QDW must own a durable attempt record:

```text
DISCOVERING
CANDIDATES_READY
ROUTED
LEASED
RUNNING
SUCCEEDED_UNVERIFIED
VERIFYING
VERIFIED
COMMITTED
FAILED
```

`COMMITTED` means:
- node lifecycle transition committed;
- QDW CostEvent committed;
- QDW route posterior update committed/idempotent;
- certificate binding persisted;
- external ref/digests persisted.

Recovery is from this state record, never from guessing what probably happened.

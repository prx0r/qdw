# GitGoblin → QDW intelligence

GitGoblin should remain a standalone technical-intelligence product.

Its current VentureLab-compatible exporter is already conceptually correct: it exports derived frontier
signals with evidence hashes and source-family metadata. Replace the old product-specific shape with a
versioned federation batch.

## Transfer

```text
GitGoblin collectors
   ↓
GitGoblin observation/evidence DB
   ↓
FrontierSignal
   ↓
ObservationBatch[v1]
   ↓
QDW Federation ingest
   ↓
QDW World Observation
   ↓
QDW Claim/Opportunity synthesis
```

## Do not

- let QDW query GitGoblin's SQLite file;
- regenerate GitGoblin's source observations from summaries;
- create QDW Opportunity IDs equal to GitGoblin Opportunity IDs;
- accept GitGoblin `decision` as QDW portfolio decision.

A GitGoblin opportunity is an `OpportunityProposal`.

## Idempotency

Batch identity:
`source_system + schema_version + cursor + batch_digest`

Observation identity should retain GitGoblin's original ID through a `FederatedRef`.

# Desired API contracts

## GitGoblin

```http
GET /health
GET /v1/export/qdw?sector=ai&cursor=...
```

Response:
`ObservationBatch + OpportunityProposal[]`.

## Dell

```http
POST /v1/federation/resolve
```

Response explicitly includes:
- `authority=ADVISORY`;
- every feasible normalized candidate;
- excluded candidates/reasons;
- Dell recommendation;
- method/as-of;
- unknown fields as null.

## Forge

Existing:
```http
GET  /v1/assets?capability=...
POST /v1/leases
POST /v1/invoke
```

Replace QDW federation verification contract with:
```http
POST /v1/invocations/{id}/verification
{"certificate": VerificationCertificateReference}
```

No caller-authored `passed`.

## QDW

Suggested:
```http
GET  /v1/federation/health
POST /v1/federation/sync/gitgoblin
POST /v1/federation/preview-route
GET  /v1/federation/snapshots
GET  /v1/federation/invocations/{id}
```

Control endpoints delegate to `QDWSystem.federation`; no private DB/router instances.

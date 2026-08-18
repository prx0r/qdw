# QDW Forge finish-line integration

Reviewed starting SHA:

`2037cdb93458278bdc4807be8e84111cce72fb10`

Forge is the largest repair in this pack.

## Mandatory pre-change baseline

Run the original 49-test suite and freeze results.

## Apply

Copy:
- `migrations/0001_finishline.sql`
- `src/qdw_forge/client_auth.py`
- `src/qdw_forge/federation.py`
- `src/qdw_forge/strict_migrations.py`
- `src/qdw_forge/store_v2.py`
- `src/qdw_forge/leases_v2.py`
- `src/qdw_forge/invocation_v2.py`
- `src/qdw_forge/forgejo_v2.py`
- replacement `src/qdw_forge/app.py`
- replacement `src/qdw_forge/api.py`

Do not delete old implementations until the new contract suite is green; then remove them or keep explicitly
named compatibility wrappers that cannot be selected in production.

## Security fixes that are mandatory

### Authorization before idempotency

Invalid credentials must never retrieve an old invocation by guessing its `client_request_id`.

Correct order:

```text
authenticate client
→ validate signed lease
→ validate client/capability/operation/asset binding
→ lookup client-scoped idempotency row
→ compare exact request digest
→ invoke only if new
```

### Operation enforcement

A lease with `["inspect"]` cannot invoke.

### No caller-controlled verification

Remove:

```json
{"certificate_id":"...", "passed":true}
```

Use:

```json
{"certificate": VerificationCertificateReference}
```

Resolve the QDW certificate and bind exact:
- issuer;
- certificate hash;
- invocation ID;
- output digest;
- policy hash;
- status.

### Immutable asset definitions

`asset_id@version` identifies a definition.

Activation/certificate/status are mutable state in `asset_activations_v2`. They do not modify the definition hash.

### Verification replay

One certificate → one invocation.
One invocation → at most one verification application.
Exact replay is idempotent and does not increment the profile twice.

### Spend settlement

Quote is authorized before execution.
Actual cost is recorded after execution.
The client is never charged more than its authorized quote by surprise.

If dispatcher reports actual > quote:
- record pricing violation;
- bill at most the quote;
- surface the discrepancy for provider/asset review.

### Client identity

Forge v2 requires an authenticated stable client ID.

Production:
`QDW_FORGE_CLIENT_KEYS_JSON={"<secret>":"qdw-prod"}`

Lab:
`QDW_FORGE_LAB_MODE=1`, key `lab-client-key`.

## Forgejo

Forgejo sync must:
- paginate all repos;
- resolve the moving branch to immutable commit SHA;
- fetch `qdw.yaml` at that SHA;
- preserve repository URI + commit SHA + manifest digest;
- store typed per-repo receipts;
- reject same `asset_id@version` with changed immutable definition.

## Migration policy

Legacy `Database.migrate()` is allowed only to establish the reviewed V1 base schema. All later schema changes are
numbered, content-hashed migrations.

Once an installation has migrated, changing an applied SQL file is a hard error.

## V11

The independent lab must exercise Forge exclusively over HTTP. No importing qdw-forge into QDW's Python process.

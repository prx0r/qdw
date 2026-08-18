# QDW finish-line integration

Reviewed starting SHA:

`46920f2547e552b7f1c0e019169a350fe44cb4c1`

## 1. Preserve baseline evidence

Before modifying QDW:

```bash
python -m compileall -q src/qdw tests
pytest -q
git status --porcelain
git rev-parse HEAD
```

Store all output under the integration evidence directory.

## 2. Add migration 0011

Copy:

`migrations/0011_federation_finishline.sql`

Do not edit 0010 in-place. Historical migration 0010 has already been applied by real checkouts and its digest is
part of QDW history. Migration 0011 retires the duplicated Forge-owned local tables safely and removes secret
lease-token material from QDW.

After migration assert:

```sql
SELECT name FROM sqlite_master WHERE name IN ('forge_leases','forge_invocation_certs');
-- must return zero rows

PRAGMA table_info(route_definitions);
-- must include fixed_request_cost_usd
```

The replacement historical tables intentionally contain no lease token.

## 3. Replace HotSwap persistence

Replace `src/qdw/hotswap/persistent.py` with the finish-line version.

Mandatory invariant:

```text
Route(... fixed_request_cost_usd=0.012)
save
process restart
load
== 0.012
```

## 4. Replace/extend federation modules

Copy the finish-line files under:

`src/qdw/federation/`

Delete production:

`src/qdw/federation/forge_client.py`

No compatibility import may point back to it. Any fake Forge belongs only under tests.

## 5. Compose real services

In `QDWSystem.__init__`, replace the current federation block:

```python
from qdw.federation.service import FederationService
from qdw.federation.store import FederationStore
self.federation_store=FederationStore(self.db,self.ledger)
self.federation=FederationService(system=self,store=self.federation_store)
```

with:

```python
from qdw.federation.composition import compose_federation

fed=compose_federation(self,repo_root=self.repo_root)
self.federation_store=fed["store"]
self.federation=fed["service"]
self.federation_certificates=fed["certificates"]
self.federation_verification_policies=fed["policies"]
self.federation_runtime=fed["runtime"]
```

Add external-client closure to application shutdown if the service becomes long lived.

Environment:

```text
QDW_GITGOBLIN_URL
QDW_DELL_URL
QDW_FORGE_URL
QDW_FORGE_CLIENT_KEY
QDW_FEDERATION_TIMEOUT_SECONDS
```

Absence means the corresponding service is deliberately unconfigured, not a successful empty source.

## 6. Wire federation API

Copy:

`src/qdw/interfaces/federation_api.py`

In `src/qdw/interfaces/api.py`, after FastAPI construction:

```python
from qdw.interfaces.federation_api import router as federation_router
app.include_router(federation_router)
```

Do not create another QDWSystem inside the federation router.

## 7. Replace false-green integrations

Delete or rewrite the current `tests/integration/test_estate_forge_integration.py`.

It may not import a simulated Forge production module. Use:
- an injected `httpx.MockTransport` for unit/contract tests; and
- the independent finish-line lab for actual qdw-forge.

Rewrite Dell regression so recommended-route cost loss is a failure.

Add real modules under `tests/e2e/`.

## 8. Verification

External invocation is never success merely because Forge says execution completed.

Required sequence:

```text
Forge SUCCEEDED_UNVERIFIED
→ write content-addressed output artifact
→ capability-specific VerificationPlan
→ QDW VerificationService
→ federation certificate
→ Forge resolves exact certificate
→ WorkGraph complete
→ CostEvent + route-posterior effect, once
→ federation attempt COMMITTED
```

Unknown capability with no verification policy must fail closed.

## 9. Crash recovery

No reusable Forge lease secret may be stored in QDW.

Recovery after a crash:
- before invoke: acquire a new scoped lease and reuse the stable QDW attempt ID as Forge client request ID;
- after invoke: recover from persisted external invocation ID/output digest;
- after verify: reapply cost/learning only if no unique effect exists.

The exact same attempt replay must return the same committed effects.

## 10. Acceptance

Do not declare QDW federation complete until:
- native QDW suite passes;
- independent source gate passes;
- independent public-protocol contract suite passes;
- V11 sibling-service flow passes;
- restart script passes;
- native QDW self-review has no unsuppressed HIGH/CRITICAL federation finding.

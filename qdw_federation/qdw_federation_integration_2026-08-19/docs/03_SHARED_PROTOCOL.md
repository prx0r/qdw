# Shared federation protocol

Do not immediately create a sixth repository. Start the protocol under QDW:

```text
src/qdw/federation/contracts/
```

Once two or more external repos consume the exact same package and compatibility burden becomes real, extract
it to `qdw-protocol`.

## Fundamental objects

### FederatedRef
Identifies a foreign object without pretending it is a local QDW ID.

```json
{
  "system": "forge",
  "object_type": "capability_asset",
  "object_id": "api.builder",
  "version": "1.2.0",
  "revision": null,
  "digest": "sha256:..."
}
```

### EvidenceEnvelope
States where a fact came from and how fresh/authoritative it is.

### ObservationBatch
Idempotent transfer from GitGoblin or another intelligence service.

### ResourceCandidateSnapshot
Dell/Forge resource facts captured at one time and content-hashed.

### DecisionAdvisory
A foreign service recommendation. `authority=false` for QDW lifecycle decisions.

### CapabilityExecutionRequest
QDW's request to an execution exchange, with an **explicit selected asset**.

### InvocationOutcome
An execution happened; status must be `SUCCEEDED_UNVERIFIED`, `FAILED`, etc.

### VerificationCertificateRef
Cross-service pointer to a certificate with enough subject/hash metadata to prevent evidence substitution.

## Protocol invariant

`external_id` strings alone are insufficient trust evidence. Trust-boundary references bind:

```text
system
object_type
object_id
version/revision
content digest
policy/subject digest where applicable
```

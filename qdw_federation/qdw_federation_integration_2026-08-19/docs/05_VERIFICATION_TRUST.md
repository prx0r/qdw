# Verification across trust domains

Current Forge invocation semantics are close to correct:
execution ends `SUCCEEDED_UNVERIFIED`, then verification binds a certificate.

The problematic part is an API shaped like:

```json
{"certificate_id": "...", "passed": true}
```

The boolean is caller-authored.

## Replacement

```json
{
  "certificate": {
    "issuer_system": "qdw",
    "certificate_id": "cert_...",
    "certificate_hash": "sha256:...",
    "subject": {
      "system": "forge",
      "object_type": "invocation",
      "object_id": "inv_...",
      "digest": "sha256:output..."
    },
    "policy_hash": "sha256:...",
    "status": "VERIFIED",
    "verification_url": "..."
  }
}
```

Forge resolves/verifies the certificate or a signed envelope before changing its profile.

## Subject binding

A valid QDW certificate for invocation A cannot verify invocation B.

At minimum match:
- invocation ID
- asset ID/version
- output hash
- QDW WorkNode/FactoryRun if supplied
- policy hash
- certificate status
- issuer allowlist
- certificate content hash/signature

## Independent lifecycle

Forge remains free to record:
`VERIFIED` / `REJECTED`

QDW separately transitions:
`VERIFYING -> SUCCEEDED/FAILED`

These states are related by the certificate but do not share a database.

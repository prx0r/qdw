# Security / side-effect boundaries

Federation increases blast radius. Default-deny.

- GitGoblin adapter is read-only.
- Dell adapter is read-only for routing intelligence.
- Forge execution requires scoped lease token.
- Sandbox is disabled in production unless a specific graduated capability is intentionally invoked.
- QDW controls allowed network/write permissions per WorkNode.
- Credentials belong to adapters/executors, not WorkNode payload logs.
- External raw responses are untrusted input.
- Certificate resolver has issuer allowlist.
- No service can push/merge/deploy/buy without QDW policy + HumanQueue where required.

The integration tests include evidence-substitution, cross-asset, stale-snapshot and external-state spoofing cases.

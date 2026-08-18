# QDW Federation Skill

Use when a QDW WorkNode needs data or execution from another QDW ecosystem repository.

## Decision order

1. Identify the foreign system's declared role from `repo_contracts/`.
2. Check QDW still owns the relevant lifecycle decision.
3. Obtain a versioned external snapshot/capability.
4. Preserve external ID, version, digest, freshness and evidence.
5. Let QDW make the canonical decision.
6. If executing through Forge, pin exact asset/version.
7. Treat execution as unverified until QDW certificate.
8. Record CostEvent and external refs.
9. Never read another service's SQLite database directly.

Failure != empty.
Unknown != zero.
Advisory != authority.

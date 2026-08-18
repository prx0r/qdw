# Contractor Mesh

A contractor is a versioned reusable global quality/process formula.

Identity:

```text
team.specialization@version
```

Examples:

- `redteam.api@1`
- `redteam.app@1`
- `qa.connector@1`
- `security.agent@1`
- `publish.python@1`
- `domain.general@1`

A contractor expands into a normal WorkGraph node. It gets no privileged backdoor.

## Standard global teams

Research, Architecture, Builder, QA, Red Team, Security, Provenance, Cost/FinOps, Docs, Publish,
Domain, Observability, Post-release, Maintenance and Portfolio Review.

## Independence

The producer cannot certify itself. Factory policies should prevent the same run/worker identity from
satisfying both production and independent certification gates where independence matters.

## Version immutability

Changing gates requires a new contractor version. Historical products retain the exact contractor version
in their Factory Genome.

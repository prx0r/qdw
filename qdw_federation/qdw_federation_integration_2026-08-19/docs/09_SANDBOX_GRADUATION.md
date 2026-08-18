# Sandbox graduation plan

Sandbox is successful when useful ideas leave it.

## Graduate now

### Contracts
Estate `CapabilityRequest`, `ExecutionConstraints`, `ResourceDescriptor`, `ExecutorConfiguration`,
`ResourceProfile` are good donors for the shared federation protocol.

Normalize names rather than copying both versions permanently.

### Context
Graduate ContextPack assembly into QDW execution context infrastructure. It should package immutable refs and
budgets for a WorkNode, not become another lifecycle authority.

### Resource policies
Extract historical/cluster/cascade scoring math as pure QDW HotSwap policy features. No EstateRouter service in
production.

### Episodes
Use execution episodes as a general observability record, but QDW WorkNodeRun/Attempt remains lifecycle truth.

### Human / bounty
Map:
- HumanOracle -> Contractor/HumanQueue capability provider
- Bounty -> Opportunity/Contractor market work
- DataRights -> common RightsHandle / policy constraints

### Artifact store
Compare Sandbox local CAS to QDW ArtifactStore. Keep one canonical QDW artifact identity and implement alternate
backends if Sandbox's code is better.

## Retire/Archive

- duplicate `_review_system` packages
- copied build packs
- Estate verification authority
- Estate final route authority
- any direct production dependency on Sandbox's SQLite DB

## Graduation gate

A Sandbox feature graduates only after:
1. explicit target owner selected;
2. contract mapping written;
3. historical behavior fixture frozen;
4. target implementation passes fixture;
5. duplicate authority removed;
6. Sandbox keeps only experiment or compatibility adapter.

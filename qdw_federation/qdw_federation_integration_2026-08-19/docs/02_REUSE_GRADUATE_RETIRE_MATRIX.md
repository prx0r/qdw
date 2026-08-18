# KEEP / ADAPT / GRADUATE / RETIRE matrix

## QDW

**KEEP**
- WorkGraph and economic scheduler
- canonical verification/review
- HotSwap final route
- World/Opportunity/Idea/Product/Outcome
- HumanQueue and contractor substrate
- CostLedger

**ADD**
- federation registry
- external snapshot store
- GitGoblin/Dell/Forge clients
- capability execution adapter
- certificate reference resolver
- external health/freshness policy

## QDW Forge

**KEEP**
- CapabilityAsset / FactoryCapsule
- leases and signed/scoped lease tokens
- idempotent invocation records
- dispatcher/transports
- empirical AssetProfile
- capability discovery API

**ADAPT**
- verification endpoint: replace `{certificate_id, passed}` with a verifiable `CertificateReference`
- canonical QDW mode: lease pinned asset/version; do not reroute outside lease
- record QDW decision/advisory refs in invocation provenance
- expose candidate/profile snapshot endpoint if not already cleanly available

**KEEP AS LOCAL FEATURE**
- `VerifiedProfileRouter` for independent Forge clients.
- Under QDW it is a nested/local policy only.

## QDW Sandbox / Estate

**GRADUATE**
- `CapabilityRequest`
- `ExecutionConstraints`
- `ResourceDescriptor`
- `ExecutorConfiguration`
- `ResourceProfile`
- execution episode vocabulary
- ContextPack/context assembly
- useful historical/cluster/cascade policy math
- artifact-CAS design ideas
- HumanOracle/DataRights/Bounty primitives after mapping to canonical QDW objects

**RETIRE FROM PRODUCTION AUTHORITY**
- `EstateRouter` as final route authority
- `EstateVerificationService` as QDW WorkGraph verifier
- duplicate Estate resource DB as permanent truth
- bundled `_review_system` / `_lifegit` packs as runtime source
- any scheduler that independently claims QDW work

Sandbox remains the place to prototype those ideas.

## GitGoblin

**KEEP**
- all source collectors
- append-only source observations
- expertise/attention graph
- deterministic technical-alpha/momentum/novelty/convergence
- primitive/opportunity derivation
- independent API/MCP product

**ADAPT**
- replace VentureLab-specific exporter with `qdw.federation.ObservationBatch`
- emit stable external entity refs rather than expecting shared DB IDs
- attach source cursor, batch hash and schema version
- QDW opportunity ingestion should preserve GitGoblin provenance rather than treat exported opportunities as QDW decisions

## Dell

**KEEP**
- source adapters and source-health/freshness machinery
- Evidence → Claims → Assertions → Offers
- endpoint-level candidate construction
- unknown-policy semantics
- DecisionService as public product API/MCP
- scoring and badges for Dell users

**ADAPT**
- add a federation candidate/advisory response that exposes *all feasible candidates and evidence refs*
- QDW should consume Dell's recommendation as an advisory, not final authority
- freeze/canonicalize an advisory hash and as-of timestamp
- map Dell model/provider/endpoint/offer identity into `FederatedRef`

**DO NOT COPY**
- provider scraping logic into QDW
- Dell's database into QDW
- Dell's final recommendation logic into HotSwap wholesale

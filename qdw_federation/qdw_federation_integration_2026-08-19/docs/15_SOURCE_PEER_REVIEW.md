# Source-level peer review of the five pinned repositories

This review was performed against the exact SHAs in `pins/REPOS.json`.

## QDW

Current composition root already has:
- one QDW WorkGraph;
- one persistent HotSwap route registry;
- global World/Pain/Stack/Idea/Human/Contractor/Product services;
- canonical VerificationService;
- native Review runtime.

This is the correct integration center.

**Do not transplant another scheduler/router/verifier into QDW.**

## QDW Forge

Strong:
- versioned `CapabilityAsset`;
- `FactoryCapsule`;
- ACTIVE requires certificate metadata;
- scoped leases;
- invocation idempotency;
- lease can pin asset/version;
- invocation returns `SUCCEEDED_UNVERIFIED`;
- asset-local empirical profile.

Integration defect:
- verification binding API still accepts caller-authored `passed: bool`.
- replace with certificate resolution/binding.

Architectural conclusion:
**Forge is the execution/capability exchange.**

## QDW Sandbox / Estate

Strong donors:
- CapabilityRequest + ExecutionConstraints;
- ResourceDescriptor + ExecutorConfiguration;
- ResourceProfile;
- execution episode vocabulary;
- context/resource/verification experiments;
- historical/cluster/cascade policies.

Conflict:
- Estate has its own `EstateRouter`;
- Estate has its own `EstateVerificationService` that can complete graph nodes.

Architectural conclusion:
**graduate pure contracts/algorithms, disable duplicate production authority.**

## GitGoblin

Strong:
- independent frontier source collection;
- append-only observations/evidence;
- technical attention/expertise graph;
- deterministic frontier metrics;
- own API/MCP;
- current VentureLab/Cuntgoblin export already includes evidence hashes.

Integration change:
- rename/productize exporter as versioned QDW federation protocol;
- export Opportunity as proposal/advisory;
- preserve raw GitGoblin identity and cursor.

Architectural conclusion:
**GitGoblin is a technical intelligence oracle.**

## Dell

Strong:
- distinct evidence/claim/assertion/offer model;
- source freshness/health;
- many provider-specific adapters;
- endpoint-level candidates;
- DecisionService shared across interfaces;
- explicit unknown hard-constraint policy;
- candidate exclusions and evidence coverage.

Integration issues:
1. normal recommendation result exposes only top candidates, so add a dedicated federation response containing
   complete normalized feasible candidate facts;
2. Dell recommendation must remain `ADVISORY`;
3. discovered correctness regression: `calculate_workload_cost` treats unknown output price as zero even with
   output tokens. Fix this before QDW consumes cost-sensitive decisions.

Architectural conclusion:
**Dell is the model/provider/resource oracle, not QDW's final route authority.**

# System-level overlap map

```text
                QDW       FORGE      ESTATE      DELL       GITGOBLIN
WorkGraph       OWNER       -        DUPLICATE      -            -
Scheduler       OWNER       -        DUPLICATE      -            -
Final route     OWNER     LOCAL       DUPLICATE    ADVISORY        -
Verification    OWNER     LOCAL*      DUPLICATE      -            -
Resource truth  cache      assets      donor       OWNER          -
Tech signals    cache       -           -           -          OWNER
Invocation       local    OWNER          -           -            -
Portfolio       OWNER       -            -           -         advisory
```

`LOCAL*`: Forge may own verification state of a Forge invocation, but its status should derive from a certificate
issued/resolved from the authority that verified the invocation result for QDW.

# Routing reconciliation

There are currently four pieces that look like routers:

1. QDW HotSwap
2. Dell DecisionService
3. Forge VerifiedProfileRouter
4. Sandbox EstateRouter

They do not need to fight.

## Layering

```text
QDW EconomicScheduler
   decides which WorkNode deserves execution
          |
          v
Candidate collection
   Dell: model/provider candidates
   Forge: capability assets
   local executors: Hermes/etc
          |
          v
QDW HotSwap
   hard policy + task posterior + cost + quota + evidence freshness
          |
          v
ExecutionRoute
          |
          +--> direct provider/model route
          +--> Hermes/local executor
          +--> Forge asset_id@version
```

Dell answers: **what external inference options appear economically/technically feasible right now?**

Forge answers: **which certified capability assets exist, and what is their verified local performance?**

Estate algorithms answer: **what additional historical/cluster/cascade policy features might improve routing?**

QDW answers: **given this specific WorkNode and global budget, what route is canonical?**

## Dell integration mode

Prefer adding/using an endpoint analogous to:

```text
POST /v1/federation/candidates
```

returning eligible + excluded candidates, evidence refs, estimated workload cost and advisory recommendation.

If the current resolve endpoint is used initially:
- retain recommended + alternatives + exclusions;
- freeze raw response hash;
- label it `ADVISORY`;
- never translate Dell score directly to `p_success`.

## Forge integration mode

QDW first chooses `forge:<asset>@<version>`.

Then:

1. create Forge lease with `asset_id` and `version`;
2. invoke capability under that lease;
3. assert returned invocation asset/version equals QDW selection;
4. store Forge's route decision hash as nested provenance;
5. independently verify;
6. send certificate reference back to Forge.

## Double-learning rule

Different systems learn different variables:

- Dell: external provider/resource truth and benchmarks.
- Forge: asset-local verified invocation success/cost.
- QDW HotSwap: success of a route for a QDW task cell.
- QDW FactoryLearning: factory/product/business outcomes.

Never ingest Forge alpha/beta directly as if it were QDW task posterior. It is an input feature/prior with its
own source and sample count.

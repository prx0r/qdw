# Federated architecture

```text
                         PUBLIC / EXTERNAL WORLD
                                  |
          +-----------------------+----------------------+
          |                                              |
          v                                              v
     GITGOBLIN                                        DELL
 technical frontier                          model/provider/deal oracle
 observations/signals                        evidence/claims/offers
          |                                              |
          | ObservationBatch                             | ResourceAdvisory
          +----------------------+-----------------------+
                                 v
                              QDW CORE
                    canonical World + Opportunity
                    portfolio/economic scheduler
                    WorkGraph + budgets + costs
                    canonical HotSwap decision
                    Verification + Review
                    Products + Outcomes
                                 |
                      CapabilityExecutionRequest
                                 |
                                 v
                            QDW FORGE
                 capability assets / factory capsules
                     lease + invocation transport
                    asset-local verified profile
                                 |
                +----------------+----------------+
                |                                 |
                v                                 v
          HTTP/MCP/A2A                        human/data/etc
          tools/agents                         adapters
                |
                v
       SUCCEEDED_UNVERIFIED
                |
                +-----------> QDW Verification
                                  |
                           CertificateReference
                                  |
                                  v
                           Forge profile update
```

`qdw-sandbox` sits beside this graph as an **incubator/donor**, not a production authority:

```text
Sandbox Estate algorithms/contracts
    |
    +--> shared federation contracts
    +--> QDW routing policy plugins
    +--> QDW ContextPack / execution episode concepts
    +--> QDW HumanQueue / contractor features
    +--> Forge data-rights/capability metadata
    |
    X no second production WorkGraph
    X no second production verifier
    X no second final route authority
```

## Why federation instead of merging

These repositories have different truth domains:

- GitGoblin's raw collector state is useful on its own.
- Dell's rapidly changing provider intelligence should remain a product/service.
- Forge can become a reusable capability exchange for QDW and other agents.
- Sandbox needs freedom to break things without migrating permanent QDW history.
- QDW is where cross-domain economic decisions and business outcomes meet.

The integration contract is therefore **content-addressed snapshots + explicit authority**, not shared SQLite files.

## End-to-end example

1. GitGoblin sees a new coding-agent primitive and emits hashed technical observations.
2. QDW ingests them into World State and synthesizes an opportunity.
3. A FactoryRun reaches a coding WorkNode.
4. QDW asks Dell for current model/provider candidates and evidence.
5. QDW asks Forge for certified capability assets that can execute the node.
6. QDW HotSwap combines these inputs with its own task posterior, budget and policy and selects a route.
7. If Forge is selected, QDW creates a lease pinned to `asset_id@version`.
8. Forge invokes exactly that leased asset and returns `SUCCEEDED_UNVERIFIED`.
9. QDW independently verifies the artifact/output.
10. QDW issues a certificate reference; Forge resolves it and records the invocation as VERIFIED/REJECTED.
11. Forge updates its asset-local posterior.
12. QDW updates task/factory/business learning from its own outcome layer.

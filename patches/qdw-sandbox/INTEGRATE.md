# Sandbox integration / graduation patch

Create `src/sandbox/estate/federation/`.

Do NOT reconfigure QDW to call EstateRouter or EstateVerificationService in production.

Instead:
- freeze Estate policy behavior tests;
- port historical/cluster/cascade scoring into QDW HotSwap policy plugins;
- port ContextPack into QDW execution context;
- port DataRights vocabulary into shared federation contracts;
- map HumanOracle/Bounty into QDW Contractor/HumanQueue;
- keep the Sandbox implementations as research/reference until the target modules prove equivalent behavior.

After graduation, delete/disable the duplicate production composition paths but keep fixtures/history.

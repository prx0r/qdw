# QDW Red Team Skill

Use for release review, trust-boundary changes, Factory/Contractor activation changes, migrations, WorkGraph,
HotSwap, product release, API/MCP control plane, or when another reviewer requests adversarial proof.

Load:
- `attacks/ATTACK_CATALOG.json`
- `prompts/redteam.md`

Prioritize attacks implicated by changed paths, but run the policy-required release set before certification.

Every executed attack needs:
- attack_id
- exact Git SHA
- expected behavior
- test/command identity
- process receipt
- actual rejection reason
- PASS only if QDW rejected the bad state for the intended reason.

Do not count crashes, test-runner failures, missing dependencies, or timeouts as successful rejection unless the attack
spec specifically targets that failure mode.

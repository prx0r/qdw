# Authority matrix

| Concern | Authority | Advisory / donor | Forbidden duplication |
|---|---|---|---|
| Portfolio allocation | QDW | GitGoblin/Dell signals | Forge/Sandbox deciding capital |
| WorkGraph lifecycle | QDW | — | Estate WorkGraph in production |
| Node scheduling | QDW | Estate algorithms may be plugins | Forge/Dell scheduling QDW nodes |
| Final execution route | QDW HotSwap | Dell + Forge + policy plugins | Dell/Forge silently replacing QDW decision |
| Provider/model truth | Dell | QDW cached snapshots | copying Dell source adapters into QDW |
| Technical frontier truth | GitGoblin | QDW cached observations | QDW duplicating attention collectors |
| Capability asset registry | Forge | QDW external refs | QDW copying Forge DB |
| Capability lease | Forge | QDW request | QDW forging lease state |
| Invocation transport | Forge | QDW selected asset | Sandbox competing transport |
| QDW node verification | QDW | Forge invocation evidence | Forge `passed=true` as authority |
| Forge asset profile | Forge | QDW certificate refs | QDW directly mutating Forge profile |
| Factory/product certification | QDW | external sub-certificates | Dell/Forge releasing QDW products |
| Human irreversible approval | QDW HumanQueue | Sandbox HumanOracle donor | external service auto-approving |
| Data-rights metadata | canonical ref in QDW + Forge | Sandbox DataRights donor | incompatible duplicate rights vocabularies |
| Raw frontier DB | GitGoblin | — | QDW reads DB file directly |
| Raw Dell DB | Dell | — | QDW reads DB file directly |
| Sandbox experiments | Sandbox | graduate after proof | depending on sandbox DB at runtime |

## Advisory vs authority

Every federation response is explicitly one of:

- `OBSERVATION` — source says something happened.
- `ADVISORY` — provider suggests a decision.
- `CAPABILITY` — provider declares something can be invoked.
- `EXECUTION_RESULT` — work happened, not yet trusted.
- `CERTIFICATE` — an authority proves a bounded claim.

A Dell recommendation is an advisory. A Forge route decision is an advisory/subroute. Neither may directly
transition a QDW WorkNode to `SUCCEEDED`.

## No dual routing truth

Dell's DecisionService is valuable because it knows provider/model facts. Forge's router is valuable because it
knows asset-local performance. Estate has useful historical/cluster/cascade policies. QDW HotSwap is the
**composition point**.

Recommended production mode:

```text
Dell -> candidate/advisory snapshot
Forge -> asset candidate/profile snapshot
Estate policies -> optional scoring features
QDW HotSwap -> final route
```

When QDW delegates to Forge, lease `asset_id` and `version` explicitly. Forge may still produce a nested
RouteDecision as proof that the pinned asset was chosen, but it cannot silently substitute another asset.

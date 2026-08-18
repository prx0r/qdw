# Authority matrix

| Concern | Canonical owner | Others |
|---|---|---|
| WorkGraph lifecycle | QDW | no external writer |
| Capital/portfolio allocation | QDW | oracles provide evidence |
| Final route | QDW HotSwap | Dell/Forge local scores are advisory/features |
| Provider/model/deal facts | Dell | QDW stores immutable snapshots |
| Frontier/repository facts | GitGoblin | QDW stores immutable snapshots |
| Capability manifests | Forge | QDW stores refs/digests |
| Forge leases | Forge | QDW stores lease ID/ref, never reusable secret token |
| Forge invocation | Forge | QDW stores external invocation ref |
| QDW acceptance | QDW Verification | Forge cannot self-certify QDW work |
| Forge performance profile | Forge | updated from independently resolved certificate |
| Repo host / qdw.yaml source | Forgejo | Forge pins commit/file digest |
| Sandbox experiments | Sandbox | graduate, then disable duplicate authority |

# QDWSystem composition patch

After migrations 0005/0006 and proof/graph hardening are installed, `QDWSystem` should compose review once.

Add:

```python
from qdw.executors.hermes import HermesExecutor
from qdw.review.bootstrap import build_review_runtime

# after core services exist
self.hermes = HermesExecutor(profile="qdw-review")
self.verification, self.review, self.review_controller = build_review_runtime(
    self,
    repo_root=repo_root,
    executor=self.hermes,
)
```

Prefer making `repo_root` an explicit QDWSystem constructor/config setting rather than deriving it from CWD.

Then API/MCP/CLI access `system.review`, never their own review DB or runner.

Also replace current `self.routes: list[Route]` with a dedicated RouteRegistry keyed by route_id;
`QDWSystem.register_route` must update/replace rather than append duplicates.

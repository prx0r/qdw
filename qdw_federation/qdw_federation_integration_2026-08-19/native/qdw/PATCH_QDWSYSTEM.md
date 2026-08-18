# QDWSystem integration

Add after canonical World/HotSwap/proof construction:

```python
from qdw.federation.store import FederationStore
from qdw.federation.service import FederationService
from qdw.federation.clients import GitGoblinClient, DellClient, ForgeClient
from qdw.federation.gitgoblin_adapter import GitGoblinFederationAdapter
from qdw.federation.dell_adapter import DellFederationAdapter
from qdw.federation.forge_adapter import ForgeExecutionAdapter

self.federation_store = FederationStore(self.db,self.ledger,artifact_store=getattr(self,"artifacts",None))

gg_client = GitGoblinClient(settings.gitgoblin_url,"gitgoblin") if configured else None
dell_client = DellClient(settings.dell_url,"dell") if configured else None
forge_client = ForgeClient(settings.forge_url,"forge") if configured else None

gg_adapter = GitGoblinFederationAdapter()
dell_adapter = DellFederationAdapter()
forge_adapter = ForgeExecutionAdapter(forge_client,self.federation_store,self.ledger,self.db) if forge_client else None

self.federation = FederationService(
    self,store=self.federation_store,
    gitgoblin_client=gg_client,gitgoblin_adapter=gg_adapter,
    dell_client=dell_client,dell_adapter=dell_adapter,
    forge_adapter=forge_adapter,
)
```

Do not let `FederationService` instantiate:
- another WorkGraphStore
- another scheduler
- another HotSwapRouter
- another VerificationService

It is an adapter/composition service only.

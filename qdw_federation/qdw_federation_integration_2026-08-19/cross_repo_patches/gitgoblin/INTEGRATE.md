# GitGoblin integration patch

Add `gitgoblin/integrations/qdw.py`.

In `create_app`, add:

```python
from .integrations.qdw import build_export

@app.get("/v1/export/qdw")
def export_qdw(sector: str | None = None, cursor: str | None = None):
    return build_export(store, sector, cursor)
```

Keep `/v1/export/cuntgoblin` temporarily for compatibility, but QDW must consume `/v1/export/qdw`.

QDW's adapter treats `opportunity_proposals[].external_decision` as external advisory context only.

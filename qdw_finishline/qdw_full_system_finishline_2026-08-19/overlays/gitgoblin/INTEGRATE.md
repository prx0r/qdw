# GitGoblin QDW federation patch

1. Copy `gitgoblin/integrations/qdw.py`.
2. In `gitgoblin/api.py` import `build_export`.
3. Add:

```python
@app.get("/v1/export/qdw")
def export_qdw(sector: str | None = None, cursor: str | None = None, limit: int = 1000):
    return build_export(store, sector=sector, cursor=cursor, limit=min(limit, 5000))
```

4. Keep `/v1/export/cuntgoblin` temporarily for compatibility, but QDW must use only `/v1/export/qdw`.
5. Set `GITGOBLIN_BUILD_SHA` in deployment/CI to the exact source SHA.
6. Contract test response over HTTP from the independent lab.
7. A GitGoblin opportunity remains `ADVISORY`; QDW decides whether it becomes a QDW Opportunity.

# Dell finish-line integration

## 1. Repair the cost invariant

In `app/services/decision.py::calculate_workload_cost` replace the current output-price handling with:

```python
if candidate.input_per_m is None:
    return None
if workload.output_tokens_per_request > 0 and candidate.output_per_m is None:
    return None
output_per_m = candidate.output_per_m or 0.0
```

This matches the function's own contract: unknown price is not zero.

## 2. Add the federation module

Copy `app/federation.py`.

## 3. Add API endpoint to `app/api_canonical.py`

```python
from app.federation import federation_resolve, load_endpoints

@app.post("/v1/federation/resolve")
def qdw_federation_resolve(body: dict):
    data=_load_all()
    conn=canonical_db.connect()
    canonical_db.migrate(conn)
    try:
        endpoints=load_endpoints(conn)
    finally:
        conn.close()
    return federation_resolve(body,data["offers"],endpoints)
```

No route status in this response is QDW authority. `authority` is always `ADVISORY`.

## 4. Run both Dell's full native suite and the independent HTTP lab.

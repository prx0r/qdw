# Dell integration patch

Add `app/federation.py`.

Expose a **new** endpoint in the canonical API rather than forcing QDW to reverse-engineer `/v1/deals`:

```python
from app.federation import federation_resolve

@app.post("/v1/federation/resolve")
def qdw_federation_resolve(body: dict):
    data = _load_all()
    # Load endpoint records from the canonical endpoint table if available.
    endpoints = ...
    return federation_resolve(body, data["offers"], endpoints)
```

The implementation agent must wire the real canonical endpoint loader after cloning Dell. Do not synthesize missing
endpoint facts. If endpoint data is unavailable, pass `[]` and preserve unknown fields.

QDW consumes this as `DecisionAdvisory + ResourceCandidateSnapshot`; Dell never writes QDW lifecycle state.


## Mandatory Dell correctness repair discovered during integration

Current `calculate_workload_cost()` says unknown must not become zero, but it checks only unknown input price and
then does:

```python
output_per_m = candidate.output_per_m if candidate.output_per_m is not None else 0
```

When workload output tokens are non-zero, unknown output price must make workload cost `None`.

Change to:

```python
if candidate.input_per_m is None:
    return None
if workload.output_tokens_per_request > 0 and candidate.output_per_m is None:
    return None
output_per_m = candidate.output_per_m or 0.0
```

Freeze/run `tests/test_unknown_output_price.py` before and after this repair.

# Generalize QDW HotSwap Route for federated/per-call capabilities

Forge assets are often priced per invocation. Do **not** synthesize fake token prices just to fit the current
`Route.request_cost()` shape.

## `src/qdw/hotswap/types.py`

Add:

```python
fixed_request_cost_usd: float | None = None
```

to `Route`.

Then make `request_cost`:

```python
def request_cost(self, task: TaskSpec) -> float | None:
    if self.free:
        return 0.0
    if self.fixed_request_cost_usd is not None:
        return self.fixed_request_cost_usd
    if self.input_per_m is None:
        return None
    if task.estimated_output_tokens > 0 and self.output_per_m is None:
        return None
    out_price = self.output_per_m or 0.0
    return (
        self.input_per_m * task.estimated_input_tokens
        + out_price * task.estimated_output_tokens
    ) / 1_000_000
```

Validate fixed cost >= 0.

## `src/qdw/hotswap/persistent.py`

Persist/load `fixed_request_cost_usd` in `route_definitions`.

The federation migration adds the column.

## Why this belongs in core

Per-call pricing is not Forge-specific. MCP tools, browser sessions, external agents, APIs and future human
capabilities may all have fixed per-call prices.

This turns HotSwap into a more general capability router without changing its authority.

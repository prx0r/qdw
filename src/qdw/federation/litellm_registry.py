"""LiteLLM model registry — reads 3,040 models with real pricing.

LiteLLM provides universal model routing with actual provider pricing.
QDW uses this as the baseline cost model, then Dell overlays deal adjustments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelPricing:
    model_id: str
    input_cost_per_token: float
    output_cost_per_token: float
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    provider: str = ""
    supports_function_calling: bool = False
    supports_vision: bool = False

    @property
    def input_cost_per_million(self) -> float:
        return self.input_cost_per_token * 1_000_000

    @property
    def output_cost_per_million(self) -> float:
        return self.output_cost_per_token * 1_000_000

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            self.input_cost_per_token * input_tokens
            + self.output_cost_per_token * output_tokens
        )


class LiteLLMRegistry:
    """Reads LiteLLM's model pricing data into QDW's cost model."""

    def __init__(self, pricing_path: str | Path | None = None):
        if pricing_path is None:
            # Try to find LiteLLM's pricing data relative to project root
            project_root = Path(__file__).resolve().parents[3]
            pricing_path = Path("/mnt/HC_Volume_106427611/litellm") / "model_prices_and_context_window.json"
        self.pricing_path = Path(pricing_path)
        self._models: dict[str, ModelPricing] = {}
        self._loaded = False

    def load(self) -> int:
        """Load pricing data. Returns number of models loaded."""
        if not self.pricing_path.exists():
            return 0
        with open(self.pricing_path) as f:
            data = json.load(f)
        for model_id, info in data.items():
            if not isinstance(info, dict):
                continue
            input_cost = info.get("input_cost_per_token", 0)
            output_cost = info.get("output_cost_per_token", 0)
            if input_cost == 0 and output_cost == 0:
                continue  # Skip free/unknown models
            self._models[model_id] = ModelPricing(
                model_id=model_id,
                input_cost_per_token=input_cost,
                output_cost_per_token=output_cost,
                max_input_tokens=info.get("max_input_tokens"),
                max_output_tokens=info.get("max_output_tokens"),
                supports_function_calling=info.get("supports_function_calling", False),
                supports_vision=info.get("supports_vision", False),
            )
        self._loaded = True
        return len(self._models)

    def get(self, model_id: str) -> ModelPricing | None:
        if not self._loaded:
            self.load()
        return self._models.get(model_id)

    def search(self, query: str, limit: int = 10) -> list[ModelPricing]:
        """Search models by partial name match."""
        if not self._loaded:
            self.load()
        results = []
        q = query.lower()
        for model in self._models.values():
            if q in model.model_id.lower():
                results.append(model)
                if len(results) >= limit:
                    break
        return sorted(results, key=lambda m: m.input_cost_per_token)

    def cheapest(self, *,
                 supports_function_calling: bool | None = None,
                 max_input_tokens: int | None = None,
                 limit: int = 5) -> list[ModelPricing]:
        """Find cheapest models matching criteria."""
        if not self._loaded:
            self.load()
        candidates = list(self._models.values())
        if supports_function_calling is not None:
            candidates = [m for m in candidates if m.supports_function_calling == supports_function_calling]
        if max_input_tokens is not None:
            candidates = [m for m in candidates if m.max_input_tokens and m.max_input_tokens >= max_input_tokens]
        return sorted(candidates, key=lambda m: m.input_cost_per_token)[:limit]

    def to_routes(self, model_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Convert models to QDW Route format."""
        if not self._loaded:
            self.load()
        models = [self._models[mid] for mid in (model_ids or list(self._models.keys())) if mid in self._models]
        routes = []
        for m in models:
            provider = m.model_id.split(".")[0] if "." in m.model_id else "unknown"
            routes.append({
                "route_id": f"litellm:{m.model_id}",
                "model_id": m.model_id,
                "provider_id": provider,
                "input_per_m": m.input_cost_per_million,
                "output_per_m": m.output_cost_per_million,
                "context_tokens": m.max_input_tokens,
                "tools_supported": m.supports_function_calling,
            })
        return routes

    @property
    def model_count(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._models)

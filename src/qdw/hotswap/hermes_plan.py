"""HotSwap Hermes plan — execution plan to Hermes profile fragment."""

from __future__ import annotations

from qdw.hotswap.types import ExecutionPlan


def hermes_profile_fragment(plan: ExecutionPlan, litellm_base_url: str, key_env: str = "LITELLM_API_KEY") -> dict:
    if plan.primary is None:
        raise ValueError("no primary route")

    def entry(a):
        return {
            "provider": "custom",
            "model": f"route/{a.route.route_id}",
            "base_url": litellm_base_url,
            "key_env": key_env,
        }

    return {
        "model": {
            "provider": "custom",
            "default": f"route/{plan.primary.route.route_id}",
            "base_url": litellm_base_url,
        },
        "fallback_providers": [entry(a) for a in plan.fallbacks],
    }

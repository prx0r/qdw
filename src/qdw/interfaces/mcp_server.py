"""QDW MCP server — official SDK v2, testable with in-process Client."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

mcp = MCPServer("QDW")

_system = None


def _get_system():
    global _system
    if _system is None:
        from qdw.system import QDWSystem
        _system = QDWSystem("data/qdw.db")
    return _system


@mcp.tool()
def qdw_get_status() -> dict[str, Any]:
    """Get QDW system status including ledger verification."""
    return _get_system().doctor()


@mcp.tool()
def qdw_list_factories() -> list[dict[str, Any]]:
    """List registered factory definitions."""
    return _get_system().factories.list()


@mcp.tool()
def qdw_route_task(
    task_kind: str,
    quality: float = 0.8,
) -> dict[str, Any]:
    """Route a task through HotSwap."""
    from qdw.hotswap.router import HotSwapRouter
    from qdw.hotswap.types import TaskSpec

    task = TaskSpec(task_id="mcp_preview", task_kind=task_kind, quality_floor=quality)
    plan = HotSwapRouter().plan(task, [])

    def _c(x):
        if x is None:
            return None
        return {
            "route_id": x.route.route_id,
            "model_id": x.route.model_id,
            "p_success": x.p_success,
        }

    return {
        "task_id": task.task_id,
        "primary": _c(plan.primary),
        "reason_codes": plan.reason_codes,
    }

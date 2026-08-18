"""QDW MCP server — official SDK v2, delegates to QDWSystem."""

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
    """Route a task through HotSwap using registered routes."""
    return _get_system().route_task(task_kind, {"quality": quality})

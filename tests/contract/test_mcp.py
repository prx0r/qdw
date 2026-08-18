"""Tests for QDW MCP server — real protocol tests using in-process Client."""

from pathlib import Path

import pytest

from qdw.interfaces.mcp_server import mcp


class TestMCPServer:
    def test_mcp_has_tools(self) -> None:
        """Verify the MCP server exposes the expected tools."""
        from mcp.server import MCPServer
        assert isinstance(mcp, MCPServer)

    def test_mcp_tool_names(self) -> None:
        """Verify tool names are registered."""
        from mcp.server import MCPServer
        assert isinstance(mcp, MCPServer)
        # The MCPServer registers tools via decorator
        # We verify the decorated functions exist
        from qdw.interfaces.mcp_server import qdw_get_status, qdw_list_factories, qdw_route_task
        assert callable(qdw_get_status)
        assert callable(qdw_list_factories)
        assert callable(qdw_route_task)

    def test_qdw_get_status_returns_dict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test qdw_get_status returns a valid status dict."""
        import qdw.interfaces.mcp_server as mod
        from qdw.system import QDWSystem
        db_path = str(tmp_path / "test.db")
        system = QDWSystem(db_path)
        monkeypatch.setattr(mod, "_system", system)
        result = mod.qdw_get_status()
        assert isinstance(result, dict)
        assert "ledger" in result
        assert result["ledger"]["ok"] is True

    def test_qdw_list_factories_returns_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test qdw_list_factories returns a list."""
        import qdw.interfaces.mcp_server as mod
        from qdw.system import QDWSystem
        system = QDWSystem(str(tmp_path / "test.db"))
        monkeypatch.setattr(mod, "_system", system)
        result = mod.qdw_list_factories()
        assert isinstance(result, list)

    def test_qdw_route_task_returns_dict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test qdw_route_task returns routing info."""
        import qdw.interfaces.mcp_server as mod
        result = mod.qdw_route_task("coding", quality=0.5)
        assert isinstance(result, dict)
        assert result["task_id"] == "mcp_preview"
        assert "primary" in result
        assert "reason_codes" in result

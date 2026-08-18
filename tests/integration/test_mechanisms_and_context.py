"""Tests for mechanism extraction and agent context mining."""

from pathlib import Path

import pytest

from qdw.review.mechanisms import Mechanism, extract_mechanisms
from qdw.review.agent_context import AgentContext, scan_agent_contexts, extract_practices


class TestMechanismExtraction:
    def test_extracts_event_sourcing_from_ledger(self, tmp_path: Path) -> None:
        """Event sourcing pattern detected in ledger code."""
        (tmp_path / "ledger.py").write_text(
            "class Ledger:\n"
            "    def append(self, event):\n"
            '        """Append-only event log with immutable events."""\n'
            "        self.events.append(event)\n"
            "        # hash chain for integrity\n"
        )
        mechs = extract_mechanisms(tmp_path)
        names = [m.name for m in mechs]
        assert "Event Sourcing" in names

    def test_extracts_cas_from_graph(self, tmp_path: Path) -> None:
        """CAS coordination detected in graph store."""
        (tmp_path / "store.py").write_text(
            "def claim(self, worker_id):\n"
            "    # atomic compare-and-swap\n"
            "    with self.db.tx(immediate=True) as con:\n"
            "        con.execute('UPDATE ... WHERE state=READY AND ...')\n"
        )
        mechs = extract_mechanisms(tmp_path)
        names = [m.name for m in mechs]
        assert "CAS Coordination" in names

    def test_extracts_cost_aware_routing(self, tmp_path: Path) -> None:
        """Cost-aware routing detected in router."""
        (tmp_path / "router.py").write_text(
            "def plan(self, task, routes):\n"
            "    # cost-aware routing with budget constraints\n"
            "    # routes sorted by expected_completion_cost\n"
        )
        mechs = extract_mechanisms(tmp_path)
        names = [m.name for m in mechs]
        assert "Cost-Aware Routing" in names

    def test_no_mechanisms_in_empty_dir(self, tmp_path: Path) -> None:
        mechs = extract_mechanisms(tmp_path)
        assert mechs == []

    def test_max_mechanisms_limit(self, tmp_path: Path) -> None:
        content = "differential oracle cross-check fault injection chaos " * 10
        (tmp_path / "test.py").write_text(content)
        mechs = extract_mechanisms(tmp_path, max_mechanisms=2)
        assert len(mechs) <= 2


class TestAgentContextMining:
    def test_detects_agents_md(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Agent Rules\n\nAlways test.\nNever skip.")
        contexts = scan_agent_contexts(tmp_path)
        assert len(contexts) == 1
        assert contexts[0].context_type == "agents_md"

    def test_detects_claude_md(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# Claude Rules\nUse ruff for linting.")
        contexts = scan_agent_contexts(tmp_path)
        assert len(contexts) == 1
        assert contexts[0].context_type == "claude_md"

    def test_extracts_practices(self) -> None:
        content = "Always run tests. Never skip linting. Commit with conventional commits."
        practices = extract_practices(content)
        assert "testing" in practices
        assert "code_quality" in practices
        assert "git_workflow" in practices

    def test_no_context_in_empty_dir(self, tmp_path: Path) -> None:
        contexts = scan_agent_contexts(tmp_path)
        assert contexts == []

    def test_context_has_hash(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Rules")
        contexts = scan_agent_contexts(tmp_path)
        assert len(contexts) == 1
        assert len(contexts[0].content_hash) == 64

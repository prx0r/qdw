"""Tests for AgentHub — architecture resolver, fault injection."""

from qdw.agenthub.failures import FaultResult, aggregate_faults
from qdw.agenthub.resolver import architecture_fit, resolve_architecture
from qdw.agenthub.types import AgentSystem, ArchitectureCapabilities, ArchitectureNeed


class TestResolver:
    def _hermes_system(self) -> AgentSystem:
        return AgentSystem(
            system_id="hermes",
            runtime="hermes",
            families=["coding", "research"],
            capabilities=ArchitectureCapabilities(
                persistent_state=True,
                independent_verification=True,
                resumable=True,
                tool_use=True,
                max_parallelism=4,
            ),
            topology_fit=0.9,
            state_fit=0.85,
            verification_fit=0.8,
            runtime_fit=1.0,
            benchmark_fit=0.7,
            economics_fit=0.6,
        )

    def test_hermes_fits_coding_need(self) -> None:
        need = ArchitectureNeed(
            need_id="n1",
            tool_use=True,
            independent_verification=True,
        )
        score, reasons = architecture_fit(need, self._hermes_system())
        assert score > 0.6
        assert reasons == []

    def test_missing_tool_use_rejected(self) -> None:
        need = ArchitectureNeed(need_id="n1", tool_use=True)
        system = AgentSystem(
            system_id="basic", runtime="local", families=["coding"],
            capabilities=ArchitectureCapabilities(tool_use=False),
        )
        score, reasons = architecture_fit(need, system)
        assert score == 0.0
        assert "tool_use:ABSENT" in reasons

    def test_unknown_parallelism_rejected(self) -> None:
        need = ArchitectureNeed(need_id="n1", parallelism=2)
        system = AgentSystem(
            system_id="single", runtime="local", families=["coding"],
            capabilities=ArchitectureCapabilities(),
        )
        score, reasons = architecture_fit(need, system)
        assert score == 0.0
        assert "parallelism:UNKNOWN" in reasons

    def test_resolve_picks_best(self) -> None:
        need = ArchitectureNeed(need_id="n1", tool_use=True)
        hermes = self._hermes_system()
        basic = AgentSystem(
            system_id="basic", runtime="local", families=["coding"],
            capabilities=ArchitectureCapabilities(tool_use=True),
        )
        result = resolve_architecture(need, [hermes, basic])
        assert result["best"]["system_id"] == "hermes"
        assert result["decision"] in {"REUSE", "FORK_OR_COMPOSE"}

    def test_resolve_synthesize_when_none_fit(self) -> None:
        need = ArchitectureNeed(need_id="n1", tool_use=True, parallelism=8)
        basic = AgentSystem(
            system_id="basic", runtime="local", families=["coding"],
            capabilities=ArchitectureCapabilities(tool_use=True),
        )
        result = resolve_architecture(need, [basic])
        assert result["decision"] == "SYNTHESIZE_EXPERIMENTAL_BUILD"
        assert result["best"] is None


class TestFailures:
    def test_aggregate_empty(self) -> None:
        result = aggregate_faults([])
        assert result["detection_rate"] == 0

    def test_aggregate_all_detected(self) -> None:
        results = [
            FaultResult("n1", True, True, 1, 10),
            FaultResult("n2", True, False, 3, 10),
        ]
        agg = aggregate_faults(results)
        assert agg["detection_rate"] == 1.0
        assert agg["recovery_rate"] == 0.5
        assert agg["mean_cascade_radius"] == 0.2

    def test_cascade_radius(self) -> None:
        r = FaultResult("n1", True, True, 5, 10)
        assert r.cascade_radius == 0.5

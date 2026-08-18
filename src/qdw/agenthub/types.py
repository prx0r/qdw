"""AgentHub types — architecture needs, capabilities, agent systems."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArchitectureNeed:
    need_id: str
    persistent_state: bool = False
    independent_verification: bool = False
    resumable: bool = False
    tool_use: bool = False
    parallelism: int = 1
    long_horizon: bool = False
    max_cost: float | None = None


@dataclass(frozen=True)
class ArchitectureCapabilities:
    persistent_state: bool | None = None
    independent_verification: bool | None = None
    resumable: bool | None = None
    tool_use: bool | None = None
    max_parallelism: int | None = None


@dataclass
class AgentSystem:
    system_id: str
    runtime: str
    families: list[str]
    capabilities: ArchitectureCapabilities
    benchmark_fit: float = 0.0
    economics_fit: float = 0.0
    topology_fit: float = 0.0
    state_fit: float = 0.0
    verification_fit: float = 0.0
    runtime_fit: float = 1.0


@dataclass(frozen=True)
class ModelSlot:
    slot_id: str
    task_kind: str
    quality_floor: float
    free_policy: str = "prefer"
    tools_required: bool = False


@dataclass
class Node:
    node_id: str
    role: str
    model_slot: str | None = None
    duration: float = 1.0
    token_cost: float = 1.0


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str = "dependency"
    retention: float = 1.0


@dataclass
class Architecture:
    architecture_id: str
    nodes: list[Node]
    edges: list[Edge]
    model_slots: list[ModelSlot] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    parent_ids: list[str] = field(default_factory=list)
    mutations: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class AssessmentVector:
    success_lower: float
    cost_per_success: float
    wall_time: float
    recovery_rate: float
    complexity: float


@dataclass(frozen=True)
class PromotionEvidence:
    distinct_tasks: int
    task_categories: int
    repetitions_per_key_task: int
    passed_target_suite: bool
    beats_simple_baseline: bool
    reproducible: bool
    ablation_supports_claim: bool
    zero_tolerance_failure: bool = False
    narrow_domain: bool = False

"""HotSwap types — TaskSpec, Route, Posterior, CandidateAssessment, ExecutionPlan."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_kind: str
    difficulty: str = "medium"
    criticality: str = "routine"
    quality_floor: float = 0.70
    free_policy: str = "prefer"
    paid_allowed: bool = True
    context_tokens_min: int = 0
    tools_required: bool = False
    json_required: bool = False
    estimated_input_tokens: int = 1000
    estimated_output_tokens: int = 500
    task_budget_usd: float | None = None
    exploration_allowed: bool = True

    @property
    def cell_id(self) -> str:
        return "|".join([
            self.task_kind,
            self.difficulty,
            self.criticality,
            "tools" if self.tools_required else "no-tools",
            _context_bin(self.context_tokens_min),
        ])


def _context_bin(n: int) -> str:
    if n <= 16000:
        return "ctx16k"
    if n <= 64000:
        return "ctx64k"
    if n <= 128000:
        return "ctx128k"
    return "ctx128k+"


@dataclass
class Route:
    route_id: str
    model_id: str
    provider_id: str
    endpoint_id: str | None = None
    account_id: str | None = None
    active: bool = True
    free: bool = False
    fixed_request_cost_usd: float | None = None
    input_per_m: float | None = None
    output_per_m: float | None = None
    context_tokens: int | None = None
    tools_supported: bool | None = None
    json_supported: bool | None = None
    reliability: float | None = None
    latency_ms: float | None = None
    prior_success: float | None = None
    prior_confidence: float = 0.0
    breaker_open: bool = False
    quota_pressure: float = 0.0
    cheapest_paid_replacement_cost: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)

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


@dataclass(frozen=True)
class Posterior:
    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


@dataclass
class CandidateAssessment:
    route: Route
    p_success: float
    p_lower: float
    request_cost: float
    quota_shadow_cost: float
    expected_completion_cost: float
    excluded: list[str] = field(default_factory=list)
    exploration_sample: float | None = None


@dataclass
class ExecutionPlan:
    task_id: str
    primary: CandidateAssessment | None
    fallbacks: list[CandidateAssessment]
    excluded: dict[str, list[str]]
    reason_codes: list[str]

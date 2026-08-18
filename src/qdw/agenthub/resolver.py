"""AgentHub resolver — weighted architecture fit scoring."""

from __future__ import annotations

from qdw.agenthub.types import AgentSystem, ArchitectureNeed

WEIGHTS = {
    "capability_fit": 0.25,
    "topology_fit": 0.20,
    "state_fit": 0.15,
    "verification_fit": 0.15,
    "runtime_fit": 0.10,
    "benchmark_fit": 0.10,
    "economics_fit": 0.05,
}


def _bool_requirement(required: bool, observed):
    if not required:
        return 1.0, None
    if observed is None:
        return 0.0, "UNKNOWN"
    return (1.0, None) if observed else (0.0, "ABSENT")


def architecture_fit(need: ArchitectureNeed, system: AgentSystem) -> tuple[float, list[str]]:
    c = system.capabilities
    hard = []
    pieces = []

    for name, req, obs in [
        ("persistent_state", need.persistent_state, c.persistent_state),
        ("independent_verification", need.independent_verification, c.independent_verification),
        ("resumable", need.resumable, c.resumable),
        ("tool_use", need.tool_use, c.tool_use),
    ]:
        score, state = _bool_requirement(req, obs)
        pieces.append(score)
        if req and state:
            hard.append(f"{name}:{state}")

    if need.parallelism > 1:
        if c.max_parallelism is None:
            hard.append("parallelism:UNKNOWN")
            pieces.append(0)
        elif c.max_parallelism < need.parallelism:
            hard.append("parallelism:INSUFFICIENT")
            pieces.append(0)
        else:
            pieces.append(1)

    capability_fit = sum(pieces) / max(1, len(pieces))
    if hard:
        return 0.0, hard

    score = (
        WEIGHTS["capability_fit"] * capability_fit
        + WEIGHTS["topology_fit"] * system.topology_fit
        + WEIGHTS["state_fit"] * system.state_fit
        + WEIGHTS["verification_fit"] * system.verification_fit
        + WEIGHTS["runtime_fit"] * system.runtime_fit
        + WEIGHTS["benchmark_fit"] * system.benchmark_fit
        + WEIGHTS["economics_fit"] * system.economics_fit
    )
    return round(score, 4), []


def resolve_architecture(need: ArchitectureNeed, systems: list[AgentSystem]):
    scored = []
    excluded = {}
    for s in systems:
        score, reasons = architecture_fit(need, s)
        if reasons:
            excluded[s.system_id] = reasons
        else:
            scored.append((score, s.system_id))
    scored.sort(reverse=True)

    if not scored:
        return {"decision": "SYNTHESIZE_EXPERIMENTAL_BUILD", "best": None, "excluded": excluded}

    best_score, best_id = scored[0]
    if best_score >= 0.78:
        decision = "REUSE"
    elif best_score >= 0.62:
        decision = "FORK_OR_COMPOSE"
    else:
        decision = "SYNTHESIZE_EXPERIMENTAL_BUILD"
    return {
        "decision": decision,
        "best": {"system_id": best_id, "fit": best_score},
        "alternatives": [{"system_id": sid, "fit": score} for score, sid in scored[1:5]],
        "excluded": excluded,
    }

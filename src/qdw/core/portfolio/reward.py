"""Outcome metrics — bounded utility calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutcomeMetrics:
    revenue_usd: float = 0
    variable_cost_usd: float = 0
    active_users: float = 0
    successful_calls: float = 0
    retained_users: float = 0
    quality: float = 0
    strategic_utility: float = 0
    data_gain: float = 0


def contribution_margin(m: OutcomeMetrics) -> float:
    return m.revenue_usd - m.variable_cost_usd


def bounded_utility(m: OutcomeMetrics) -> float:
    margin = max(-1.0, min(1.0, contribution_margin(m) / 100.0))
    usage = max(0.0, min(1.0, m.successful_calls / 1000.0))
    retention = max(0.0, min(1.0, m.retained_users / max(1.0, m.active_users)))
    quality = max(0.0, min(1.0, m.quality))
    strategic = max(0.0, min(1.0, m.strategic_utility))
    data = max(0.0, min(1.0, m.data_gain))
    return 0.30 * margin + 0.20 * usage + 0.15 * retention + 0.15 * quality + 0.10 * strategic + 0.10 * data

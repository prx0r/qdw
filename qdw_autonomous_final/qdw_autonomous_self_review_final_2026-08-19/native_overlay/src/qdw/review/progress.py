from __future__ import annotations

def stop_reason(*,previous_blockers,current_blockers,round_no,max_rounds,
                total_cost_usd,max_cost_usd):
    if not current_blockers:
        return None
    if previous_blockers is not None and tuple(previous_blockers)==tuple(current_blockers):
        return "NO_PROGRESS"
    if round_no>=max_rounds:
        return "MAX_ROUNDS"
    if max_cost_usd is not None and total_cost_usd>=max_cost_usd:
        return "BUDGET_EXHAUSTED"
    return None

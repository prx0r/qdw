"""Functions to expose through QDW's existing MCP server.

Wire these through QDWSystem.review; do not construct a second QDWSystem.
"""

def qdw_peer_review(system, profile:str="quick"):
    return system.review.start_current_checkout(profile=profile)

def qdw_review_status(system, review_run_id:str):
    return system.review.get(review_run_id)

def qdw_review_findings(system, review_run_id:str, min_severity:str="INFO"):
    return system.review.findings(review_run_id,min_severity=min_severity)

def qdw_red_team(system, review_run_id:str):
    return system.review.run_formula(review_run_id,"review.redteam")

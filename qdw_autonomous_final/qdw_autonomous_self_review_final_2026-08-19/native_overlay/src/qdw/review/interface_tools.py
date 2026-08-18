"""Thin API/MCP-callable functions.

Register these in the existing FastAPI/MCP modules; do not instantiate a second QDWSystem.
"""
from __future__ import annotations

def review_start(system,profile:str="change-aware"):
    # API/MCP adapter should call the same CLI/service helper logic with an authenticated request context.
    return {"supported":True,"profile":profile,
            "instruction":"resolve exact Git subject then call system.review_controller"}

def review_status(system,review_run_id:str):
    return system.review.report(review_run_id)

def review_findings(system,review_run_id:str,min_severity:str="INFO"):
    from .models import Severity
    return system.review.store.open_findings(review_run_id,Severity.parse(min_severity))

def review_pack(system,review_run_id:str,output_path:str):
    return system.review.export_pack(review_run_id,output_path)

from __future__ import annotations
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from qdw.hotswap.types import TaskSpec
from qdw.federation.http_clients import FederationHTTPError
from qdw.federation.runtime import FederationAttemptConflict

router=APIRouter(prefix="/v1/federation",tags=["federation"])

def system():
    from qdw.interfaces.api import _get_system
    return _get_system()

class RefreshBody(BaseModel):
    capability:str
    workload:dict=Field(default_factory=dict)
    max_cost_usd:float|None=None

class ExecuteBody(BaseModel):
    attempt_id:str
    capability:str
    arguments:dict=Field(default_factory=dict)
    max_spend_usd:float|None=None
    task_kind:str|None=None
    quality_floor:float=0.7
    work_node_id:str|None=None
    factory_run_id:str|None=None
    debug_stop_after:str|None=None

class ResumeBody(BaseModel):
    attempt_id:str

def task(body:ExecuteBody):
    return TaskSpec(
      task_id=body.attempt_id,task_kind=body.task_kind or body.capability,
      quality_floor=body.quality_floor,task_budget_usd=body.max_spend_usd)

def _error(exc):
    if isinstance(exc,FederationAttemptConflict):raise HTTPException(409,str(exc))
    if isinstance(exc,FederationHTTPError):
        code=503 if exc.status=="UNAVAILABLE" else 403 if exc.status=="UNAUTHORIZED" else 502
        raise HTTPException(code,str(exc))
    raise exc

@router.get("/protocol")
def protocol():
    return {
      "version":"qdw-federation-runtime/2",
      "terminal_success_states":["COMMITTED"],
      "attempt_states":["DISCOVERING","CANDIDATES_READY","ROUTED","RUNNING",
                        "SUCCEEDED_UNVERIFIED","VERIFYING","VERIFIED","COMMITTED","FAILED"],
      "authority":{"workgraph":"qdw","final_route":"qdw","verification":"qdw"},
    }

@router.post("/sync/gitgoblin")
def sync_gitgoblin():
    s=system()
    try:
        out=s.federation.sync_gitgoblin({})
        snap_id=out["snapshot_id"]
        with s.db.connect() as con:r=con.execute("SELECT * FROM external_snapshots WHERE snapshot_id=?",(snap_id,)).fetchone()
        return {**out,"status":r["external_status"] if r else "FAILED"}
    except Exception as e:_error(e)

@router.post("/refresh")
def refresh(body:RefreshBody):
    s=system()
    t=TaskSpec(task_id="refresh",task_kind=body.workload.get("task",body.capability),
               estimated_input_tokens=int(body.workload.get("input_tokens_per_request",1000)),
               estimated_output_tokens=int(body.workload.get("output_tokens_per_request",500)),
               task_budget_usd=body.max_cost_usd)
    try:
        x=s.federation_runtime.refresh_candidates(capability=body.capability,task=t)
        return {"dell":{"authority":"ADVISORY","snapshot":x["dell_snapshot"].response_digest},
                "route_count":len(x["route_ids"]),"route_ids":x["route_ids"]}
    except Exception as e:_error(e)

@router.post("/execute")
def execute(body:ExecuteBody):
    import os
    if body.debug_stop_after and os.environ.get("QDW_FEDERATION_LAB_MODE")!="1":
        raise HTTPException(403,"debug_stop_after is available only in federation lab mode")
    s=system()
    try:
        return s.federation_runtime.execute(
          attempt_id=body.attempt_id,capability=body.capability,arguments=body.arguments,
          task=task(body),work_node_id=body.work_node_id,factory_run_id=body.factory_run_id,
          verification_cwd=s.repo_root,stop_after=body.debug_stop_after)
    except Exception as e:_error(e)

@router.post("/resume")
def resume(body:ResumeBody):
    s=system()
    row=s.federation_runtime._attempt(body.attempt_id)
    if not row:raise HTTPException(404,"attempt not found")
    req=__import__("json").loads(row["request_json"])
    t=TaskSpec(**req["task"])
    try:
        return s.federation_runtime.execute(
          attempt_id=body.attempt_id,capability=req["capability"],arguments=req["arguments"],task=t,
          work_node_id=req.get("work_node_id"),factory_run_id=req.get("factory_run_id"),
          verification_cwd=s.repo_root)
    except Exception as e:_error(e)

@router.get("/attempts/{attempt_id}")
def attempt(attempt_id:str):
    try:return system().federation_runtime.result(attempt_id)
    except KeyError:raise HTTPException(404,"attempt not found")

@router.get("/certificates/{certificate_id}")
def certificate(certificate_id:str):
    try:return system().federation_certificates.get(certificate_id)
    except KeyError:raise HTTPException(404,"certificate not found")

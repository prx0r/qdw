"""QDW API — FastAPI with real health checks, typed errors.

BROKEN DATABASE != ZERO OPPORTUNITIES.
All business logic delegates to QDWSystem.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

_DB = "data/qdw.db"
_system = None


def _get_system():
    global _system
    if _system is None:
        from qdw.system import QDWSystem
        _system = QDWSystem(_DB)
    return _system


class HealthResponse(BaseModel):
    status: str
    ledger_ok: bool
    db_tables: int
    route_count: int
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_system()
    yield


app = FastAPI(title="QDW API", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    system = _get_system()
    doctor = system.doctor()
    if not doctor["ok"]:
        raise HTTPException(status_code=503, detail="ledger verification failed")
    return HealthResponse(
        status="ok",
        ledger_ok=doctor["ledger"]["ok"],
        db_tables=len(doctor["tables"]),
        route_count=doctor["route_count"],
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/graph/{graph_id}")
def get_graph(graph_id: str) -> dict[str, Any]:
    system = _get_system()
    with system.db.connect() as con:
        graph = con.execute(
            "SELECT * FROM work_graphs WHERE graph_id=?", (graph_id,)
        ).fetchone()
        if not graph:
            raise HTTPException(status_code=404, detail=f"graph {graph_id} not found")
        nodes = [dict(r) for r in con.execute(
            "SELECT * FROM work_nodes WHERE graph_id=? ORDER BY priority DESC", (graph_id,)
        ).fetchall()]
        return {"graph": dict(graph), "nodes": nodes}


@app.get("/factories")
def list_factories() -> list[dict[str, Any]]:
    system = _get_system()
    return system.factories.list()


@app.post("/route")
def route_task(body: dict[str, Any]) -> dict[str, Any]:
    system = _get_system()
    # Register routes from request if provided
    from qdw.hotswap.types import Route
    for r in body.get("routes", []):
        system.register_route(Route(
            route_id=r.get("route_id", "default"),
            model_id=r.get("model_id", "unknown"),
            provider_id=r.get("provider_id", "unknown"),
            free=r.get("free", False),
            input_per_m=r.get("input_per_m"),
            output_per_m=r.get("output_per_m"),
        ))
    return system.route_task(
        body.get("task_kind", "coding"),
        {"quality": body.get("quality", 0.8), "task_id": body.get("task_id", "api_preview")},
    )

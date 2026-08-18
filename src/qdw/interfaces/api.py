"""QDW API — FastAPI with real health checks, typed errors.

BROKEN DATABASE != ZERO OPPORTUNITIES.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

_DB = "data/qdw.db"


class HealthResponse(BaseModel):
    status: str
    ledger_ok: bool
    db_tables: int
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    from qdw.core.db import Database
    db = Database(_DB)
    db.migrate()
    yield


app = FastAPI(title="QDW API", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from qdw.core.db import Database
    db = Database(_DB)
    try:
        with db.connect() as con:
            tables = con.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from None

    from qdw.core.ledger.events import Ledger
    ledger = Ledger(db)
    ok, bad_seq, reason = ledger.verify_chain()

    return HealthResponse(
        status="ok" if ok else "degraded",
        ledger_ok=ok,
        db_tables=tables,
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/graph/{graph_id}")
def get_graph(graph_id: str) -> dict[str, Any]:
    from qdw.core.db import Database
    db = Database(_DB)
    with db.connect() as con:
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
    from qdw.core.db import Database
    db = Database(_DB)
    with db.connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT factory_id, version, status FROM factory_definitions ORDER BY factory_id"
        ).fetchall()]


@app.post("/route")
def route_task(body: dict[str, Any]) -> dict[str, Any]:
    from qdw.hotswap.router import HotSwapRouter
    from qdw.hotswap.types import Route, TaskSpec

    task_kind = body.get("task_kind", "coding")
    quality = body.get("quality", 0.8)
    task = TaskSpec(
        task_id=body.get("task_id", "preview"),
        task_kind=task_kind,
        quality_floor=float(quality),
    )
    routes = [
        Route(
            route_id=r.get("route_id", "default"),
            model_id=r.get("model_id", "unknown"),
            provider_id=r.get("provider_id", "unknown"),
            free=r.get("free", False),
            input_per_m=r.get("input_per_m"),
            output_per_m=r.get("output_per_m"),
        )
        for r in body.get("routes", [])
    ]
    plan = HotSwapRouter().plan(task, routes)

    def _candidate(x):
        if x is None:
            return None
        return {
            "route_id": x.route.route_id,
            "model_id": x.route.model_id,
            "p_success": x.p_success,
            "expected_completion_cost": x.expected_completion_cost,
        }

    return {
        "task_id": task.task_id,
        "primary": _candidate(plan.primary),
        "fallbacks": [_candidate(x) for x in plan.fallbacks],
        "reason_codes": plan.reason_codes,
    }

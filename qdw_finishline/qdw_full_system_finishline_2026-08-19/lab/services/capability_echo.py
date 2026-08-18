from __future__ import annotations
import os
from fastapi import FastAPI,Response

app=FastAPI(title="Forge capability fixture")
@app.get("/health")
def health():return {"status":"ok"}

@app.post("/invoke")
def invoke(body:dict,response:Response):
    response.headers["x-qdw-cost-usd"]=os.environ.get("FIXTURE_ACTUAL_COST","0.001")
    return {"echo":body}

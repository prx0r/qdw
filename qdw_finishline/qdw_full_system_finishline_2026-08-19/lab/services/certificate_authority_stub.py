from __future__ import annotations
from fastapi import FastAPI,HTTPException
CERTS={}
app=FastAPI(title="QDW certificate resolver fixture")

@app.get("/health")
def health():return {"status":"ok"}

@app.post("/certificates")
def add(body:dict):
    cid=body["certificate_id"];CERTS[cid]=body;return body

@app.get("/certificates/{certificate_id}")
def get(certificate_id:str):
    if certificate_id not in CERTS:raise HTTPException(404)
    return CERTS[certificate_id]

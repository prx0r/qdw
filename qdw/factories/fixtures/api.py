"""Real offline API factory fixture.

Produces a real FastAPI artifact, boots a real Uvicorn process on localhost, calls /health, and hashes
the generated tree. The broken fixture is checked by the same verifier.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json,socket,subprocess,sys,time
from urllib.error import URLError,HTTPError
from urllib.request import urlopen

@dataclass(frozen=True)
class APIFixtureResult:
    passed:bool
    status_code:int|None
    body:str
    artifact_hash:str
    files:tuple[str,...]
    reason_code:str

def _port()->int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]

def _tree_hash(root:Path)->str:
    h=sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        h.update(str(p.relative_to(root)).encode()+b"\0")
        h.update(sha256(p.read_bytes()).digest())
    return h.hexdigest()

class APIFactoryFixture:
    def generate(self,root:str|Path,*,broken:bool=False)->Path:
        root=Path(root)
        root.mkdir(parents=True,exist_ok=True)
        health = "" if broken else (
            '@app.get("/health")\n'
            'def health():\n'
            '    return {"ok": True}\n'
        )
        app = (
            'from fastapi import FastAPI\n'
            'app=FastAPI()\n'
            + health +
            '@app.get("/items")\n'
            'def items():\n'
            '    return {"items":[]}\n'
        )
        (root/"app.py").write_text(app,encoding="utf-8")
        (root/"fixture.json").write_text(json.dumps(
            {"kind":"api","expected_health":not broken},sort_keys=True
        ),encoding="utf-8")
        return root

    def verify(self,root:str|Path,*,timeout_seconds:float=10.0)->APIFixtureResult:
        root=Path(root)
        port=_port()
        proc=subprocess.Popen(
            [sys.executable,"-m","uvicorn","app:app","--host","127.0.0.1","--port",str(port)],
            cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        )
        status=None
        body=""
        reason="API_HEALTH_FAILED"
        passed=False
        deadline=time.monotonic()+timeout_seconds
        try:
            while time.monotonic()<deadline:
                if proc.poll() is not None:
                    break
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health",timeout=.5) as response:
                        status=response.status
                        body=response.read().decode()
                        if status==200:
                            payload=json.loads(body)
                            passed=payload.get("ok") is True
                            reason="OK" if passed else "API_HEALTH_BODY"
                            break
                except (URLError,HTTPError,TimeoutError,ConnectionError,json.JSONDecodeError):
                    time.sleep(.1)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        files=tuple(sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()))
        return APIFixtureResult(passed,status,body,_tree_hash(root),files,reason)

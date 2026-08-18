import json,socket,subprocess,time
from urllib.request import urlopen
import pytest

IMAGE="qdw:runtime-review"

def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        return sock.getsockname()[1]

def test_container_health_contract():
    subprocess.run(["docker","build","--no-cache","-t",IMAGE,"."],check=True)
    port=_free_port()
    name=f"qdw-runtime-{port}"
    subprocess.run([
        "docker","run","-d","--rm","--name",name,
        "-p",f"{port}:8000",IMAGE
    ],capture_output=True,text=True,check=True)
    try:
        deadline=time.monotonic()+30
        last=None
        while time.monotonic()<deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/health",timeout=1) as response:
                    body=response.read().decode()
                    last=(response.status,body)
                    if response.status==200:
                        payload=json.loads(body)
                        assert payload.get("status") in {"ok","healthy"} or payload.get("ok") is True
                        return
            except Exception as exc:
                last=repr(exc)
                time.sleep(.5)
        pytest.fail(f"container never became healthy: {last}")
    finally:
        subprocess.run(["docker","rm","-f",name],capture_output=True)

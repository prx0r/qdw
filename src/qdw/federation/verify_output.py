from __future__ import annotations
import json,sys
from pathlib import Path

def verify_fixture_echo(path:Path)->int:
    x=json.loads(path.read_text())
    if not isinstance(x,dict):return 2
    if "echo" not in x and not (x.get("ok") is True and "arguments" in x):return 3
    return 0

def main(argv=None)->int:
    a=list(argv or sys.argv[1:])
    if len(a)!=2:raise SystemExit("usage: verify_output <policy> <path>")
    policy,path=a
    if policy=="fixture.echo":return verify_fixture_echo(Path(path))
    raise SystemExit(f"unknown policy: {policy}")

if __name__=="__main__":raise SystemExit(main())

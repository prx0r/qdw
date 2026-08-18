from __future__ import annotations
import argparse,json
from pathlib import Path
from .authority import OWNERS,FORBIDDEN

def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="qdw-federation-doctor")
    p.add_argument("--pins",default="pins/REPOS.json")
    a=p.parse_args(argv)
    pins=json.loads(Path(a.pins).read_text())
    out={"pins":pins,"authority":OWNERS,"forbidden":[list(x) for x in sorted(FORBIDDEN)]}
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":raise SystemExit(main())

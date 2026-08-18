from __future__ import annotations
import argparse,json,os
from .system import VentureLabSystem

def main(argv=None):
    p=argparse.ArgumentParser("venturelab-os")
    p.add_argument("--db",default=os.environ.get("VENTURELAB_DB","data/venturelab-os.db"))
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("doctor");sub.add_parser("verify-ledger");sub.add_parser("list-factories")
    a=p.parse_args(argv);s=VentureLabSystem(a.db)
    if a.cmd=="doctor":
        d=s.doctor();print(json.dumps(d,indent=2));return 0 if d["ok"] else 1
    if a.cmd=="verify-ledger":
        ok,seq,reason=s.ledger.verify_chain()
        print(json.dumps({"ok":ok,"bad_seq":seq,"reason":reason},indent=2));return 0 if ok else 1
    if a.cmd=="list-factories":
        print(json.dumps(s.factories.list(),indent=2));return 0
    return 2

if __name__=="__main__":
    raise SystemExit(main())

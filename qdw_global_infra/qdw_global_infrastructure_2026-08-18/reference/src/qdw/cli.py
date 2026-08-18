from __future__ import annotations
import argparse,json,os
from pathlib import Path
from qdw.system import QDWSystem
from qdw.proof.test_guard import scan_test_tree

def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="qdw")
    p.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("doctor")
    sub.add_parser("cemetery")
    sub.add_parser("human-pending")
    sub.add_parser("ideas-unused")
    s=sub.add_parser("catalog");s.add_argument("query")
    t=sub.add_parser("test-guard");t.add_argument("path",default="tests",nargs="?")
    args=p.parse_args(argv)
    system=QDWSystem(args.db)
    if args.cmd=="doctor":
        d=system.doctor();print(json.dumps(d,indent=2));return 0 if d["ok"] else 1
    if args.cmd=="cemetery":
        print(json.dumps(system.ideas.cemetery(),indent=2));return 0
    if args.cmd=="human-pending":
        print(json.dumps(system.human.pending(),indent=2));return 0
    if args.cmd=="ideas-unused":
        print(json.dumps(system.idea_library.unused(),indent=2));return 0
    if args.cmd=="catalog":
        print(json.dumps(system.catalog.search(args.query),indent=2));return 0
    if args.cmd=="test-guard":
        findings=scan_test_tree(args.path)
        print(json.dumps([x.__dict__ for x in findings],indent=2))
        return 1 if findings else 0
    return 2

if __name__=="__main__":
    raise SystemExit(main())

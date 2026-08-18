from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from qdw_review.migration_lock import create_lock
from qdw_review.policy import evaluate,load_policy
from qdw_review.report_html import write_html
from qdw_review.sarif import to_sarif
from qdw_review.scanner import ReviewScanner

def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="qdw-review")
    sub=p.add_subparsers(dest="cmd",required=True)

    s=sub.add_parser("scan");s.add_argument("repo");s.add_argument("--profile",choices=["quick","full","release"],default="quick");s.add_argument("--out",default=".qdw/review")
    r=sub.add_parser("report");r.add_argument("json_report");r.add_argument("--html",required=True)
    g=sub.add_parser("gate");g.add_argument("json_report");g.add_argument("--policy",required=True)
    a=sub.add_parser("sarif");a.add_argument("json_report");a.add_argument("--out",required=True)
    l=sub.add_parser("lock-migrations");l.add_argument("repo");l.add_argument("--out",default=".qdw/review/migration_lock.json")
    sub.add_parser("modules")

    args=p.parse_args(argv)
    if args.cmd=="scan":
        report=ReviewScanner().scan(args.repo,profile=args.profile,out_dir=args.out)
        print(json.dumps(report.to_dict(),indent=2))
        return 1 if any(f.severity.name in {"CRITICAL","HIGH"} for f in report.findings) else 0
    if args.cmd=="report":
        d=json.loads(Path(args.json_report).read_text());write_html(d,args.html);return 0
    if args.cmd=="gate":
        d=json.loads(Path(args.json_report).read_text());res=evaluate(d,load_policy(args.policy));print(json.dumps(res,indent=2));return 0 if res["status"]=="PASS" else 1
    if args.cmd=="sarif":
        d=json.loads(Path(args.json_report).read_text());Path(args.out).write_text(json.dumps(to_sarif(d),indent=2));return 0
    if args.cmd=="lock-migrations":
        print(json.dumps(create_lock(args.repo,args.out),indent=2));return 0
    if args.cmd=="modules":
        for c in ReviewScanner().checks:print(c.module_id,c.version)
        return 0
    return 2

if __name__=="__main__":raise SystemExit(main())

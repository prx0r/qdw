from __future__ import annotations
import argparse,json
from pathlib import Path
from .scanner import StaticScanner
from .fix_plan import build_fix_tasks,to_dict
from .report import write_outputs
from .pack import ReviewPackBuilder

def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="qdw-review")
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("scan");s.add_argument("repo");s.add_argument("--out",default=".qdw/review");s.add_argument("--profile",default="quick");s.add_argument("--base")
    r=sub.add_parser("report");r.add_argument("review_json");r.add_argument("--html",required=True);r.add_argument("--sarif",required=True)
    pk=sub.add_parser("pack");pk.add_argument("review_json");pk.add_argument("--out",required=True)
    sub.add_parser("modules")

    a=p.parse_args(argv)
    if a.cmd=="scan":
        report=StaticScanner().scan(a.repo,a.profile,a.base)
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        d=report.to_dict()
        write_outputs(d,out/"REVIEW.json",out/"REPORT.html",out/"REVIEW.sarif")
        (out/"FIX_PLAN.json").write_text(json.dumps(to_dict(build_fix_tasks(report.findings)),indent=2))
        print(json.dumps({"counts":report.counts(),"blockers":report.blocker_fingerprints()},indent=2))
        return 1 if report.blocker_fingerprints() else 0
    if a.cmd=="report":
        d=json.loads(Path(a.review_json).read_text())
        write_outputs(d,a.review_json,a.html,a.sarif)
        return 0
    if a.cmd=="pack":
        d=json.loads(Path(a.review_json).read_text())
        result=ReviewPackBuilder().build(report=d,fix_tasks=[],acceptance_specs=[],
            attack_results=d.get("attacks",[]),reviewer_outputs=[],receipts=d.get("receipts",[]),
            certificates=[],output_zip=a.out)
        print(json.dumps(result,indent=2));return 0
    if a.cmd=="modules":
        for c in StaticScanner().checks:print(c.module_id,c.version)
        return 0
    return 2

if __name__=="__main__":
    raise SystemExit(main())

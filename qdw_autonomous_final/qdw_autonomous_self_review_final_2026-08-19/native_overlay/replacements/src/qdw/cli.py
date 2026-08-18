from __future__ import annotations
import argparse,json,os,shlex
from pathlib import Path

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.proof.plan import VerificationPlan
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2
from qdw.review.static_export import write_static_report

def _verification(db_path,runs_dir):
    db=Database(db_path);db.migrate()
    return VerificationService(db,Ledger(db),runs_dir)

def main(argv=None)->int:
    parser=argparse.ArgumentParser(prog="qdw")
    sub=parser.add_subparsers(dest="cmd",required=True)

    vp=sub.add_parser("verify-plan")
    vp.add_argument("plan")
    vp.add_argument("--task",default="MANUAL")
    vp.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))
    vp.add_argument("--runs-dir",default=".qdw/verification")
    vp.add_argument("--allow-dirty",action="store_true")

    bc=sub.add_parser("build-certificate")
    bc.add_argument("run_id")
    bc.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))
    bc.add_argument("--runs-dir",default=".qdw/verification")
    bc.add_argument("--out",default="BUILD_CERTIFICATE.json")

    rs=sub.add_parser("review-static")
    rs.add_argument("--profile",default="quick")
    rs.add_argument("--out",default=".qdw/review/static")

    status=sub.add_parser("status")
    status.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))

    # Legacy compatibility: still process-backed, but explicitly labeled compatibility only.
    legacy=sub.add_parser("verify")
    legacy.add_argument("task_id")
    legacy.add_argument("command")
    legacy.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))
    legacy.add_argument("--runs-dir",default=".qdw/verification")

    args=parser.parse_args(argv)

    if args.cmd=="verify-plan":
        service=_verification(args.db,args.runs_dir)
        plan=VerificationPlan.load(args.plan)
        run_id=service.execute(plan,task_id=args.task,cwd=".",require_clean=not args.allow_dirty)
        ok,reason=service.verify_evidence(run_id)
        print(json.dumps({"verification_run_id":run_id,"status":"PASS" if ok else "FAIL","reason":reason},indent=2))
        return 0 if ok else 1

    if args.cmd=="build-certificate":
        service=_verification(args.db,args.runs_dir)
        cert=BuildCertificateV2(service).issue(args.run_id)
        Path(args.out).write_text(json.dumps(cert,indent=2),encoding="utf-8")
        ok,reason=BuildCertificateV2(service).verify(cert["build_certificate_id"])
        print(json.dumps({"status":"PASS" if ok else "FAIL","reason":reason,
                          "build_certificate_id":cert["build_certificate_id"]},indent=2))
        return 0 if ok else 1

    if args.cmd=="review-static":
        report=write_static_report(".",args.profile,args.out)
        blockers=report["counts"]["CRITICAL"]+report["counts"]["HIGH"]
        print(json.dumps({"counts":report["counts"],"blockers":blockers},indent=2))
        return 1 if blockers else 0

    if args.cmd=="status":
        db=Database(args.db);db.migrate();ledger=Ledger(db)
        ok,seq,reason=ledger.verify_chain()
        print(json.dumps({"ok":ok,"ledger":{"bad_seq":seq,"reason":reason}},indent=2))
        return 0 if ok else 1

    if args.cmd=="verify":
        service=_verification(args.db,args.runs_dir)
        from qdw.proof.plan import VerificationCommand
        plan=VerificationPlan(
            plan_id="legacy-single-command",version="1",
            commands=(VerificationCommand("legacy",tuple(shlex.split(args.command))),),
        )
        run_id=service.execute(plan,task_id=args.task_id,cwd=".",require_clean=False)
        ok,reason=service.verify_evidence(run_id)
        print(json.dumps({"verification_run_id":run_id,"status":"PASS" if ok else "FAIL","reason":reason}))
        return 0 if ok else 1

    return 2

if __name__=="__main__":
    raise SystemExit(main())

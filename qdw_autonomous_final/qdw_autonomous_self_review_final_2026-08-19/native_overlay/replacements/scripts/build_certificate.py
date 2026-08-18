#!/usr/bin/env python3
"""Issue BuildCertificate v2 from one explicit VerificationRun.

There is no "latest receipt", majority task ID, or inferred required command behavior.
"""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--run-id",required=True)
    p.add_argument("--db",default=os.environ.get("QDW_DB",".qdw/qdw.db"))
    p.add_argument("--runs-dir",default=".qdw/verification")
    p.add_argument("--out",default="BUILD_CERTIFICATE.json")
    args=p.parse_args()

    db=Database(args.db);db.migrate()
    service=VerificationService(db,Ledger(db),args.runs_dir)
    cert=BuildCertificateV2(service).issue(args.run_id)
    Path(args.out).write_text(json.dumps(cert,indent=2),encoding="utf-8")
    ok,reason=BuildCertificateV2(service).verify(cert["build_certificate_id"])
    if not ok:
        print(f"certificate self-verification failed: {reason}")
        return 1
    print(json.dumps({
        "status":"PROVEN","build_certificate_id":cert["build_certificate_id"],
        "subject_git_sha":cert["subject_git_sha"],"plan_hash":cert["plan_hash"],
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Canonical local/CI release evidence runner."""
from __future__ import annotations
import json,os
from pathlib import Path
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.proof.plan import VerificationPlan
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2

def main()->int:
    root=Path(".").resolve()
    ci=root/".qdw/ci";ci.mkdir(parents=True,exist_ok=True)
    db=Database(ci/"qdw-ci.db");db.migrate()
    service=VerificationService(db,Ledger(db),ci/"verification")
    plan=VerificationPlan.load(root/"acceptance/plans/qdw-release-v2.json")
    run_id=service.execute(plan,task_id="CI-RELEASE",cwd=root,require_clean=True)
    ok,reason=service.verify_evidence(run_id)
    (ci/"verification_run_id.txt").write_text(run_id,encoding="utf-8")
    if not ok:
        print(f"verification failed: {reason}")
        return 1
    cert=BuildCertificateV2(service).issue(run_id)
    (root/"BUILD_CERTIFICATE.json").write_text(json.dumps(cert,indent=2),encoding="utf-8")
    ok,reason=BuildCertificateV2(service).verify(cert["build_certificate_id"])
    if not ok:
        print(f"certificate verification failed: {reason}")
        return 1
    print(json.dumps({
        "status":"PROVEN","verification_run_id":run_id,
        "build_certificate_id":cert["build_certificate_id"],
        "subject_git_sha":cert["subject_git_sha"],
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

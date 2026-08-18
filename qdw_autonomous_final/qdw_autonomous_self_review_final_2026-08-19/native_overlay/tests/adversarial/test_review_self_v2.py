import json,zipfile
import pytest

from qdw.review.models import (
    ReviewPolicy,ReviewRequest,ReviewerFinding,ReviewerResult,Severity
)
from qdw.review.store import ReviewStore
from qdw.review.certificate import ReviewCertificateService
from qdw.review.acceptance import AcceptanceRunner
from qdw.review.progress import stop_reason
from qdw.review.report import ReviewReportService
from qdw.review.pack import NativeReviewPackBuilder,verify_pack

def _request(producer="producer"):
    policy=ReviewPolicy(
        "test-policy","policy-hash",Severity.HIGH,(),(),2,1.0,False,False,True
    )
    return ReviewRequest("sha",False,None,(),"test","quick",policy,producer),policy

def test_reviewer_cannot_self_certify(db,ledger):
    store=ReviewStore(db,ledger)
    req,policy=_request("same-worker")
    rid=store.create_run(req)
    service=ReviewCertificateService(store)
    with pytest.raises(ValueError,match="producer"):
        service.issue(rid,policy,certifier_worker_id="same-worker")

def test_acceptance_mutation_detected(db,ledger,tmp_path):
    store=ReviewStore(db,ledger)
    req,policy=_request()
    rid=store.create_run(req)
    round_id=store.start_round(rid,"sha","reviewers","attacks")
    mid=store.create_module_run(round_id,"review.test","1","definition")
    finding=ReviewerFinding(
        rule_id="X",severity="HIGH",title="x",summary="x",invariant="must hold",
        remediation="fix it",evidence=(),
        acceptance_tests=("frozen",),
        acceptance_specs=({
            "kind":"inline_pytest","id":"x","filename":"test_x.py",
            "content":"def test_x():\\n    assert 1 == 1\\n",
        },),
        confidence=1.0,
    )
    ids=store.ingest_result(
        rid,round_id,mid,ReviewerResult("review.test","1","ok",(finding,)),"sha"
    )
    fid=ids[0]
    with db.tx(immediate=True) as con:
        row=con.execute("""SELECT a.acceptance_spec_id FROM review_acceptance_specs a
            JOIN review_finding_acceptance fa ON fa.acceptance_spec_id=a.acceptance_spec_id
            WHERE fa.finding_id=?""",(fid,)).fetchone()
        con.execute("UPDATE review_acceptance_specs SET spec_json='{}' WHERE acceptance_spec_id=?",
                    (row["acceptance_spec_id"],))
    result=AcceptanceRunner(db,ledger,verification=None).run_for_finding(fid,cwd=tmp_path)
    assert result[0]["status"]=="FAIL"
    assert result[0]["reason"]=="ACCEPTANCE_HASH_MISMATCH"

def test_no_progress_stops_loop():
    current=("a","b")
    assert stop_reason(
        previous_blockers=current,current_blockers=current,round_no=2,max_rounds=4,
        total_cost_usd=.1,max_cost_usd=10,
    )=="NO_PROGRESS"

def test_review_pack_integrity(db,ledger,tmp_path):
    store=ReviewStore(db,ledger)
    req,_=_request()
    rid=store.create_run(req)
    report=ReviewReportService(store)
    builder=NativeReviewPackBuilder(store,report)
    out=tmp_path/"review.zip"
    result=builder.export(rid,out)
    assert result["integrity"]=="PASS"
    ok,reason=verify_pack(out)
    assert ok,reason

    with zipfile.ZipFile(out,"a",zipfile.ZIP_DEFLATED) as z:
        root_name=z.namelist()[0].split("/",1)[0]
        z.writestr(f"{root_name}/README.md","tampered")
    ok,reason=verify_pack(out)
    assert not ok
    assert reason.startswith("member_hash")

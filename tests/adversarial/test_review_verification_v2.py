from pathlib import Path
import inspect
import sys
import pytest
import qdw
from qdw.proof.plan import VerificationPlan,VerificationCommand
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2

def _service(db,ledger,tmp_path,monkeypatch):
    import qdw.proof.verification_service as vs
    monkeypatch.setattr(vs,"_git_subject",lambda cwd:("subject-sha",False))
    return VerificationService(db,ledger,tmp_path/"runs")

def test_single_verification_truth():
    root=Path(qdw.__file__).resolve().parent
    paths=[
        root/"core/verification/runner.py",
        root/"proof/runner.py",
        root/"proof/verification_service.py",
    ]
    definitions=0
    for path in paths:
        if path.exists():
            definitions += path.read_text(errors="replace").count("class VerificationRunner")
            definitions += path.read_text(errors="replace").count("class VerificationService")
    assert definitions==1, f"expected one canonical verification implementation, found {definitions}"

def test_plan_preexists_receipts():
    with pytest.raises(ValueError):
        VerificationPlan.from_dict({"plan_id":"x","version":"1","commands":[]})

def test_plan_mutation_detected(db,ledger,tmp_path,monkeypatch):
    service=_service(db,ledger,tmp_path,monkeypatch)
    p1=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print(1)")),))
    p2=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print(2)")),))
    service.register_plan(p1)
    with pytest.raises(ValueError,match="immutable"):
        service.register_plan(p2)

def test_mixed_sha_rejected():
    sig=inspect.signature(BuildCertificateV2.issue)
    assert "verification_run_id" in sig.parameters
    assert "receipts" not in sig.parameters, "certificate must not accept arbitrary receipt mixtures"

def test_dirty_subject_rejected(db,ledger,tmp_path,monkeypatch):
    import qdw.proof.verification_service as vs
    monkeypatch.setattr(vs,"_git_subject",lambda cwd:("sha",True))
    service=VerificationService(db,ledger,tmp_path/"runs")
    plan=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print(1)")),))
    with pytest.raises(ValueError,match="dirty"):
        service.execute(plan,task_id="x",cwd=tmp_path,require_clean=True)

def test_artifact_mutation_detected(db,ledger,tmp_path,monkeypatch):
    service=_service(db,ledger,tmp_path,monkeypatch)
    artifact=tmp_path/"artifact.txt"
    artifact.write_text("before")
    plan=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print(1)")),),
                          artifacts=("artifact.txt",))
    run=service.execute(plan,task_id="x",cwd=tmp_path,require_clean=False)
    cert=BuildCertificateV2(service).issue(run)
    artifact.write_text("after")
    ok,reason=BuildCertificateV2(service).verify(cert["build_certificate_id"])
    assert not ok
    assert "artifact_hash" in reason

def test_log_mutation_detected(db,ledger,tmp_path,monkeypatch):
    service=_service(db,ledger,tmp_path,monkeypatch)
    plan=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print('ok')")),))
    run=service.execute(plan,task_id="x",cwd=tmp_path,require_clean=False)
    record=service.run_record(run)
    Path(record["receipts"][0]["stdout_path"]).write_text("tampered")
    ok,reason=service.verify_evidence(run)
    assert not ok
    assert reason.startswith("log_hash")

def test_attack_crash_is_not_success(db,ledger,tmp_path,monkeypatch):
    from qdw.review.attacks import AttackDefinition,AttackRunner
    service=_service(db,ledger,tmp_path,monkeypatch)
    runner=AttackRunner(db,ledger,service)
    # review_round row is required; create minimal canonical review state via helper SQL.
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO review_runs(
          review_run_id,subject_git_sha,subject_dirty,policy_id,policy_hash,profile,trigger_type,
          changed_paths_json,status,current_round,max_rounds,spent_cost_usd,started_at,updated_at
        ) VALUES('review-x','sha',0,'p','h','quick','test','[]','ATTACKING',1,1,0,'t','t')""")
        con.execute("""INSERT INTO review_rounds(
          review_round_id,review_run_id,round_no,subject_git_sha,policy_hash,reviewer_set_hash,
          attack_set_hash,status,started_at
        ) VALUES('round-x','review-x',1,'sha','h','r','a','RUNNING','t')""")
    attack=AttackDefinition("X","1","test","crash",(sys.executable,"-c","raise SystemExit(2)"),"EXPECTED")
    result=runner.run("round-x",attack,cwd=tmp_path,subject_sha="sha")
    assert result["status"]=="FAIL"

def test_replay_requires_exact_sha(db,ledger,tmp_path,monkeypatch):
    service=_service(db,ledger,tmp_path,monkeypatch)
    plan=VerificationPlan("p","1",(VerificationCommand("x",(sys.executable,"-c","print(1)")),))
    run=service.execute(plan,task_id="x",cwd=tmp_path,require_clean=False)
    cert=BuildCertificateV2(service).issue(run)
    with db.tx(immediate=True) as con:
        con.execute("UPDATE verification_runs_v2 SET subject_git_sha='other' WHERE verification_run_id=?",(run,))
    ok,reason=BuildCertificateV2(service).verify(cert["build_certificate_id"])
    assert not ok
    assert reason=="subject_binding"

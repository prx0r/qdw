from pathlib import Path
import json,sys,pytest
from qdw.proof.runner import VerificationRunner
from qdw.proof.certificate import BuildCertificateBuilder
from qdw.proof.test_guard import scan_test_file

def test_runner_records_real_pass_and_fail(tmp_path):
    r=VerificationRunner(tmp_path/"runs")
    ok=r.run("T",[sys.executable,"-c","print('real')"],cwd=tmp_path)
    bad=r.run("T",[sys.executable,"-c","raise SystemExit(3)"],cwd=tmp_path)
    assert ok.status=="PASS" and ok.exit_code==0 and Path(ok.stdout_path).read_text().strip()=="real"
    assert bad.status=="FAIL" and bad.exit_code==3
    assert ok.stdout_sha256 != bad.stdout_sha256

def test_certificate_refuses_missing_or_failed_receipt(tmp_path):
    r=VerificationRunner(tmp_path/"runs")
    good=[sys.executable,"-c","print('ok')"]
    bad=[sys.executable,"-c","raise SystemExit(2)"]
    r.run("T",good,cwd=tmp_path);r.run("T",bad,cwd=tmp_path)
    artifact=tmp_path/"a.txt";artifact.write_text("x")
    b=BuildCertificateBuilder(r)
    with pytest.raises(ValueError):
        b.build(task_id="T",required_commands=[good,bad],acceptance_spec_hash="h",
                artifact_paths=[artifact],output_path=tmp_path/"cert.json")
    cert=b.build(task_id="T",required_commands=[good],acceptance_spec_hash="h",
                 artifact_paths=[artifact],output_path=tmp_path/"cert.json")
    assert cert["status"]=="PROVEN"

def test_test_guard_catches_fake_green(tmp_path):
    p=tmp_path/"test_fake.py"
    p.write_text("def test_fake():\n    assert True\n")
    findings=scan_test_file(p)
    assert any(x.code=="ASSERT_TRUE" for x in findings)

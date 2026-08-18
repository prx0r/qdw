import json,zipfile
from pathlib import Path
import pytest
from qdw_review.models import Evidence,Finding,ModuleResult,ReviewReport,Severity,SubjectSnapshot
from qdw_review.pack import ReviewPackBuilder
from qdw_review.report import html,sarif
from qdw_review.certificate import ReviewCertificateBuilder
from qdw_review.policy import ReviewPolicy

def report(blocker=False,dirty=False):
    findings=[]
    if blocker:
        findings=[Finding("R","m",Severity.HIGH,"title","summary","inv",
                          [Evidence("source","x.py")],"fix",["test"])]
    return ReviewReport(
        "qdw.review.v2",SubjectSnapshot(".", "abcdef123456",dirty),"quick",
        [ModuleResult("m","1",findings)],"now"
    )

def test_html_interactive():
    h=html(report(True).to_dict())
    assert "function draw()" in h
    assert "QDW Autonomous Review" in h
    assert "CRITICAL" in h

def test_sarif_has_finding():
    s=sarif(report(True).to_dict())
    assert s["runs"][0]["results"][0]["ruleId"]=="R"

def test_pack_builder_integrity(tmp_path):
    out=tmp_path/"review.zip"
    result=ReviewPackBuilder().build(
        report=report(True).to_dict(),fix_tasks=[{"x":1}],acceptance_specs=[{"a":1}],
        attack_results=[{"attack_id":"A","status":"PASS"}],reviewer_outputs=[],
        receipts=[],certificates=[],output_zip=out,
    )
    assert result["integrity"]=="PASS"
    assert result["sha256"]
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert any(n.endswith("/REPORT.html") for n in z.namelist())
        assert any(n.endswith("/MANIFEST.json") for n in z.namelist())

def test_review_certificate_rejects_blocker():
    b=ReviewCertificateBuilder()
    with pytest.raises(ValueError):
        b.issue(
            report(True),ReviewPolicy("p"),attack_results=[],
            reviewer_definitions=[],certifier_worker_id="cert",
        )

def test_review_certificate_rejects_dirty():
    b=ReviewCertificateBuilder()
    with pytest.raises(ValueError):
        b.issue(
            report(False,True),ReviewPolicy("p"),attack_results=[],
            reviewer_definitions=[],certifier_worker_id="cert",
        )

def test_review_certificate_rejects_same_producer():
    b=ReviewCertificateBuilder()
    with pytest.raises(ValueError):
        b.issue(
            report(False),ReviewPolicy("p"),attack_results=[],
            reviewer_definitions=[],certifier_worker_id="w",producer_worker_id="w",
        )

def test_review_certificate_binds_required_attack():
    b=ReviewCertificateBuilder()
    policy=ReviewPolicy("p",required_attacks=("A01",))
    with pytest.raises(ValueError):
        b.issue(report(False),policy,attack_results=[],reviewer_definitions=[],
                certifier_worker_id="cert")
    cert=b.issue(report(False),policy,attack_results=[{"attack_id":"A01","status":"PASS"}],
                 reviewer_definitions=[],certifier_worker_id="cert")
    assert b.verify_envelope(cert)

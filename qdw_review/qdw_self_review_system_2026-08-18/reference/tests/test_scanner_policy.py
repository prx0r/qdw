from qdw_review.models import Evidence,Finding,Severity
from qdw_review.scanner import ReviewScanner
from qdw_review.policy import evaluate
from qdw_review.sarif import to_sarif
from qdw_review.report_html import render

def test_finding_id_stable():
    a=Finding("R","M",Severity.HIGH,"T","S","I",[Evidence("source","x.py",detail="a")])
    b=Finding("R","M",Severity.HIGH,"T","changed","I",[Evidence("source","x.py",detail="b")])
    assert a.finding_id == b.finding_id

def test_scanner_aggregates(broken_repo,tmp_path):
    report=ReviewScanner().scan(broken_repo,out_dir=tmp_path/"out")
    assert report.findings
    assert report.counts()["CRITICAL"] >= 1
    assert (tmp_path/"out/latest.json").exists()

def test_policy_blocks_high(broken_repo):
    report=ReviewScanner().scan(broken_repo).to_dict()
    res=evaluate(report,{"block_at":"HIGH","required_modules":[],"minimum_passing_receipts":0})
    assert res["status"]=="FAIL" and res["blockers"]

def test_sarif_contains_results(broken_repo):
    s=to_sarif(ReviewScanner().scan(broken_repo).to_dict())
    assert s["runs"][0]["results"]

def test_html_is_interactive(broken_repo):
    h=render(ReviewScanner().scan(broken_repo).to_dict())
    assert '<select id="sev">' in h and "function draw()" in h

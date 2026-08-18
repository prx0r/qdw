import json
from pathlib import Path
from qdw_review.scanner import StaticScanner
from qdw_review.cli import main

def test_scanner_aggregates_broken_repo(broken_repo):
    r=StaticScanner().scan(broken_repo)
    assert r.counts()["CRITICAL"]>=1
    assert r.blocker_fingerprints()

def test_cli_scan_writes_outputs(broken_repo,tmp_path):
    out=tmp_path/"review"
    rc=main(["scan",str(broken_repo),"--out",str(out)])
    assert rc==1
    assert (out/"REVIEW.json").exists()
    assert (out/"REPORT.html").exists()
    assert (out/"REVIEW.sarif").exists()
    assert (out/"FIX_PLAN.json").exists()

def test_cli_modules(capsys):
    rc=main(["modules"])
    assert rc==0
    assert "review.verification" in capsys.readouterr().out

def test_cli_pack(tmp_path):
    review={
        "schema_version":"qdw.review.v2",
        "subject":{"repo_path":".","git_sha":"abcdef123456","dirty":False,"changed_paths":[]},
        "profile":"quick","generated_at":"now",
        "counts":{"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"INFO":0},
        "modules":[],"receipts":[],"attacks":[]
    }
    inp=tmp_path/"r.json";inp.write_text(json.dumps(review))
    out=tmp_path/"r.zip"
    rc=main(["pack",str(inp),"--out",str(out)])
    assert rc==0 and out.exists()

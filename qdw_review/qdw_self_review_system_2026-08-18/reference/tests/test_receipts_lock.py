import sys,json
from pathlib import Path
from qdw_review.receipts import ReceiptRunner
from qdw_review.migration_lock import create_lock

def test_receipt_real_exit_code(tmp_path):
    r=ReceiptRunner(tmp_path/"runs")
    good=r.run("x",[sys.executable,"-c","print('ok')"],tmp_path)
    bad=r.run("x",[sys.executable,"-c","raise SystemExit(7)"],tmp_path)
    assert good.status=="PASS" and good.exit_code==0
    assert bad.status=="FAIL" and bad.exit_code==7
    assert Path(good.stdout_path).read_text().strip()=="ok"

def test_migration_lock_hashes_files(tmp_path):
    (tmp_path/"migrations").mkdir()
    (tmp_path/"migrations/0001_x.sql").write_text("select 1;")
    out=tmp_path/"lock.json"
    d=create_lock(tmp_path,out)
    assert "migrations/0001_x.sql" in d["files"]
    assert json.loads(out.read_text())["files"]==d["files"]

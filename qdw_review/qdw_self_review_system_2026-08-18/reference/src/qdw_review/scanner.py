from __future__ import annotations
from datetime import UTC, datetime
from pathlib import Path
import json
from qdw_review.checks import ALL_CHECKS
from qdw_review.models import ReviewReport
from qdw_review.profiles import PROFILES
from qdw_review.receipts import ReceiptRunner
from qdw_review.repo import Repo

class ReviewScanner:
    def __init__(self, checks=None):
        self.checks = checks or [c() for c in ALL_CHECKS]

    def scan(self, repo_path:str|Path, *, profile:str="quick", out_dir:str|Path|None=None)->ReviewReport:
        repo=Repo(repo_path)
        modules=[c.run(repo) for c in self.checks]
        receipts=[]
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile}")
        if out_dir is not None and PROFILES[profile]:
            runner=ReceiptRunner(Path(out_dir)/"receipts")
            for argv in PROFILES[profile]:
                try:r=runner.run("dynamic."+profile,argv,repo.root)
                except FileNotFoundError:
                    continue
                receipts.append(r.to_dict())
        report=ReviewReport(
            schema_version="qdw.review.v1",
            repo_path=str(repo.root),
            git_sha=repo.git_sha(),
            git_dirty=repo.git_dirty(),
            profile=profile,
            modules=modules,
            generated_at=datetime.now(UTC).isoformat().replace("+00:00","Z"),
            receipts=receipts,
        )
        if out_dir is not None:
            out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
            (out/"latest.json").write_text(json.dumps(report.to_dict(),indent=2),encoding="utf-8")
        return report

from __future__ import annotations
from datetime import UTC,datetime
from pathlib import Path
from .checks import ALL_CHECKS
from .models import ReviewReport,SubjectSnapshot
from .repo import Repo

class StaticScanner:
    def __init__(self,checks=None):
        self.checks=[c() for c in (checks or ALL_CHECKS)]

    def scan(self,repo_path:str|Path,profile:str="quick",base_ref:str|None=None)->ReviewReport:
        repo=Repo(repo_path)
        subject=SubjectSnapshot(str(repo.root),repo.git_sha(),repo.dirty(),repo.changed_paths(base_ref))
        modules=[c.run(repo) for c in self.checks]
        return ReviewReport(
            "qdw.review.v2",subject,profile,modules,
            datetime.now(UTC).isoformat().replace("+00:00","Z"),
        )

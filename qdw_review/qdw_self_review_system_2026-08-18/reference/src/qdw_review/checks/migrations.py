from __future__ import annotations
import json
from pathlib import Path
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class MigrationCheck(Check):
    module_id="review.migrations"

    def run(self,repo:Repo):
        fs=[]
        mig=repo.read("src/qdw/core/migrations.py")
        db=repo.read("src/qdw/core/db.py")
        if "schema_versions" in mig and "checksum" not in mig.lower():
            fs.append(finding(
                rule_id="QDW-MIG-001",module_id=self.module_id,severity=Severity.CRITICAL,
                title="Applied migration content is not checksum-locked",
                summary="schema_versions records only integer versions. Editing an already-applied migration silently leaves existing databases on a different schema than fresh databases.",
                invariant="An applied migration version is immutable and bound to a content digest.",
                evidence=[self.evidence(repo,"src/qdw/core/migrations.py","schema_versions has no content checksum enforcement")],
                remediation="Store migration SHA-256 with version/name. On every startup, recompute all applied migration hashes and refuse drift. New changes require a new numbered migration.",
                acceptance_tests=[
                    "Apply migration 2, modify its bytes, rerun migrator: must fail with MIGRATION_DRIFT.",
                    "Fresh DB and upgraded DB have identical schema fingerprints."
                ],
                tags=["schema","upgrade","immutability"]
            ))
        if "def migrate(self, migrations_dir" in db and "migrate_all(self)" in db:
            fs.append(finding(
                rule_id="QDW-MIG-002",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Database.migrate ignores its migrations_dir argument",
                summary="The public method accepts a custom migration path but drops it when delegating.",
                invariant="Public migration parameters change the behavior they claim to control.",
                evidence=[self.evidence(repo,"src/qdw/core/db.py","migrations_dir is accepted but not forwarded")],
                remediation="Forward migrations_dir through migrate_all/migrate and test an isolated custom directory.",
                acceptance_tests=["Database.migrate(custom_dir) applies only custom_dir migrations."],
                tags=["api-contract"]
            ))
        if "executescript(sql)" in mig and 'INSERT OR IGNORE INTO schema_versions' in mig and "BEGIN" not in mig:
            fs.append(finding(
                rule_id="QDW-MIG-003",module_id=self.module_id,severity=Severity.HIGH,
                title="Migration SQL and version recording are not proven atomic",
                summary="The runner calls executescript and then records the version without an explicit transaction that covers both operations.",
                invariant="A migration either fully applies and records its checksum/version, or no part is committed.",
                evidence=[self.evidence(repo,"src/qdw/core/migrations.py","executescript + version insert without explicit transaction envelope")],
                remediation="Wrap each migration and schema_versions insert in an explicit transaction strategy tested against a deliberately failing migration.",
                acceptance_tests=["A migration failing halfway leaves neither schema changes nor schema_versions row."],
                tags=["atomicity","migration"]
            ))
        # Baseline lock support: once installed, reviewer itself can catch future drift.
        lock=repo.path(".qdw/review/migration_lock.json")
        if lock.exists():
            try:
                data=json.loads(lock.read_text())
                for rel, expected in data.get("files",{}).items():
                    actual=repo.file_hash(rel)
                    if actual and actual != expected:
                        fs.append(finding(
                            rule_id="QDW-MIG-004",module_id=self.module_id,severity=Severity.CRITICAL,
                            title=f"Locked migration changed: {rel}",
                            summary="A migration previously locked by qdw-review changed in place.",
                            invariant="Locked migration bytes never change.",
                            evidence=[self.evidence(repo,rel,f"expected {expected}, actual {actual}")],
                            remediation="Restore migration bytes and create a new migration.",
                            acceptance_tests=["Migration lock passes with zero drift."],
                            tags=["migration","drift"]
                        ))
            except Exception:
                pass
        return self.result(fs)

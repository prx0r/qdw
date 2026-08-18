from __future__ import annotations
import re
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

_TABLE=re.compile(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\);",re.S|re.I)

class SchemaCheck(Check):
    module_id="review.schema"

    def run(self,repo:Repo):
        fs=[]
        text="\n".join(repo.read(repo.rel(p)) for p in repo.glob("migrations/*.sql"))
        weak=[]
        for name,body in _TABLE.findall(text):
            lines=[x.strip() for x in body.splitlines()]
            for line in lines:
                m=re.match(r"(\w+_id)\s+TEXT\b",line,re.I)
                if not m:continue
                col=m.group(1)
                # Primary identity columns are not foreign keys.
                if col in {f"{name[:-1]}_id", "event_id"} or "PRIMARY KEY" in line.upper():
                    continue
                if "REFERENCES" not in line.upper():
                    weak.append((name,col))
        if len(weak) >= 8:
            preview=", ".join(f"{t}.{c}" for t,c in weak[:18])
            fs.append(finding(
                rule_id="QDW-SCHEMA-001",module_id=self.module_id,severity=Severity.HIGH,
                title="Global object graph relies heavily on unbound TEXT IDs",
                summary=f"Detected many relationship-shaped *_id columns without database foreign keys, including {preview}.",
                invariant="Canonical cross-object lineage is protected by DB constraints where the relation is mandatory/stable.",
                evidence=[self.evidence(repo,"migrations/0002_global.sql","relationship IDs lack REFERENCES constraints")],
                remediation="Add new migration(s) rebuilding affected SQLite tables with foreign keys and CHECK constraints. Keep polymorphic references explicit where FKs are impossible.",
                acceptance_tests=["PRAGMA foreign_key_check returns empty.", "Deleting parent objects cannot leave impossible product/idea/factory lineage."],
                tags=["foreign-key","lineage"]
            ))
        return self.result(fs,notes=[f"Unbound relationship-shaped columns: {len(weak)}"])

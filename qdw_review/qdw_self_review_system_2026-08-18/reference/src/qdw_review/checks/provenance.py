from __future__ import annotations
import ast
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ProvenanceCheck(Check):
    module_id="review.provenance"

    def _split_tx_functions(self, text:str):
        try: tree=ast.parse(text)
        except SyntaxError:return []
        bad=[]
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            has_tx=False; ledger_after=False
            for stmt in node.body:
                src=ast.unparse(stmt) if hasattr(ast,"unparse") else ""
                if "self.db.tx(" in src:
                    has_tx=True
                if has_tx and "self.ledger.append(" in src and not isinstance(stmt,ast.With):
                    ledger_after=True
            if has_tx and ledger_after:bad.append(node.name)
        return bad

    def run(self,repo:Repo):
        fs=[]
        offenders=[]
        for p in repo.rglob("*.py"):
            rel=repo.rel(p)
            if not rel.startswith("src/qdw/"):continue
            text=repo.read(rel)
            funcs=self._split_tx_functions(text)
            if funcs: offenders.append((rel,funcs))
        if offenders:
            detail="; ".join(f"{p}: {','.join(fs_)}" for p,fs_ in offenders[:12])
            fs.append(finding(
                rule_id="QDW-PROV-001",module_id=self.module_id,severity=Severity.HIGH,
                title="State transitions and ledger events are split across transactions",
                summary="Multiple services commit canonical state and only then append provenance. A crash between those operations leaves state with no corresponding event.",
                invariant="A state transition and its semantic event commit atomically or neither commits.",
                evidence=[self.evidence(repo,p,f"split transaction functions: {','.join(names)}") for p,names in offenders[:8]],
                remediation="Add Ledger.append(..., con=existing_connection) or an Outbox table written in the same transaction. Never append required provenance after commit.",
                acceptance_tests=[
                    "Inject a failure during event write and prove state mutation rolls back.",
                    "Inject a failure during state write and prove no event appears.",
                    "Replay ledger/state consistency check reports zero orphan transitions."
                ],
                tags=["ledger","atomicity","crash-consistency"]
            ))
        return self.result(fs,notes=[f"Detected split transaction patterns: {len(offenders)}"])

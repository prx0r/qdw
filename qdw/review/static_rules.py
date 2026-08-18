"""High-value deterministic rules.

These are cheap, run on every commit, and should grow whenever semantic reviewers find a pattern that can
be encoded mechanically.
"""
from __future__ import annotations
import ast
from .models import ReviewerFinding
from .static_engine import file_evidence

class Base:
    version="2.0.0"
    def rf(self,rule_id,severity,title,summary,invariant,remediation,evidence,tests=(),specs=()):
        return ReviewerFinding(
            rule_id,severity,title,summary,invariant,remediation,
            tuple(evidence),tuple(tests),tuple(specs),1.0
        )

class SingleVerificationTruth(Base):
    rule_id="STATIC-VER-001"
    def check(self,root):
        a=root/"src/qdw/core/verification/runner.py"; b=root/"src/qdw/proof/runner.py"
        ta=a.read_text(errors="replace") if a.exists() else ""
        tb=b.read_text(errors="replace") if b.exists() else ""
        independent=("class VerificationRunner" in ta and "class VerificationRunner" in tb)
        split=("qdw.proof.verification_service" not in ta and "qdw.proof.verification_service" not in tb)
        if a.exists() and b.exists() and (independent or split):
            yield self.rf(
                self.rule_id,"CRITICAL","Multiple verification runners",
                "Both core and proof VerificationRunner implementations exist.",
                "One canonical service computes verification PASS.",
                "Collapse to qdw.proof.VerificationService and keep only compatibility imports.",
                [
                    file_evidence(root,"src/qdw/core/verification/runner.py","runner A"),
                    file_evidence(root,"src/qdw/proof/runner.py","runner B"),
                ],
                specs=({"kind":"static_rule","rule_id":self.rule_id},),
            )

class FrozenPlanRule(Base):
    rule_id="STATIC-VER-002"
    def check(self,root):
        rel="scripts/build_certificate.py"
        p=root/rel
        t=p.read_text(errors="replace") if p.exists() else ""
        if "required_cmds" in t and "for r in receipts" in t:
            yield self.rf(
                self.rule_id,"CRITICAL","Certificate requirements derived from receipts",
                "Required commands are observed after execution.",
                "Acceptance plan is frozen and hashed before any command runs.",
                "Require explicit VerificationPlan path/hash.",
                [file_evidence(root,rel,"post-hoc requirements")],
                specs=({"kind":"static_rule","rule_id":self.rule_id},),
            )

class SplitProvenanceRule(Base):
    rule_id="STATIC-PROV-001"
    def check(self,root):
        rel="src/qdw/core/graph/store.py"
        p=root/rel
        if not p.exists():
            return
        text=p.read_text(errors="replace")
        try:
            tree=ast.parse(text)
        except SyntaxError:
            return
        bad=[]
        for n in ast.walk(tree):
            if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            body="\n".join(ast.unparse(x) for x in n.body)
            if "self.db.tx(" in body and "self.ledger.append(" in body and "append_in_tx" not in body:
                bad.append(n.name)
        if bad:
            yield self.rf(
                self.rule_id,"CRITICAL","State/event split transaction",
                "Methods commit canonical state then append provenance separately: "+", ".join(sorted(set(bad))),
                "State transition and required semantic event commit together.",
                "Use append_in_tx/outbox and crash-inject each transition.",
                [file_evidence(root,rel,"split methods: "+",".join(bad))],
                specs=({"kind":"static_rule","rule_id":self.rule_id},),
            )

class CycleCommitRule(Base):
    rule_id="STATIC-GRAPH-001"
    def check(self,root):
        rel="src/qdw/core/graph/store.py"
        p=root/rel
        if not p.exists():
            return
        t=p.read_text(errors="replace")
        insert=t.find("INSERT OR IGNORE INTO work_edges")
        validate=t.find("cycles = self.validate_dag(graph_id)")
        if insert!=-1 and validate>insert:
            yield self.rf(
                self.rule_id,"CRITICAL","Cycle validation follows edge insert",
                "A raised cycle error can leave the edge committed.",
                "Rejected graph mutations leave canonical state unchanged.",
                "Validate tentative edge in same transaction/rollback.",
                [file_evidence(root,rel,"insert before cycle check")],
                specs=({
                    "kind":"command","id":"cycle_rollback",
                    "argv":["python","-m","pytest","tests/adversarial/test_review_graph_v2.py::test_cycle_insert_rolls_back","-q"],
                },),
            )

class FakeAPIFixtureRule(Base):
    rule_id="STATIC-FACTORY-001"
    def check(self,root):
        rel="tests/factories/test_api_factory.py"
        p=root/rel
        if not p.exists():
            return
        t=p.read_text(errors="replace")
        if 'ctx.get("ok") is True' in t and not any(x in t for x in ("TestClient","urlopen","httpx.")):
            yield self.rf(
                self.rule_id,"CRITICAL","API fixture does not exercise HTTP",
                "Fixture hand-feeds ok=True into a lambda.",
                "API factory fixture boots/calls the generated artifact.",
                "Replace with actual temporary app + HTTP verifier.",
                [file_evidence(root,rel,"manual gate")],
                specs=({
                    "kind":"command","id":"real_api_fixture",
                    "argv":["python","-m","pytest","tests/factories/test_api_factory_real.py","-q"],
                },),
            )

class NativeReviewRule(Base):
    rule_id="STATIC-SELF-001"
    def check(self,root):
        if not (root/"src/qdw/review").exists():
            yield self.rf(
                self.rule_id,"CRITICAL","No native self-review subsystem",
                "Review assets may exist as a nested pack but not runtime code.",
                "QDW owns persisted review lifecycle and can review itself.",
                "Integrate src/qdw/review and QDWSystem.review.",
                [],specs=({"kind":"static_rule","rule_id":self.rule_id},),
            )

class MigrationCIRule(Base):
    rule_id="STATIC-MIG-001"
    def check(self,root):
        ci=root/".github/workflows/ci.yml"
        migrations=sorted((root/"migrations").glob("[0-9][0-9][0-9][0-9]_*.sql"))
        if not ci.exists() or not migrations:
            return
        highest=int(migrations[-1].name.split("_")[0])
        t=ci.read_text(errors="replace")
        if f"assert {highest} in v" not in t and "expected_versions" not in t:
            yield self.rf(
                self.rule_id,"HIGH","CI migration gate is stale",
                f"Highest migration is {highest}, but CI does not prove complete version set.",
                "CI exercises the current full migration graph.",
                "Replace inline partial check with migration fresh/upgrade/drift suite.",
                [file_evidence(root,".github/workflows/ci.yml","stale migration assertions")],
                specs=({
                    "kind":"command","id":"migration_suite",
                    "argv":["python","-m","pytest","tests/adversarial/test_review_migrations_v2.py","-q"],
                },),
            )

class RouteRoundTripRule(Base):
    rule_id="STATIC-HOT-001"
    FIELDS=("endpoint_id","account_id","prior_success","prior_confidence","breaker_open","quota_pressure","evidence_ids")
    def check(self,root):
        rel="src/qdw/hotswap/persistent.py"
        p=root/rel
        if not p.exists():
            return
        t=p.read_text(errors="replace")
        missing=[x for x in self.FIELDS if x not in t]
        if missing:
            yield self.rf(
                self.rule_id,"HIGH","Route persistence is lossy",
                "Missing persisted route fields: "+", ".join(missing),
                "Restart preserves all routing-relevant semantics.",
                "Persist full RouteDefinition or split dynamic observations explicitly.",
                [file_evidence(root,rel,"missing route fields")],
                specs=({
                    "kind":"command","id":"route_roundtrip",
                    "argv":["python","-m","pytest","tests/adversarial/test_review_hotswap_v2.py::test_route_roundtrip_complete","-q"],
                },),
            )

ALL_RULES=[
    SingleVerificationTruth(),FrozenPlanRule(),SplitProvenanceRule(),CycleCommitRule(),
    FakeAPIFixtureRule(),NativeReviewRule(),MigrationCIRule(),RouteRoundTripRule(),
]

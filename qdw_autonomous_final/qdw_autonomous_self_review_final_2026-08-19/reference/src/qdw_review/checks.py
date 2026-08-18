from __future__ import annotations
import ast,re
from abc import ABC,abstractmethod
from .models import Evidence,Finding,ModuleResult,Severity
from .repo import Repo

def ev(repo:Repo,path:str,detail:str,line:int|None=None)->Evidence:
    return Evidence("source",path,line,detail,repo.digest(path))

def f(rule,module,severity,title,summary,invariant,evidence,remediation,tests,confidence=1.0):
    return Finding(rule,module,severity,title,summary,invariant,evidence,remediation,tests,confidence=confidence)

class Check(ABC):
    module_id="review.base"
    version="2.0.0"
    @abstractmethod
    def run(self,repo:Repo)->ModuleResult:...
    def result(self,findings,notes=None):return ModuleResult(self.module_id,self.version,findings,notes or [])

class VerificationCheck(Check):
    module_id="review.verification"
    def run(self,repo):
        out=[]
        core=repo.read("src/qdw/core/verification/runner.py")
        proof=repo.read("src/qdw/proof/runner.py")
        script=repo.read("scripts/build_certificate.py")
        cert=repo.read("src/qdw/proof/certificate.py")
        ci=repo.read(".github/workflows/ci.yml")
        if "class VerificationRunner" in core and "class VerificationRunner" in proof:
            out.append(f("QDW-AUTO-VER-001",self.module_id,Severity.CRITICAL,
                "Two canonical-looking VerificationRunner implementations",
                "CLI/core verification and proof/certificate verification use different receipt stores and schemas.",
                "One VerificationService owns command evidence.",
                [ev(repo,"src/qdw/core/verification/runner.py","VerificationRunner A"),
                 ev(repo,"src/qdw/proof/runner.py","VerificationRunner B")],
                "Collapse onto one service; compatibility modules only re-export/adapt it.",
                ["CLI receipt is consumable by BuildCertificate without translation.","Only one code path computes PASS."]))
        if "required_cmds" in script and "for r in receipts" in script:
            out.append(f("QDW-AUTO-VER-002",self.module_id,Severity.CRITICAL,
                "Build requirements are inferred after execution",
                "build_certificate.py derives required_commands from observed receipts instead of a pre-frozen plan.",
                "Acceptance criteria are frozen before execution.",
                [ev(repo,"scripts/build_certificate.py","observed receipts become required commands")],
                "Load a content-hashed VerificationPlan and demand its command IDs.",
                ["Adding/removing a receipt cannot change plan requirements.","Missing planned command blocks certificate."]))
        if 'acceptance_spec_hash="ci_pipeline"' in script or "acceptance_spec_hash='ci_pipeline'" in script:
            out.append(f("QDW-AUTO-VER-003",self.module_id,Severity.HIGH,
                "Acceptance spec hash is a label, not a digest",
                "Certificate script uses ci_pipeline instead of a cryptographic digest of a frozen plan/spec.",
                "Certificate binds exact immutable acceptance bytes.",
                [ev(repo,"scripts/build_certificate.py","placeholder acceptance hash")],
                "Hash the actual plan file and store its path/bytes digest.",
                ["Mutating plan bytes invalidates evidence."]))
        if "negative tests still fail" in cert or "negative test" in cert and "exit_code == 0" in cert:
            out.append(f("QDW-AUTO-VER-004",self.module_id,Severity.HIGH,
                "Adversarial test success is modeled as process failure",
                "Certificate treats a negative test as valid when its process exits nonzero.",
                "A verifier command should pass while proving the invalid action was rejected.",
                [ev(repo,"src/qdw/proof/certificate.py","negative tests expect nonzero")],
                "Represent attacks as typed AttackResults separate from command exit status.",
                ["pytest adversarial command exits 0 and AttackResult is REJECTED_AS_EXPECTED."]))
        if "pytest tests/" in ci and "qdw verify-plan" not in ci and "verification plan" not in ci.lower():
            out.append(f("QDW-AUTO-VER-005",self.module_id,Severity.HIGH,
                "CI gates are not executed through the certificate evidence run",
                "CI invokes test/lint/type commands directly rather than through one frozen verification run.",
                "Release certificate consumes receipts for the exact CI gates.",
                [ev(repo,".github/workflows/ci.yml","direct CI commands")],
                "Run `qdw verify-plan acceptance/qdw-release.json` as the canonical CI gate.",
                ["Certificate lists receipts for compile/lint/type/unit/contract/adversarial/integration/runtime gates."]))
        return self.result(out)

class TrustCheck(Check):
    module_id="review.trust"
    def run(self,repo):
        out=[]
        for path,label,idkey,verkey in [
            ("src/qdw/factories/registry.py","factory","factory_id","factory_version"),
            ("src/qdw/contractors/registry.py","contractor","contractor_id","contractor_version"),
        ]:
            text=repo.read(path)
            if "SELECT * FROM gate_results WHERE gate_result_id=?" in text:
                out.append(f(f"QDW-AUTO-TRUST-{label.upper()}-001",self.module_id,Severity.CRITICAL,
                    f"{label.title()} activation uses gate_results as certificates",
                    f"A passing generic gate row is promoted into {label} activation evidence.",
                    "Authorization evidence is a dedicated certificate bound to exact subject/version/definition/fixture/artifacts.",
                    [ev(repo,path,"gate_results used as certificate")],
                    f"Introduce typed {label} fixture certificate and verify every binding.",
                    [f"Valid unrelated gate cannot activate {label}.",f"Missing exact {verkey} rejects activation."]))
            if f"if cert_version and cert_version != version" in text:
                out.append(f(f"QDW-AUTO-TRUST-{label.upper()}-002",self.module_id,Severity.HIGH,
                    f"{label.title()} certificate version is optional",
                    "Evidence with no version can authorize a versioned definition.",
                    "Versioned activation requires an exact version binding.",
                    [ev(repo,path,"optional version check")],
                    "Require version field and definition hash equality.",
                    ["Certificate missing version is rejected."]))
        product=repo.read("src/qdw/products/registry.py")
        if "SELECT * FROM gate_results WHERE gate_result_id=?" in product:
            out.append(f("QDW-AUTO-TRUST-PRODUCT-001",self.module_id,Severity.CRITICAL,
                "Product release uses generic gate result as release certificate",
                "Release only checks a product_id in detail_json, not build/artifact/review bindings.",
                "Release authorization binds product, build run, artifact set, build certificate and review policy.",
                [ev(repo,"src/qdw/products/registry.py","gate_result used for product release")],
                "Create ReleaseAuthorization/BuildCertificate relationship and verify it transactionally.",
                ["Certificate from same product but wrong build_run is rejected.","Mutated artifact blocks release."]))
        return self.result(out)

class WorkGraphCheck(Check):
    module_id="review.workgraph"
    def run(self,repo):
        out=[]; text=repo.read("src/qdw/core/graph/store.py")
        if text:
            split=[]
            try:
                tree=ast.parse(text)
                for n in ast.walk(tree):
                    if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
                    body="\n".join(ast.unparse(x) for x in n.body) if hasattr(ast,"unparse") else ""
                    if "self.db.tx(" in body and "self.ledger.append(" in body and "append_in_tx" not in body:
                        split.append(n.name)
            except SyntaxError:pass
            if split:
                out.append(f("QDW-AUTO-GRAPH-001",self.module_id,Severity.CRITICAL,
                    "Canonical state/event transitions remain split transactions",
                    "Functions commit state then append ledger separately: "+", ".join(sorted(set(split))),
                    "Every provenance-required transition commits state+event/outbox atomically.",
                    [ev(repo,"src/qdw/core/graph/store.py","split transitions: "+",".join(split))],
                    "Use append_in_tx or transactional outbox in all listed transitions.",
                    ["Injected ledger failure rolls back each state mutation."]))
            if "con.execute(" in text and "cycles = self.validate_dag(graph_id)" in text:
                insert=text.find("INSERT OR IGNORE INTO work_edges")
                validate=text.find("cycles = self.validate_dag(graph_id)")
                txclose=text.find("cycles = self.validate_dag(graph_id)")
                if insert!=-1 and validate>insert:
                    out.append(f("QDW-AUTO-GRAPH-002",self.module_id,Severity.CRITICAL,
                        "Cyclic edge is validated after its insert transaction commits",
                        "add_edge can raise while leaving the rejected cyclic edge in canonical state.",
                        "Invalid graph mutations never commit.",
                        [ev(repo,"src/qdw/core/graph/store.py","insert then validate")],
                        "Validate tentative adjacency within the same transaction and rollback on cycle.",
                        ["After rejected cycle insertion, querying work_edges shows no new edge."]))
            if "FROZEN" not in text and "freeze" not in text.lower():
                out.append(f("QDW-AUTO-GRAPH-003",self.module_id,Severity.HIGH,
                    "No enforced WorkGraph freeze boundary",
                    "Graph structure can remain mutable around execution.",
                    "Only content-hashed frozen DAG revisions are executable.",
                    [ev(repo,"src/qdw/core/graph/store.py","no graph freeze lifecycle")],
                    "Add DRAFT→FROZEN→RUNNING lifecycle and structure hash.",
                    ["Adding node/edge after freeze fails.","claim_ready rejects non-frozen graph."]))
        return self.result(out)

class MigrationCheck(Check):
    module_id="review.migrations"
    def run(self,repo):
        out=[]; text=repo.read("src/qdw/core/migrations.py"); ci=repo.read(".github/workflows/ci.yml")
        if "executescript(sql)" in text and "INSERT INTO schema_versions" in text:
            out.append(f("QDW-AUTO-MIG-001",self.module_id,Severity.HIGH,
                "Migration body and version record lack a proven atomic envelope",
                "executescript and schema_versions insert are not guarded by a failure-tested transaction.",
                "Migration applies completely with digest or leaves database unchanged.",
                [ev(repo,"src/qdw/core/migrations.py","executescript + later version insert")],
                "Use explicit transaction semantics compatible with SQLite executescript and test mid-script failure.",
                ["Half-failing migration preserves pre-migration schema/data."]))
        if 'row["content_hash"] and row["content_hash"] != content_hash' in text:
            out.append(f("QDW-AUTO-MIG-002",self.module_id,Severity.HIGH,
                "NULL historical migration digests bypass drift checking",
                "Legacy schema_versions rows with NULL content_hash never become protected.",
                "Every applied version has an accepted immutable digest.",
                [ev(repo,"src/qdw/core/migrations.py","drift check skips NULL hash")],
                "Add one-time baseline adoption with schema fingerprint and then enforce NOT NULL digests.",
                ["Applied version with NULL digest is BLOCKED until baselined."]))
        if "assert 2 in v" in ci and "assert 3 in v" not in ci:
            out.append(f("QDW-AUTO-MIG-003",self.module_id,Severity.HIGH,
                "CI migration test is stale",
                "Current migration test proves only versions 1 and 2.",
                "CI proves the complete expected migration sequence and populated upgrade path.",
                [ev(repo,".github/workflows/ci.yml","migration check omits current versions")],
                "Test exact applied version/hash set plus fresh/upgraded DB parity.",
                ["Fresh DB applies every migration.","Populated old DB upgrades without row loss."]))
        m4=repo.read("migrations/0004_foreign_keys.sql")
        if "DROP TABLE IF EXISTS" in m4 and "INSERT OR IGNORE" in m4:
            out.append(f("QDW-AUTO-MIG-004",self.module_id,Severity.HIGH,
                "Destructive FK migration lacks row-preservation proof",
                "0004 rebuilds/drops many tables using INSERT OR IGNORE.",
                "Upgrade preserves every valid row or fails loudly without partial commit.",
                [ev(repo,"migrations/0004_foreign_keys.sql","table rebuild migration")],
                "Add row-count/content-hash pre/post assertions and populated upgrade fixture.",
                ["No row silently disappears during 0004.","foreign_key_check empty after upgrade."]))
        return self.result(out)

class HotSwapCheck(Check):
    module_id="review.hotswap"
    def run(self,repo):
        out=[]; p=repo.read("src/qdw/hotswap/persistent.py"); t=repo.read("src/qdw/hotswap/types.py"); s=repo.read("src/qdw/system.py")
        route_fields=set(re.findall(r"^\s{4}(\w+):",t,re.M))
        persisted=set(re.findall(r"\b(route_id|model_id|provider_id|endpoint_id|account_id|active|free|input_per_m|output_per_m|context_tokens|tools_supported|json_supported|reliability|latency_ms|prior_success|prior_confidence|breaker_open|quota_pressure|cheapest_paid_replacement_cost|evidence_ids)\b",p))
        important={"endpoint_id","account_id","prior_success","prior_confidence","breaker_open","quota_pressure","evidence_ids"}
        missing=sorted(important-persisted)
        if missing:
            out.append(f("QDW-AUTO-HOT-001",self.module_id,Severity.HIGH,
                "Persisted Route snapshot is lossy",
                "Fields disappear on restart: "+", ".join(missing),
                "Restart preserves routing semantics or fields are explicitly modeled as fresh observations.",
                [ev(repo,"src/qdw/hotswap/persistent.py","route save/load subset"),
                 ev(repo,"src/qdw/hotswap/types.py","full Route model")],
                "Persist complete RouteDefinition and separate dynamic evidenced observations.",
                ["save→restart→load roundtrip equals original routing-relevant fields."]))
        if "self._upsert(cell_id, route.route_id, posterior)" in p and "DO UPDATE SET alpha=excluded.alpha" in p:
            out.append(f("QDW-AUTO-HOT-002",self.module_id,Severity.HIGH,
                "First-read posterior initialization can overwrite concurrent updates",
                "get() writes prior with an UPSERT that updates existing rows.",
                "Initialization never decreases/overwrites learned posterior state.",
                [ev(repo,"src/qdw/hotswap/persistent.py","get uses overwrite upsert")],
                "Use INSERT OR IGNORE for initialization; atomic increment for learning.",
                ["Concurrent first get/update preserves all observations."]))
        if "self.routes.append(route)" in s:
            out.append(f("QDW-AUTO-HOT-003",self.module_id,Severity.MEDIUM,
                "In-memory route registry permits duplicate route IDs",
                "DB upsert and list append have different identity semantics.",
                "One active route_id maps to one candidate projection.",
                [ev(repo,"src/qdw/system.py","register_route appends unconditionally")],
                "Use a RouteRegistry keyed by route_id and refresh projection after write.",
                ["Registering same route twice yields one candidate."]))
        return self.result(out)

class FactoryCheck(Check):
    module_id="review.factory"
    def run(self,repo):
        out=[]; text="\n".join(repo.read(repo.rel(p)) for p in repo.rglob("test_*factory*.py"))
        if "lambda ctx: (ctx.get(\"ok\") is True" in text and "uvicorn" not in text and "TestClient" not in text:
            out.append(f("QDW-AUTO-FACTORY-001",self.module_id,Severity.CRITICAL,
                "API factory fixture is simulated",
                "Fixture feeds booleans/result dictionaries into gates without generating and exercising an API artifact.",
                "Factory fixtures exercise the actual artifact through its public contract.",
                [Evidence("source","tests/factories/test_api_factory.py",detail="manual ok=True gate")],
                "Generate temporary API project, boot it, make real HTTP request, hash artifact, and run same verifier against broken variant.",
                ["Success fixture performs actual HTTP.","Broken generated API is rejected by same verifier."]))
        return self.result(out)

class E2ECheck(Check):
    module_id="review.e2e"
    def run(self,repo):
        out=[]; text="\n".join(repo.read(repo.rel(p)) for p in repo.rglob("test_e2e.py"))
        required=["FactoryRegistry","WorkGraphStore","ExecutionRequest","BuildCertificate","release("]
        missing=[x for x in required if x not in text]
        if text and missing:
            out.append(f("QDW-AUTO-E2E-001",self.module_id,Severity.HIGH,
                "E2E does not cross the full execution/certification spine",
                "Missing evidence signals: "+", ".join(missing),
                "V10 includes factory run, graph, executor, artifact, independent verification, certificate and release.",
                [Evidence("source","tests/integration/test_e2e.py",detail="integration path inspected")],
                "Build one gold-standard deterministic product through all runtime layers.",
                ["Removing executor/certificate/release makes V10 fail."]))
        return self.result(out)

class SelfReviewCheck(Check):
    module_id="review.self-review"
    def run(self,repo):
        out=[]
        if not repo.exists("src/qdw/review"):
            out.append(f("QDW-AUTO-SELF-001",self.module_id,Severity.CRITICAL,
                "Self-review is not a native QDW subsystem",
                "Previous review bundle may be committed, but no src/qdw/review runtime exists.",
                "QDW can create, persist, execute and certify review runs through its own composition root.",
                [],
                "Integrate the native review overlay and remove/archive the nested stale pack afterward.",
                ["QDWSystem exposes review service.","qdw review quick works against current checkout."]))
        return self.result(out)

class ClaimCheck(Check):
    module_id="review.claim-consistency"
    def run(self,repo):
        out=[]
        commit_claim=repo.read(".qdw/review/commit_claim.txt")
        graph=repo.read("src/qdw/core/graph/store.py")
        if "atomic provenance" in commit_claim.lower() and graph.count("append_in_tx")<=1 and graph.count("self.ledger.append(")>1:
            out.append(f("QDW-AUTO-CLAIM-001",self.module_id,Severity.HIGH,
                "Atomic-provenance claim exceeds implementation",
                "Only a subset of graph transitions use append_in_tx.",
                "Strong architecture claims are backed by complete mechanical coverage.",
                [ev(repo,"src/qdw/core/graph/store.py","partial append_in_tx coverage")],
                "Close the claim only when transition matrix tests prove atomicity everywhere.",
                ["Every state-mutating method has crash-injection coverage."]))
        return self.result(out)

ALL_CHECKS=[VerificationCheck,TrustCheck,WorkGraphCheck,MigrationCheck,HotSwapCheck,FactoryCheck,E2ECheck,SelfReviewCheck,ClaimCheck]

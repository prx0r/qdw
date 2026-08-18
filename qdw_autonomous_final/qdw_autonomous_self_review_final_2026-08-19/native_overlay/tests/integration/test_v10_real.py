"""Gold-standard V10 exemplar.

This test intentionally crosses QDW's real execution/certification spine and performs actual localhost HTTP.
"""
from hashlib import sha256
from pathlib import Path
import json,sys

from qdw.core import hash_object,utc_now
from qdw.executors.protocol import ExecutionRequest,ExecutionResult
from qdw.factories.fixtures.api import APIFactoryFixture
from qdw.hotswap.types import Route
from qdw.proof.plan import VerificationPlan,VerificationCommand
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2
from qdw.proof.subject_certificates import FixtureCertificateService,ReleaseAuthorizationService
from qdw.products.registry import ProductRegistry,OutcomeAuthority
from qdw.system import QDWSystem

class APIBuilder:
    executor_id="fixture-builder"
    def __init__(self,artifact_dir:Path):
        self.artifact_dir=artifact_dir
    def execute(self,request):
        APIFactoryFixture().generate(self.artifact_dir,broken=False)
        return ExecutionResult(True,"ok",{"artifact_dir":str(self.artifact_dir)},exit_code=0)

class APIVerifier:
    executor_id="independent-api-verifier"
    def execute(self,request):
        result=APIFactoryFixture().verify(Path(request.payload["artifact_dir"]))
        return ExecutionResult(
            result.passed,"ok" if result.passed else "rejected",
            {"status_code":result.status_code,"artifact_hash":result.artifact_hash,
             "reason_code":result.reason_code},
            exit_code=0 if result.passed else 1,
        )

def test_full_execution_spine(tmp_path):
    repo=Path.cwd()
    q=QDWSystem(tmp_path/"qdw.db")

    # 1. Real route inventory and HotSwap selection.
    q.register_route(Route(
        route_id="fixture-route",model_id="deterministic",provider_id="local",
        free=True,reliability=1.0,input_per_m=0,output_per_m=0,
        tools_supported=True,json_supported=True,
    ))
    routed=q.route_task("factory_generate",{"task_id":"v10","quality":0.5})
    assert routed["primary"]["route_id"]=="fixture-route"

    # 2. Register a candidate API factory definition.
    manifest=tmp_path/"factory-api-v10.json"
    manifest.write_text(json.dumps({
        "factory_id":"factory-api-v10","version":"1.0.0","kind":"api","name":"API V10",
        "phases":["generate","verify"],"mandatory_teams":["qa.api"],
        "fixture":{"fixture_id":"api-real-http-v1","max_cost_usd":1.0},
    }))
    definition=q.factories.register_manifest(manifest)
    definition_row=q.factories.get(definition.factory_id,definition.version)

    # 3. FactoryRun + frozen WorkGraph.
    run_id="factoryrun_v10"
    with q.db.tx(immediate=True) as con:
        con.execute("""INSERT INTO factory_runs(
          factory_run_id,factory_id,factory_version,opportunity_id,graph_id,status,
          started_at,total_cost_usd
        ) VALUES(?,?,?,?,NULL,'RUNNING',?,0)""",
        (run_id,definition.factory_id,definition.version,None,utc_now()))
        q.ledger.append_in_tx(con,"factory_run.started","factory_run",run_id,{
            "factory_id":definition.factory_id,"factory_version":definition.version,
        })

    gid=q.graphs.create_graph(factory_run_id=run_id)
    generate=q.graphs.add_node(
        gid,"generate_api","Generate actual API",
        {"route_id":"fixture-route"},expected_value=1,expected_cost=0,
    )
    verify=q.graphs.add_node(
        gid,"verify_api","Independent HTTP verification",
        {},expected_value=1,expected_cost=0,
    )
    q.graphs.add_edge(gid,generate,verify)
    structure_hash=q.graphs.freeze(gid)
    with q.db.tx(immediate=True) as con:
        con.execute("UPDATE factory_runs SET graph_id=? WHERE factory_run_id=?",(gid,run_id))
        q.ledger.append_in_tx(con,"factory_run.graph_bound","factory_run",run_id,{
            "graph_id":gid,"structure_hash":structure_hash,
        })

    artifact_dir=tmp_path/"generated-api"
    builder=APIBuilder(artifact_dir)
    verifier=APIVerifier()

    # 4. Builder executes through typed Executor request.
    q.graphs.refresh_ready(gid)
    claim=q.graphs.claim_ready(builder.executor_id,graph_id=gid)
    assert claim["node_id"]==generate
    q.graphs.start(generate,builder.executor_id)
    build_result=builder.execute(ExecutionRequest(
        run_id,generate,"generate_api","generate",claim["payload"],str(tmp_path)
    ))
    assert build_result.ok
    q.graphs.verifying(generate)
    q.graphs.complete(generate,build_result.final)

    # 5. Independent verifier executes actual localhost HTTP.
    q.graphs.refresh_ready(gid)
    claim=q.graphs.claim_ready(verifier.executor_id,graph_id=gid)
    assert claim["node_id"]==verify
    q.graphs.start(verify,verifier.executor_id)
    verify_result=verifier.execute(ExecutionRequest(
        run_id,verify,"verify_api","verify",
        {"artifact_dir":str(artifact_dir)},str(tmp_path)
    ))
    assert verify_result.ok
    assert verify_result.final["status_code"]==200
    q.graphs.verifying(verify)
    q.graphs.complete(verify,verify_result.final)

    with q.db.tx(immediate=True) as con:
        con.execute("UPDATE factory_runs SET status='SUCCEEDED',finished_at=? WHERE factory_run_id=?",
                    (utc_now(),run_id))
        q.ledger.append_in_tx(con,"factory_run.succeeded","factory_run",run_id,{})

    artifact_paths=[artifact_dir/"app.py",artifact_dir/"fixture.json"]
    for path in artifact_paths:
        with q.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO artifacts(
              artifact_id,factory_run_id,node_id,sha256,media_type,size_bytes,uri,created_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            ("artifact_"+path.stem,run_id,generate,sha256(path.read_bytes()).hexdigest(),
             "text/plain",path.stat().st_size,str(path),utc_now()))

    # 6. Frozen VerificationPlan actually boots and re-verifies HTTP.
    verification=VerificationService(q.db,q.ledger,tmp_path/"verification")
    command=(
        sys.executable,"-c",
        "from qdw.factories.fixtures.api import APIFactoryFixture; import sys; "
        "r=APIFactoryFixture().verify(sys.argv[1]); "
        "assert r.passed and r.status_code==200, r.reason_code",
        str(artifact_dir),
    )
    plan=VerificationPlan(
        "api-fixture-release","1.0.0",
        (VerificationCommand("real_http",command,30,True,0),),
        artifacts=tuple(str(p) for p in artifact_paths),
    )
    verification_run=verification.execute(
        plan,task_id="V10-API",cwd=repo,require_clean=True
    )
    build_certs=BuildCertificateV2(verification)
    build_cert=build_certs.issue(verification_run)

    # 7. Exact typed fixture certificate activates the factory.
    fixture_certs=FixtureCertificateService(q.db,q.ledger,build_certs)
    fixture_cert=fixture_certs.issue(
        subject_type="factory",subject_id=definition.factory_id,subject_version=definition.version,
        definition_hash=definition_row["definition_hash"],fixture_id=definition.fixture_id,
        factory_run_id=run_id,artifact_paths=artifact_paths,acceptance_plan_hash=plan.plan_hash,
        build_certificate_id=build_cert["build_certificate_id"],
        independent_worker_id=verifier.executor_id,
    )
    q.factories.activate(definition.factory_id,definition.version,fixture_cert["fixture_certificate_id"])

    # 8. Product lineage + ReleaseAuthorization + release.
    products=ProductRegistry(q.db,q.ledger)
    product_id=products.create_from_factory_run(
        "V10 API","v10-api","api",idea_id=None,
        factory_id=definition.factory_id,factory_version=definition.version,build_run_id=run_id,
    )
    auth_service=ReleaseAuthorizationService(q.db,q.ledger,build_certs)
    auth=auth_service.issue(
        product_id=product_id,build_run_id=run_id,artifact_paths=artifact_paths,
        build_certificate_id=build_cert["build_certificate_id"],review_certificate_id=None,
        policy_hash="v10-fixture-policy",
    )
    products.release(product_id,auth["release_authorization_id"])

    # 9. Measured outcome and Passport preserve lineage.
    products.outcome(
        product_id,"health_checks",value=1,unit="pass",source="experiment",
        authority=OutcomeAuthority.MEASURED,learning_eligible=True,
        evidence={"verification_run_id":verification_run},
    )
    passport=products.passport(product_id)
    assert passport["product"]["status"]=="RELEASED"
    assert passport["product"]["build_run_id"]==run_id
    assert passport["release_authorization"]["release_authorization_id"]==auth["release_authorization_id"]
    assert passport["outcomes"][0]["learning_eligible"]==1

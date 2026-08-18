import json
from pathlib import Path
import pytest
from qdw.core import hash_object
from qdw.factories.registry import FactoryRegistry
from qdw.contractors.registry import ContractorRegistry
from qdw.products.registry import ProductRegistry

def _factory_manifest(path, factory_id="fa", version="1"):
    path.write_text(json.dumps({
        "factory_id":factory_id,"version":version,"kind":"api","name":"A",
        "phases":["build"],"mandatory_teams":[],
        "fixture":{"fixture_id":"fixture-a","max_cost_usd":1}
    }))
    return path

def _contractor_manifest(path,cid="redteam.api",version="1"):
    path.write_text(json.dumps({
        "contractor_id":cid,"version":version,"team":"redteam","specialization":"api",
        "inputs":["artifact"],"outputs":["report"],"gates":["health"]
    }))
    return path

def _gate(db,gid,detail):
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO gate_results(
            gate_result_id,factory_run_id,node_id,gate_id,passed,result_hash,detail_json,created_at
        ) VALUES(?,NULL,NULL,'fixture',1,'h',?,'2026-01-01T00:00:00Z')""",(gid,json.dumps(detail)))

def _create_release_chain(db,product_id,build_run_id,artifact_set_hash="ash",auth_build_run=None,auth_artifact_set_hash=None):
    auth_build_run=auth_build_run or build_run_id
    auth_artifact_set_hash=auth_artifact_set_hash or artifact_set_hash
    with db.tx(immediate=True) as con:
        for run_id in {build_run_id,auth_build_run}:
            con.execute("""INSERT OR IGNORE INTO factory_runs(
                factory_run_id,factory_id,factory_version,status,started_at
            ) VALUES(?,'f','1','DONE','2026-01-01T00:00:00Z')""",(run_id,))
        con.execute("""INSERT OR IGNORE INTO verification_plans_v2(
            plan_id,version,plan_hash,plan_json,status,created_at
        ) VALUES('plan-1','1','planhash','{}','ACTIVE','2026-01-01T00:00:00Z')""")
        con.execute("""INSERT OR IGNORE INTO verification_runs_v2(
            verification_run_id,plan_hash,task_id,subject_git_sha,subject_dirty,
            cwd,environment_hash,status,started_at
        ) VALUES('vr-1','planhash','t','sha',0,'/','ehash','PASS','2026-01-01T00:00:00Z')""")
        cert_inner={"artifacts":[]}
        cert_hash=hash_object(cert_inner)
        con.execute("""INSERT OR IGNORE INTO build_certificates_v2(
            build_certificate_id,verification_run_id,subject_git_sha,plan_hash,
            artifact_set_hash,certificate_json,certificate_hash,issued_at
        ) VALUES('bc-1','vr-1','sha','planhash',?,?,?,'2026-01-01T00:00:00Z')""",
        (artifact_set_hash,json.dumps({"artifacts":[],"certificate_hash":cert_hash}),cert_hash))
        auth_json={"product_id":product_id,"build_run_id":auth_build_run,"artifact_set_hash":auth_artifact_set_hash}
        auth_hash=hash_object(auth_json)
        auth_json["authorization_hash"]=auth_hash
        con.execute("""INSERT INTO release_authorizations(
            release_authorization_id,product_id,build_run_id,artifact_set_hash,
            build_certificate_id,policy_hash,status,authorization_json,
            authorization_hash,issued_at
        ) VALUES('ra-1',?,?,?,?,'phash','AUTHORIZED',?,?,'2026-01-01T00:00:00Z')""",
        (product_id,auth_build_run,auth_artifact_set_hash,'bc-1',json.dumps(auth_json),auth_hash))
    return 'ra-1'

def test_factory_rejects_unrelated_certificate(db,tmp_path):
    reg=FactoryRegistry(db)
    reg.register_manifest(_factory_manifest(tmp_path/"f.json"))
    _gate(db,"gate_x",{"factory_id":"other","factory_version":"1"})
    with pytest.raises(ValueError):
        reg.activate("fa","1","gate_x")

def test_factory_rejects_missing_or_wrong_version(db,tmp_path):
    reg=FactoryRegistry(db)
    reg.register_manifest(_factory_manifest(tmp_path/"f.json"))
    _gate(db,"gate_x",{"factory_id":"fa"})
    with pytest.raises(ValueError):
        reg.activate("fa","1","gate_x")

def test_factory_rejects_definition_hash_mismatch(db,tmp_path):
    reg=FactoryRegistry(db)
    reg.register_manifest(_factory_manifest(tmp_path/"f.json"))
    # V2 activation must require a typed fixture certificate with exact definition hash.
    _gate(db,"gate_x",{
        "factory_id":"fa","factory_version":"1","definition_hash":"wrong",
        "fixture_id":"fixture-a","artifact_set_hash":"a"
    })
    with pytest.raises(ValueError):
        reg.activate("fa","1","gate_x")

def test_factory_rejects_fixture_mismatch(db,tmp_path):
    reg=FactoryRegistry(db)
    reg.register_manifest(_factory_manifest(tmp_path/"f.json"))
    _gate(db,"gate_x",{
        "factory_id":"fa","factory_version":"1","fixture_id":"wrong",
        "artifact_set_hash":"a"
    })
    with pytest.raises(ValueError):
        reg.activate("fa","1","gate_x")

def test_contractor_rejects_unrelated_certificate(db,ledger,tmp_path):
    reg=ContractorRegistry(db,ledger)
    reg.register_manifest(_contractor_manifest(tmp_path/"c.json"))
    _gate(db,"gate_x",{"contractor_id":"other","contractor_version":"1"})
    with pytest.raises(ValueError):
        reg.activate("redteam.api","1","gate_x")

def test_release_rejects_wrong_build_run(db,ledger):
    products=ProductRegistry(db,ledger)
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO factory_runs(
            factory_run_id,factory_id,factory_version,status,started_at
        ) VALUES('run-a','f','1','DONE','2026-01-01T00:00:00Z')""")
        con.execute("""INSERT INTO factory_runs(
            factory_run_id,factory_id,factory_version,status,started_at
        ) VALUES('run-b','f','1','DONE','2026-01-01T00:00:00Z')""")
    pid=products.create("P","p","api",factory_id="f",factory_version="1",build_run_id="run-a")
    ra_id=_create_release_chain(db,pid,"run-a",auth_build_run="run-b")
    with pytest.raises(ValueError):
        products.release(pid,ra_id)

def test_release_rejects_artifact_set_mismatch(db,ledger):
    products=ProductRegistry(db,ledger)
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO factory_runs(
            factory_run_id,factory_id,factory_version,status,started_at
        ) VALUES('run-a','f','1','DONE','2026-01-01T00:00:00Z')""")
    pid=products.create("P","p","api",factory_id="f",factory_version="1",build_run_id="run-a")
    ra_id=_create_release_chain(db,pid,"run-a",artifact_set_hash="correct",auth_artifact_set_hash="wrong")
    with pytest.raises(ValueError):
        products.release(pid,ra_id)

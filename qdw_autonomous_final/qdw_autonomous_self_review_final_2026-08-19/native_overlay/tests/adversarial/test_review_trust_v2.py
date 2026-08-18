import json
from pathlib import Path
import pytest
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
    pid=products.create("P","p","api",build_run_id="run-a")
    _gate(db,"gate_x",{"product_id":pid,"build_run_id":"run-b"})
    with pytest.raises(ValueError):
        products.release(pid,"gate_x")

def test_release_rejects_artifact_set_mismatch(db,ledger):
    products=ProductRegistry(db,ledger)
    pid=products.create("P","p","api",build_run_id="run-a")
    _gate(db,"gate_x",{
        "product_id":pid,"build_run_id":"run-a","artifact_set_hash":"wrong"
    })
    with pytest.raises(ValueError):
        products.release(pid,"gate_x")

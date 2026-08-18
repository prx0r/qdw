"""Regression tests intentionally FAIL on qdw@c1ab1e4 until trust-boundary fixes land."""

import json

import pytest

from qdw.contractors.registry import ContractorRegistry
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.factories.registry import FactoryRegistry
from qdw.products.registry import ProductRegistry


def db(tmp_path):
    d=Database(tmp_path/"qdw.db");d.migrate();return d

def test_factory_activation_rejects_unrelated_passing_gate(tmp_path):
    d=db(tmp_path);reg=FactoryRegistry(d)
    manifest=tmp_path/"factory.json"
    manifest.write_text(json.dumps({
        "factory_id":"factory-a","version":"1","kind":"api","name":"A",
        "phases":["build"],"mandatory_teams":[],
        "fixture":{"fixture_id":"fixture-a","max_cost_usd":1}
    }))
    reg.register_manifest(manifest)
    # This gate is deliberately unrelated to factory-a/fixture-a.
    with d.tx(immediate=True) as con:
        con.execute("""INSERT INTO gate_results(
            gate_result_id,factory_run_id,node_id,gate_id,passed,result_hash,detail_json,created_at
        ) VALUES('gate_unrelated',NULL,NULL,'unrelated',1,'h','{}','2026-01-01T00:00:00Z')""")
    with pytest.raises(ValueError):
        reg.activate("factory-a","1","gate_unrelated")

def test_product_release_rejects_unknown_certificate(tmp_path):
    d=db(tmp_path);ledger=Ledger(d);products=ProductRegistry(d,ledger)
    pid=products.create("P","p","api")
    with pytest.raises(ValueError):
        products.release(pid,"cert_does_not_exist")

def test_contractor_version_is_immutable(tmp_path):
    d=db(tmp_path);ledger=Ledger(d);reg=ContractorRegistry(d,ledger)
    p=tmp_path/"contractor.json"
    base={"contractor_id":"redteam.api","version":"1","team":"red_team","specialization":"api",
          "inputs":["artifact"],"outputs":["report"],"gates":["health"]}
    p.write_text(json.dumps(base));reg.register_manifest(p)
    p.write_text(json.dumps({**base,"gates":["weakened"]}))
    with pytest.raises(ValueError):
        reg.register_manifest(p)

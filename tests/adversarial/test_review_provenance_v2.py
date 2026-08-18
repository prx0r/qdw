import json
import pytest
from qdw.core import hash_object
from qdw.core.graph.store import WorkGraphStore
from qdw.human.queue import HumanQueue
from qdw.products.registry import ProductRegistry

def _break_ledger(monkeypatch,ledger):
    def boom(*args,**kwargs):
        raise RuntimeError("INJECTED_LEDGER_FAILURE")
    monkeypatch.setattr(ledger,"append",boom)
    if hasattr(ledger,"append_in_tx"):
        monkeypatch.setattr(ledger,"append_in_tx",boom)

def test_add_node_event_failure_rolls_back(db,ledger,monkeypatch):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        g.add_node(gid,"x","x",{})
    with db.connect() as con:
        assert con.execute("SELECT 1 FROM work_nodes WHERE graph_id=?",(gid,)).fetchone() is None

def test_claim_event_failure_rolls_back(db,ledger,monkeypatch):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    nid=g.add_node(gid,"x","x",{},expected_value=1,expected_cost=0)
    if hasattr(g,"freeze"):
        g.freeze(gid)
    g.refresh_ready(gid)
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        g.claim_ready("w",graph_id=gid)
    with db.connect() as con:
        row=con.execute("SELECT state,lease_owner FROM work_nodes WHERE node_id=?",(nid,)).fetchone()
    assert row["state"]=="READY"
    assert row["lease_owner"] is None

def test_complete_event_failure_rolls_back(db,ledger,monkeypatch):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    nid=g.add_node(gid,"x","x",{},expected_value=1,expected_cost=0)
    if hasattr(g,"freeze"):
        g.freeze(gid)
    g.refresh_ready(gid)
    g.claim_ready("w",graph_id=gid)
    g.start(nid,"w")
    g.verifying(nid)
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        g.complete(nid,{"ok":True})
    with db.connect() as con:
        row=con.execute("SELECT state FROM work_nodes WHERE node_id=?",(nid,)).fetchone()
    assert row["state"]=="VERIFYING"

def test_human_event_failure_rolls_back(db,ledger,monkeypatch):
    q=HumanQueue(db,ledger)
    aid=q.request("release","release",{},idempotency_key="h1")
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        q.approve(aid,"owner",{"ok":True})
    with db.connect() as con:
        row=con.execute("SELECT status FROM human_actions WHERE action_id=?",(aid,)).fetchone()
    assert row["status"]=="REQUESTED"

def test_product_release_event_failure_rolls_back(db,ledger,monkeypatch):
    p=ProductRegistry(db,ledger)
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO factory_runs(
            factory_run_id,factory_id,factory_version,status,started_at
        ) VALUES('run-1','f','1','DONE','2026-01-01T00:00:00Z')""")
    pid=p.create("P","p","api",factory_id="f",factory_version="1",build_run_id="run-1")
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO verification_plans_v2(
            plan_id,version,plan_hash,plan_json,status,created_at
        ) VALUES('plan-1','1','planhash','{}','ACTIVE','2026-01-01T00:00:00Z')""")
        con.execute("""INSERT INTO verification_runs_v2(
            verification_run_id,plan_hash,task_id,subject_git_sha,subject_dirty,
            cwd,environment_hash,status,started_at
        ) VALUES('vr-1','planhash','t','sha',0,'/','ehash','PASS','2026-01-01T00:00:00Z')""")
        cert_inner={"artifacts":[]}
        cert_hash=hash_object(cert_inner)
        con.execute("""INSERT INTO build_certificates_v2(
            build_certificate_id,verification_run_id,subject_git_sha,plan_hash,
            artifact_set_hash,certificate_json,certificate_hash,issued_at
        ) VALUES('bc-1','vr-1','sha','planhash','ash',?,'chash','2026-01-01T00:00:00Z')""",
        (json.dumps({"artifacts":[],"certificate_hash":cert_hash}),))
        auth_json={"product_id":pid,"build_run_id":"run-1","artifact_set_hash":"ash"}
        auth_hash=hash_object(auth_json)
        auth_json["authorization_hash"]=auth_hash
        con.execute("""INSERT INTO release_authorizations(
            release_authorization_id,product_id,build_run_id,artifact_set_hash,
            build_certificate_id,policy_hash,status,authorization_json,
            authorization_hash,issued_at
        ) VALUES('ra-1',?,'run-1','ash','bc-1','phash','AUTHORIZED',?,?,'2026-01-01T00:00:00Z')""",
        (pid,json.dumps(auth_json),auth_hash))
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        p.release(pid,"ra-1")
    with db.connect() as con:
        row=con.execute("SELECT status FROM products WHERE product_id=?",(pid,)).fetchone()
    assert row["status"]!="RELEASED"

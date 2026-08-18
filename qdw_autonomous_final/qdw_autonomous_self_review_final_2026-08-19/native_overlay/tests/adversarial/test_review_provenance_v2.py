import json
import pytest
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
    pid=p.create("P","p","api")
    with db.tx(immediate=True) as con:
        con.execute("""INSERT INTO gate_results(
          gate_result_id,factory_run_id,node_id,gate_id,passed,result_hash,detail_json,created_at
        ) VALUES('cert_x',NULL,NULL,'release',1,'h',?,'2026-01-01T00:00:00Z')""",
        (json.dumps({"product_id":pid}),))
    _break_ledger(monkeypatch,ledger)
    with pytest.raises(RuntimeError,match="INJECTED"):
        p.release(pid,"cert_x")
    with db.connect() as con:
        row=con.execute("SELECT status FROM products WHERE product_id=?",(pid,)).fetchone()
    assert row["status"]!="RELEASED"

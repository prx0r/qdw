from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.core.graph.store import WorkGraphStore

def make(tmp_path):
    db=Database(tmp_path/"x.db");db.migrate()
    return db,WorkGraphStore(db,Ledger(db))

def test_dependencies(tmp_path):
    db,g=make(tmp_path);gid=g.create_graph()
    a=g.add_node(gid,"test","A",{},priority=1)
    b=g.add_node(gid,"test","B",{},priority=2)
    g.add_edge(gid,a,b)
    assert g.refresh_ready(gid)==1
    c=g.claim_ready("w",graph_id=gid);assert c["node_id"]==a
    g.start(a,"w");g.verifying(a);g.complete(a,{"ok":True})
    assert g.refresh_ready(gid)==1
    assert g.claim_ready("w",graph_id=gid)["node_id"]==b

def test_atomic_claim(tmp_path):
    db,g=make(tmp_path);gid=g.create_graph();g.add_node(gid,"test","A",{})
    g.refresh_ready(gid)
    assert g.claim_ready("a",graph_id=gid) is not None
    assert g.claim_ready("b",graph_id=gid) is None

def test_retry_limit(tmp_path):
    db,g=make(tmp_path);gid=g.create_graph()
    n=g.add_node(gid,"test","A",{},max_retries=0)
    g.refresh_ready(gid);g.claim_ready("w",graph_id=gid);g.start(n,"w")
    assert g.fail(n,{"why":"x"},True)=="FAILED"

from datetime import UTC,datetime,timedelta
import pytest
from qdw.core.graph.store import WorkGraphStore

def test_cycle_insert_rolls_back(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    a=g.add_node(gid,"x","a",{})
    b=g.add_node(gid,"x","b",{})
    c=g.add_node(gid,"x","c",{})
    g.add_edge(gid,a,b)
    g.add_edge(gid,b,c)
    with pytest.raises(ValueError):
        g.add_edge(gid,c,a)
    with db.connect() as con:
        row=con.execute("""SELECT 1 FROM work_edges
            WHERE graph_id=? AND from_node=? AND to_node=?""",(gid,c,a)).fetchone()
    assert row is None, "rejected cyclic edge must not remain persisted"

def test_frozen_graph_immutable(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    g.add_node(gid,"x","a",{})
    g.freeze(gid)
    with pytest.raises((ValueError,RuntimeError)):
        g.add_node(gid,"x","late",{})
    with pytest.raises((ValueError,RuntimeError)):
        g.add_edge(gid,"missing-a","missing-b")

def test_unfrozen_graph_not_executable(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    g.add_node(gid,"x","a",{},expected_value=1,expected_cost=0)
    with pytest.raises((ValueError,RuntimeError)):
        g.refresh_ready(gid)

def test_lease_expiry_attempt_ceiling(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    nid=g.add_node(gid,"x","a",{},expected_value=1,expected_cost=0,max_retries=1)
    if hasattr(g,"freeze"):g.freeze(gid)
    g.refresh_ready(gid)
    g.claim_ready("w",lease_seconds=1,graph_id=gid)
    future=datetime.now(UTC)+timedelta(seconds=10)
    g.reclaim_stale(future)
    with db.connect() as con:
        row=con.execute("SELECT state,attempt_count,max_retries FROM work_nodes WHERE node_id=?",(nid,)).fetchone()
    assert row["state"]=="FAILED"
    assert row["attempt_count"]==1

def test_fix_idempotency(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    key="review-fix:abc"
    first=g.add_node(gid,"review_fix","fix",{},idempotency_key=key)
    second=g.add_node(gid,"review_fix","fix",{},idempotency_key=key)
    assert second==first
    with db.connect() as con:
        n=con.execute("SELECT COUNT(*) FROM work_nodes WHERE graph_id=? AND idempotency_key=?",(gid,key)).fetchone()[0]
    assert n==1

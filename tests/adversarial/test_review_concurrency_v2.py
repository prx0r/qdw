import threading
from qdw.core.graph.store import WorkGraphStore

def test_32_way_claim_one_winner(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    g.add_node(gid,"x","one",{},expected_value=1,expected_cost=0)
    if hasattr(g,"freeze"):g.freeze(gid)
    g.refresh_ready(gid)
    barrier=threading.Barrier(32)
    wins=[];errors=[]
    def worker(i):
        try:
            barrier.wait(timeout=10)
            r=g.claim_ready(f"w{i}",graph_id=gid)
            if r:wins.append(r["node_id"])
        except Exception as exc:
            errors.append(exc)
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(32)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert len(wins)==1

def test_terminal_transition_race(db,ledger):
    g=WorkGraphStore(db,ledger)
    gid=g.create_graph()
    nid=g.add_node(gid,"x","one",{},expected_value=1,expected_cost=0)
    if hasattr(g,"freeze"):g.freeze(gid)
    g.refresh_ready(gid);g.claim_ready("w",graph_id=gid);g.start(nid,"w");g.verifying(nid)
    barrier=threading.Barrier(2);ok=[];errors=[]
    def complete():
        try:barrier.wait();g.complete(nid,{"ok":1});ok.append("complete")
        except Exception as e:errors.append(e)
    def fail():
        try:barrier.wait();g.fail(nid,{"bad":1},retryable=False);ok.append("fail")
        except Exception as e:errors.append(e)
    a=threading.Thread(target=complete);b=threading.Thread(target=fail)
    a.start();b.start();a.join();b.join()
    assert len(ok)==1, f"exactly one terminal transition may succeed, got {ok}"
    assert len(errors)==1

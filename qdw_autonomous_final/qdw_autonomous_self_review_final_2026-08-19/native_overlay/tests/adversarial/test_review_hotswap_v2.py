import threading
from qdw.hotswap.persistent import PersistentBanditStore
from qdw.hotswap.types import Route
from qdw.system import QDWSystem

def test_posterior_atomic_updates(db):
    store=PersistentBanditStore(db)
    barrier=threading.Barrier(20)
    errors=[]
    def work():
        try:
            barrier.wait(timeout=10)
            store.update("cell","route",True)
        except Exception as exc:
            errors.append(exc)
    ts=[threading.Thread(target=work) for _ in range(20)]
    [t.start() for t in ts];[t.join() for t in ts]
    assert not errors
    with db.connect() as con:
        row=con.execute("SELECT alpha,beta FROM route_posteriors WHERE cell_id='cell' AND route_id='route'").fetchone()
    assert row["alpha"]==21.0
    assert row["beta"]==1.0

def test_initializer_does_not_overwrite_learning(db,monkeypatch):
    store=PersistentBanditStore(db)
    route=Route("r","m","p")
    entered=threading.Event();release=threading.Event()
    original=store._upsert
    def delayed(*args,**kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return original(*args,**kwargs)
    monkeypatch.setattr(store,"_upsert",delayed)
    errors=[]
    def getter():
        try:store.get("cell",route)
        except Exception as exc:errors.append(exc)
    t=threading.Thread(target=getter);t.start()
    assert entered.wait(timeout=5)
    store.update("cell","r",True)
    release.set();t.join()
    assert not errors
    with db.connect() as con:
        row=con.execute("SELECT alpha,beta FROM route_posteriors WHERE cell_id='cell' AND route_id='r'").fetchone()
    # If the delayed initializer overwrites the learned row, beta becomes the prior's beta=2.
    assert row["beta"]==1.0

def test_route_roundtrip_complete(db):
    store=PersistentBanditStore(db)
    route=Route(
        route_id="r",model_id="m",provider_id="p",
        endpoint_id="ep",account_id="acct",active=True,free=False,
        input_per_m=.1,output_per_m=.2,context_tokens=128000,
        tools_supported=True,json_supported=True,reliability=.99,latency_ms=123,
        prior_success=.83,prior_confidence=.7,breaker_open=True,quota_pressure=.4,
        cheapest_paid_replacement_cost=0.0,evidence_ids=["obs1","obs2"],
    )
    store.save_route(route)
    loaded=store.load_routes()
    assert len(loaded)==1
    got=loaded[0]
    for field in (
        "route_id","model_id","provider_id","endpoint_id","account_id","active","free",
        "input_per_m","output_per_m","context_tokens","tools_supported","json_supported",
        "reliability","latency_ms","prior_success","prior_confidence","breaker_open",
        "quota_pressure","cheapest_paid_replacement_cost","evidence_ids"
    ):
        assert getattr(got,field)==getattr(route,field), field

def test_route_registry_deduplicates(tmp_path):
    q=QDWSystem(tmp_path/"db.sqlite")
    route=Route("r","m","p",input_per_m=.1,output_per_m=.1)
    q.register_route(route)
    q.register_route(route)
    assert [x.route_id for x in q.routes].count("r")==1

def test_route_survives_restart(tmp_path):
    path=tmp_path/"db.sqlite"
    q=QDWSystem(path)
    q.register_route(Route("r","m","p",endpoint_id="ep",input_per_m=.1,output_per_m=.1))
    q2=QDWSystem(path)
    got=next(x for x in q2.routes if x.route_id=="r")
    assert got.endpoint_id=="ep"

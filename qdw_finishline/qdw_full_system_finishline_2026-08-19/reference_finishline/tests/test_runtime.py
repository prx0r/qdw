import sqlite3
from qdw_finishline import FederationRuntime
from qdw_finishline.models import AttemptState

def runtime(tmp_path,gg,dell,forge):
    return FederationRuntime(tmp_path/"runtime.db",tmp_path/"routes.db",gg,dell,forge)

def test_refresh_includes_real_forge_asset(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge);xs=r.refresh_routes("api.build",max_cost=.1)
    assert any(x.source=="forge" for x in xs)

def test_qdw_reference_route_can_choose_forge(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge);r.refresh_routes("api.build",max_cost=.1)
    assert r.choose("api.build").source=="forge"

def test_full_execution_commits(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    x=r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    assert x["state"]==AttemptState.COMMITTED.value
    assert x["external_invocation_id"]
    assert x["certificate_id"]

def test_cost_record_exactly_once(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    with r.store.connect() as c:
        n=c.execute("SELECT COUNT(*) FROM costs WHERE attempt_id='a1'").fetchone()[0]
    assert n==1

def test_learning_updates_exactly_once(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    x=r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    route=x["route_id"]
    with r.store.connect() as c:a=c.execute("SELECT alpha,beta FROM learning WHERE route_id=?",(route,)).fetchone()
    r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    with r.store.connect() as c:b=c.execute("SELECT alpha,beta FROM learning WHERE route_id=?",(route,)).fetchone()
    assert tuple(a)==tuple(b)

def test_restart_after_routing_preserves_fixed_cost(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    x=r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1",stop_after="ROUTED")
    assert x["state"]==AttemptState.ROUTED.value
    r2=runtime(tmp_path,gg,dell,forge)
    route=r2.routes.load(x["route_id"])
    assert route.fixed_cost==.01

def test_restart_after_unverified_can_finish(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    x=r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1",stop_after="SUCCEEDED_UNVERIFIED")
    assert x["state"]==AttemptState.SUCCEEDED_UNVERIFIED.value
    r2=runtime(tmp_path,gg,dell,forge)
    y=r2.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1")
    assert y["state"]==AttemptState.COMMITTED.value

def test_no_lease_token_persisted_in_qdw_runtime(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1",stop_after="LEASED")
    raw=(tmp_path/"runtime.db").read_bytes()
    assert b"lease-token-" not in raw

def test_proposals_do_not_become_authoritative_decisions(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge);r.sync_gitgoblin()
    with r.store.connect() as c:
        rows=c.execute("SELECT authority FROM proposals").fetchall()
    assert rows and all(x[0]=="ADVISORY" for x in rows)

def test_attempt_state_is_durable(tmp_path,gg,dell,forge):
    r=runtime(tmp_path,gg,dell,forge)
    r.execute("api.build",{"task":"x"},max_spend=.1,attempt_id="a1",stop_after="CANDIDATES_READY")
    assert runtime(tmp_path,gg,dell,forge).store.get("a1")["state"]=="CANDIDATES_READY"

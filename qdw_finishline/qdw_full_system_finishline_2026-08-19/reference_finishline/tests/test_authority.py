from qdw_finishline import FederationRuntime

def test_dell_response_declares_advisory(dell):
    assert dell.federation_resolve()["authority"]=="ADVISORY"

def test_gitgoblin_proposals_declare_advisory(gg):
    assert all(p["authority"]=="ADVISORY" for p in gg.export_qdw().proposals)

def test_forge_execution_never_returns_verified(forge):
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.1,operations=("invoke",))
    x=forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")
    assert x.status=="SUCCEEDED_UNVERIFIED"

def test_qdw_runtime_is_only_component_committing_learning(tmp_path,gg,dell,forge):
    r=FederationRuntime(tmp_path/"q.db",tmp_path/"r.db",gg,dell,forge)
    r.execute("api.build",{},max_spend=.1,attempt_id="a")
    with r.store.connect() as c:n=c.execute("SELECT COUNT(*) FROM learning").fetchone()[0]
    assert n==1

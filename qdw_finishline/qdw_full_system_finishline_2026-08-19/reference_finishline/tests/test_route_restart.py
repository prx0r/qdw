from qdw_finishline.models import Route,Ref
from qdw_finishline.route_store import RouteStore

def test_fixed_cost_survives_restart(tmp_path):
    p=tmp_path/"routes.db";s=RouteStore(p)
    s.save(Route("forge:a@1","forge","coding",0.012,.9,True,Ref("forge","asset","a","1","sha256:a")))
    del s
    s=RouteStore(p)
    r=s.load("forge:a@1")
    assert r.fixed_cost==0.012

def test_external_ref_survives_restart(tmp_path):
    p=tmp_path/"routes.db";s=RouteStore(p)
    s.save(Route("dell:o","dell","coding",.02,.8,True,Ref("dell","offer","o",None,"sha256:o")))
    r=RouteStore(p).load("dell:o")
    assert r.external_ref.system=="dell" and r.external_ref.digest_value=="sha256:o"

def test_route_update_persists_new_cost(tmp_path):
    s=RouteStore(tmp_path/"r.db")
    s.save(Route("x","forge","c",.2));s.save(Route("x","forge","c",.1))
    assert RouteStore(tmp_path/"r.db").load("x").fixed_cost==.1

from qdw_finishline.dell import DellService,Workload,workload_cost
from qdw_finishline.models import Status

def test_unknown_output_price_is_unknown_when_output_nonzero():
    assert workload_cost(1,None,False,Workload(1000,500,1)) is None

def test_unknown_output_price_can_be_irrelevant_when_zero_output():
    assert workload_cost(1,None,False,Workload(1000,0,1))==.001

def test_free_route_is_zero_even_unknown_prices():
    assert workload_cost(None,None,True,Workload())==0

def test_budget_excludes_unknown_paid_price():
    d=DellService([{"offer_id":"o","provider_id":"p","model_id":"m",
                    "input_per_m":1,"output_per_m":None,"free":False}])
    x=d.federation_resolve(Workload(),max_cost=1)
    assert x["status"] is Status.OK_EMPTY
    assert x["excluded"][0]["reasons"]==["PRICE_UNKNOWN"]

def test_full_candidate_facts_survive_response():
    d=DellService([{"offer_id":"o","provider_id":"p","model_id":"m",
                    "input_per_m":1,"output_per_m":2,"free":False,"score":.9,"quality":.8}])
    x=d.federation_resolve(Workload(),max_cost=1)
    c=x["candidates"][0]
    assert c["input_per_m"]==1 and c["output_per_m"]==2 and c["estimated_cost"] is not None
    assert x["authority"]=="ADVISORY"

def test_unavailable_is_not_ok_empty(dell):
    dell.available=False
    try:dell.federation_resolve()
    except ConnectionError as e:assert "unavailable" in str(e)
    else:raise AssertionError("outage incorrectly returned normal response")

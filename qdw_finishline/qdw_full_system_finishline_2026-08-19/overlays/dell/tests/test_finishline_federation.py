from app.services.decision import RouteCandidate,Workload,calculate_workload_cost
from app.federation import federation_resolve

def test_unknown_output_price_stays_unknown():
    c=RouteCandidate("o","m","p",input_per_m=1,output_per_m=None,free=False)
    assert calculate_workload_cost(c,Workload(input_tokens_per_request=1000,
        output_tokens_per_request=500,requests=1)) is None

def test_zero_output_allows_input_only_price():
    c=RouteCandidate("o","m","p",input_per_m=1,output_per_m=None,free=False)
    assert calculate_workload_cost(c,Workload(input_tokens_per_request=1000,
        output_tokens_per_request=0,requests=1))==0.001

def test_federation_response_keeps_complete_recommended_price():
    x=federation_resolve(
      {"workload":{"input_tokens_per_request":1000,"output_tokens_per_request":500,"requests":1}},
      [{"offer_id":"o","model_id":"m","provider_id":"p","input_per_m":1,"output_per_m":2,
        "free":False,"metadata":{"reliability":90,"throughput_tps":10}}],[])
    assert x["authority"]=="ADVISORY"
    assert x["recommended"]["input_per_m"]==1
    assert x["recommended"]["output_per_m"]==2
    assert x["recommended"]["estimated_cost"]==0.002

from app.services.decision import RouteCandidate,Workload,calculate_workload_cost

def test_output_price_unknown_is_unknown_when_output_tokens_nonzero():
    c=RouteCandidate(offer_id="o",model_id="m",provider_id="p",
                     input_per_m=1.0,output_per_m=None,free=False)
    w=Workload(input_tokens_per_request=1000,output_tokens_per_request=500,requests=1)
    assert calculate_workload_cost(c,w) is None

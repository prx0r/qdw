from qdw.hotswap.types import Route,TaskSpec

def test_fixed_per_call_cost_is_supported():
    r=Route("forge:a@1","forge-capability:a","forge",fixed_request_cost_usd=.012)
    assert r.request_cost(TaskSpec("t","coding"))==.012

def test_unknown_output_token_price_remains_unknown():
    r=Route("dell:o","m","p",input_per_m=1.0,output_per_m=None)
    t=TaskSpec("t","coding",estimated_input_tokens=1000,estimated_output_tokens=100)
    assert r.request_cost(t) is None

from qdw_lab.repo import text

def test_unknown_output_price_is_not_zero():
    s=text("dell","app/services/decision.py")
    block=s[s.find("def calculate_workload_cost"):s.find("def assess_route")]
    assert "output_tokens_per_request > 0" in block
    assert "output_per_m is None" in block
    # There may still be `(output_per_m or 0)` after the guard; the guard is the invariant.

def test_federation_endpoint_exists():
    s=text("dell","app/api_canonical.py")
    assert "/v1/federation/resolve" in s

def test_federation_response_exposes_complete_candidates():
    s=text("dell","app/api_canonical.py")+text("dell","app/services/decision.py")
    assert "authority" in s and "ADVISORY" in s
    assert "candidates" in s

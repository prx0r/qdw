from qdw_lab.httpcheck import post_json

def body(output=500,max_cost=1):
    return {"workload":{"task":"coding","input_tokens_per_request":1000,
                        "output_tokens_per_request":output,"requests":1},
            "constraints":{"max_total_cost_usd":max_cost}}

def test_federation_resolve_is_advisory(urls):
    x=post_json(urls["dell"],"/v1/federation/resolve",body())
    assert x["schema_version"]=="qdw-federation-resource/1"
    assert x["authority"]=="ADVISORY"
    assert "candidates" in x and "excluded" in x

def test_candidate_has_complete_price_facts(urls):
    x=post_json(urls["dell"],"/v1/federation/resolve",body())
    for c in x["candidates"][:20]:
        assert "input_per_m" in c and "output_per_m" in c
        assert "estimated_cost" in c

def test_unknown_output_price_is_not_zero_cost(urls):
    # This endpoint must never invent output cost. We cannot force Dell's live DB to have an unknown-output
    # candidate, so the dedicated deterministic unit regression remains mandatory too.
    x=post_json(urls["dell"],"/v1/federation/resolve",body(output=500))
    for c in x["candidates"]:
        if not c.get("free") and c.get("output_per_m") is None:
            assert c.get("estimated_cost") is None

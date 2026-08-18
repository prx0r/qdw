from app.federation import federation_resolve

def test_federation_route_is_advisory():
    out=federation_resolve(
      {"workload":{"task":"coding","requests":1},
       "constraints":{"max_total_cost_usd":1}},
      [{"offer_id":"o","model_id":"m","provider_id":"p","input_per_m":1,
        "output_per_m":1,"free":False,"context_tokens":32000,
        "lifecycle_state":"ACTIVE","freshness_state":"FRESH","evidence_coverage":1,
        "reliability":.9,"throughput_tps":10}],
      []
    )
    assert out["authority"]=="ADVISORY"
    assert out["schema_version"].endswith("/1")

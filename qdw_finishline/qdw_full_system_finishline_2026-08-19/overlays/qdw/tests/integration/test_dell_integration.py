from qdw.federation.dell_adapter import DellFederationAdapter

def response():
    c={"offer_id":"o1","provider_id":"p","model_id":"m","input_per_m":1.0,
       "output_per_m":2.0,"free":False,"estimated_cost":.002,"score":90,
       "reliability":90,"evidence_coverage":1.0,"confidence":.9}
    return {
      "schema_version":"qdw-federation-resource/1","authority":"ADVISORY",
      "candidates":[c],"recommended":c,"excluded":[],
      "decision":{"status":"RESOLVED","method":"decision_service_v2_federation"}}

def test_recommended_candidate_keeps_cost():
    snap,adv=DellFederationAdapter().normalize({},response())
    c=snap.normalized["candidates"][0]
    assert c["estimated_cost_usd"]==.002
    assert c["input_per_m"]==1.0 and c["output_per_m"]==2.0
    assert adv.authority=="ADVISORY"

def test_dell_score_is_not_qdw_probability():
    snap,_=DellFederationAdapter().normalize({},response())
    c=snap.normalized["candidates"][0]
    assert c["dell_score"]==90
    assert "p_success" not in c

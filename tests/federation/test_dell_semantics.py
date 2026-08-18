from qdw.federation.dell_adapter import DellFederationAdapter
from qdw.federation.contracts import ExternalStatus

def test_dell_score_not_normalized_as_qdw_probability():
    a=DellFederationAdapter()
    s,ad=a.normalize({"workload":{"task":"coding"}},{
      "schema_version":"qdw-federation-resource/1",
      "candidates":[{"offer_id":"o","provider_id":"p","model_id":"m","score":99,
                     "input_per_m":1,"output_per_m":2,"estimated_cost":.01}],
      "recommended":{"offer_id":"o","provider_id":"p","model_id":"m","score":99},
      "excluded":[],"decision":{"status":"RESOLVED","method":"dell"}
    })
    c=s.normalized["candidates"][0]
    assert c["dell_score"]==99
    assert "p_success" not in c
    assert ad.authority=="ADVISORY"

def test_no_candidates_is_ok_empty():
    s,_=DellFederationAdapter().normalize({},{
      "schema_version":"qdw-federation-resource/1",
      "candidates":[],"recommended":None,
      "excluded":[],"decision":{"status":"NO_CANDIDATES"}
    })
    assert s.status is ExternalStatus.OK_EMPTY

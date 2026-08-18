from qdw_federation.adapters.dell import DellAdapter
from qdw_federation.models import ExternalStatus,AuthorityKind

def req():
    return {"capability":"inference","workload":{"task":"coding"},"constraints":{"max_total_cost_usd":1}}

def test_dell_resolved_is_snapshot_plus_advisory():
    result={
      "recommended":{"offer_id":"o1","model_id":"m1","provider_id":"p1","score":88,
                     "estimated_cost":.01,"evidence_coverage":.8,"confidence":.9},
      "alternatives":[{"offer_id":"o2","model_id":"m2","provider_id":"p2","score":70,"estimated_cost":.02}],
      "excluded":[],"decision":{"status":"RESOLVED","method":"decision_service_v2","as_of":"now"}
    }
    snap,adv=DellAdapter().resolve_to_snapshot(req(),result,source_revision="sha")
    assert snap.status is ExternalStatus.OK
    assert len(snap.candidates)==2
    assert snap.candidates[0].quality is None  # Dell score is not QDW p_success/quality.
    assert snap.candidates[0].attributes["dell_score"]==88
    assert adv.authority is AuthorityKind.ADVISORY
    assert adv.evidence_snapshot_digest==snap.snapshot_digest

def test_dell_no_candidates_is_not_failure():
    snap,adv=DellAdapter().resolve_to_snapshot(req(),{
        "recommended":None,"alternatives":[],"excluded":[],
        "decision":{"status":"NO_CANDIDATES","reasons":["budget"]}
    })
    assert snap.status is ExternalStatus.OK_EMPTY and adv is None

def test_dell_outage_is_unavailable_not_empty():
    snap=DellAdapter().failure_snapshot(req(),"timeout")
    assert snap.status is ExternalStatus.UNAVAILABLE
    assert snap.candidates==()

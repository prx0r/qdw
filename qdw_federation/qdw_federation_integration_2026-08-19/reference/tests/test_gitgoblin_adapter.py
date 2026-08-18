from qdw_federation.adapters.gitgoblin import GitGoblinAdapter
from qdw_federation.store import FederationStore
from qdw_federation.models import AuthorityKind

def records():
    return [{
        "observation_id":"gg_sig1_momentum","oracle_id":"gitgoblin.frontier_graph.v1",
        "entity_id":"repo:owner/project","observed_at":"2026-08-19T00:00:00+00:00",
        "source_family":"frontier_attention","sector":"ai","metric":"momentum","value":.82,
        "unit":"score","evidence":{"artifact_sha256":"a"*64},
        "quality":{"confidence":.9,"expert_count":8,"independent_cluster_count":3,"evidence_count":10},
    }]

def test_gitgoblin_batch_is_hashed_and_observational():
    b=GitGoblinAdapter().market_records_to_batch(records(),cursor="c1",source_revision="sha1")
    assert b.observations[0].evidence.authority is AuthorityKind.OBSERVATION
    assert b.observations[0].external_ref.system=="gitgoblin"
    assert b.batch_digest.startswith("sha256:")

def test_gitgoblin_ingest_idempotent():
    b=GitGoblinAdapter().market_records_to_batch(records(),cursor="c1")
    s=FederationStore()
    assert s.ingest_batch(b)=={"inserted":1,"duplicates":0}
    assert s.ingest_batch(b)=={"inserted":0,"duplicates":1}

def test_gitgoblin_opportunity_remains_proposal():
    x=GitGoblinAdapter().opportunity_proposal({
        "opportunity_id":"opp1","problem":"x","evidence":["e1"],"scorecard":{"x":1},
        "decision":"BUILD","solution_hypotheses":["a"],
    })
    assert x["authority"] is AuthorityKind.ADVISORY
    assert x["external_decision"]=="BUILD"
    assert x["proposal_ref"].system=="gitgoblin"

from datetime import UTC,datetime
from types import SimpleNamespace
from gitgoblin.integrations.qdw import SCHEMA,build_export

class Signal:
    signal_id="s1"
    target_id="repo:x"
    detected_at=datetime(2026,8,19,tzinfo=UTC)
    sector="ai"
    confidence=.9
    expert_count=3
    independent_cluster_count=2
    evidence_ids=["e1","e2"]
    technical_alpha=.8
    novelty=.7
    momentum=.9
    def model_dump(self,mode="json"):
        return {
          "signal_id":self.signal_id,"target_id":self.target_id,
          "detected_at":self.detected_at.isoformat(),"sector":self.sector,
          "confidence":self.confidence,"expert_count":self.expert_count,
          "independent_cluster_count":self.independent_cluster_count,
          "evidence_ids":self.evidence_ids,"technical_alpha":self.technical_alpha,
          "novelty":self.novelty,"momentum":self.momentum}

class Opp:
    opportunity_id="p1";problem="x";sector="ai";primitive="tool"
    evidence_ids=["e1"];scorecard={"value":.8};decision="BUILD";solution_hypotheses=["a"]
    def model_dump(self,mode="json"):
        return {
          "opportunity_id":self.opportunity_id,"problem":self.problem,"sector":self.sector,
          "primitive":self.primitive,"evidence_ids":self.evidence_ids,"scorecard":self.scorecard,
          "decision":self.decision,"solution_hypotheses":self.solution_hypotheses}

class Store:
    def signals(self,sector,limit):return [Signal()]
    def opportunities(self,sector,limit):return [Opp()]

def test_schema_version_is_explicit():
    assert SCHEMA=="qdw-federation-observation/1"

def test_export_decisions_are_advisory():
    x=build_export(Store(),limit=10)
    assert x["opportunity_proposals"][0]["authority"]=="ADVISORY"

def test_unchanged_export_has_stable_batch_digest():
    a=build_export(Store(),limit=10)
    b=build_export(Store(),limit=10)
    assert a["batch_digest"]==b["batch_digest"]

def test_export_contains_evidence_bound_observations():
    x=build_export(Store(),limit=10)
    assert x["observations"]
    o=x["observations"][0]
    assert o["external_ref"]["digest"].startswith("sha256:")
    assert o["evidence_digest"].startswith("sha256:")
